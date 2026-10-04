"""
Telemetry client for Cornerstone.

Fires events to AGENTIC_TELEMETRY_URL/v1/events in a background thread.
If AGENTIC_TELEMETRY_URL is unset or empty, all calls are silent no-ops.
Never raises. Never blocks the caller.
"""

# ADR: 0058
from __future__ import annotations

import json
import os
import re
import time
import uuid
from pathlib import Path
import subprocess  # nosec B404
import threading
import urllib.error
import urllib.request
from typing import Any

_TELEMETRY_URL_VAR = "AGENTIC_TELEMETRY_URL"
_DEBUG_VAR = "AGENTIC_TELEMETRY_DEBUG"
_TIMEOUT_SECONDS = 3

# ADR-0076: ingest is guarded by two layers the emitter must satisfy —
# Google IAP at the edge (ADR-0070) and the app ApiKey (ADR-0068). The ApiKey
# is read from the same credentials file the Lodge MCP tools use; the IAP
# ID-token is minted via ADC impersonating the already-provisioned invoker SA,
# mirroring src/lodge/mcp/server.py::_resolve_iap_token. All best-effort.
_CREDENTIALS_PATH = Path.home() / ".cornerstone" / "credentials"
_IAP_TOKEN_VAR = "CORNERSTONE_IAP_TOKEN"  # nosec B105  # env var name, not a secret
_IAP_OAUTH_CLIENT_ID_ENV = "CORNERSTONE_IAP_OAUTH_CLIENT_ID"
_IAP_OAUTH_CLIENT_ID_DEFAULT = (
    "377653143743-rdat4rgothfg3amqj8bgjcji6ovun0u9.apps.googleusercontent.com"
)
_KEYSTONE_INVOKER_SA_ENV = "KEYSTONE_INVOKER_SA"
_KEYSTONE_INVOKER_SA_DEFAULT = (
    "keystone-invoker@dea-keystone-prj-dev.iam.gserviceaccount.com"
)

# Retry policy for send_event_sync (ADR-0058, issue #56): sleep the given seconds
# between attempts, so N backoffs => N+1 attempts. Module-level so tests can
# monkeypatch it (e.g. to () for a single, no-sleep attempt).
_RETRY_BACKOFFS = (0.5, 1.0, 2.0)

# Sub-directory of ~/.lodge holding events that could not be delivered, so a
# later telemetry run can flush them. Resolved via a function so tests can
# repoint HOME and the real path is never touched during the suite.
_PENDING_DIR_NAME = "pending_events"

_GIT_CONTEXT: dict[str, str | None] | None = None
_GIT_LOCK = threading.Lock()

_ISSUE_RE = re.compile(r"(?:issue|fix|feat|feature|bug)[/_-](\d+)", re.IGNORECASE)


def _read_git_context() -> dict[str, str | None]:
    global _GIT_CONTEXT  # noqa: PLW0603
    with _GIT_LOCK:
        if _GIT_CONTEXT is not None:
            return _GIT_CONTEXT

        ctx: dict[str, str | None] = {
            "branch": None,
            "commit_sha": None,
            "pr_number": None,
            "issue_number": None,
        }
        try:
            ctx["commit_sha"] = subprocess.check_output(  # nosec B603 B607
                ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
            ).strip()[:40]
        except Exception:  # nosec B110  # noqa: BLE001
            pass
        try:
            branch = subprocess.check_output(  # nosec B603 B607
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            if branch and branch != "HEAD":
                ctx["branch"] = branch
        except Exception:  # nosec B110  # noqa: BLE001
            pass

        # PR number from GitHub Actions env
        github_ref = os.environ.get("GITHUB_REF", "")
        pr_match = re.search(r"refs/pull/(\d+)/", github_ref)
        if pr_match:
            ctx["pr_number"] = pr_match.group(1)

        # Issue number: explicit env > branch name regex
        issue_env = os.environ.get("GITHUB_ISSUE", "").strip()
        if issue_env and issue_env.isdigit():
            ctx["issue_number"] = issue_env
        elif ctx.get("branch"):
            m = _ISSUE_RE.search(ctx["branch"])
            if m:
                ctx["issue_number"] = m.group(1)

        _GIT_CONTEXT = ctx
        return ctx


_GH_USERNAME: str | None = None
_GH_USERNAME_LOCK = threading.Lock()


def get_github_username(fallback: str = "unknown") -> str:
    """Resolve the GitHub username via gh CLI, cached per process."""
    global _GH_USERNAME  # noqa: PLW0603
    with _GH_USERNAME_LOCK:
        if _GH_USERNAME is not None:
            return _GH_USERNAME
        try:
            result = subprocess.run(  # nosec B603 B607
                ["gh", "api", "user", "--jq", ".login"],
                capture_output=True,
                text=True,
                check=False,
                timeout=3,
            )
            username = result.stdout.strip()
            if result.returncode == 0 and username:
                _GH_USERNAME = username
                return _GH_USERNAME
        except Exception:  # nosec B110  # noqa: BLE001
            pass
        _GH_USERNAME = fallback
        return _GH_USERNAME


def _read_url_from_local_config() -> str:
    try:
        env_lodge = Path(".telemetry") / ".env.lodge"
        if env_lodge.exists():
            for line in env_lodge.read_text(encoding="utf-8").splitlines():
                if line.startswith("AGENTIC_TELEMETRY_URL="):
                    return line.split("=", 1)[1].strip().rstrip("/")
    except Exception:  # nosec B110  # noqa: BLE001
        pass
    try:
        import json

        data = json.loads(Path(".cornerstone").read_text(encoding="utf-8"))
        url = data.get("cookiecutter_vars", {}).get("agentic_telemetry_url", "")
        return url.rstrip("/")
    except Exception:  # nosec B110  # noqa: BLE001
        pass
    return ""


def _read_api_token() -> str:
    """Read the Lodge ApiKey (ADR-0068) from the [default] section of
    ~/.cornerstone/credentials — the same file the Lodge MCP tools use.
    interpolation=None so a token containing '%' is never mis-parsed."""
    try:
        import configparser

        cp = configparser.ConfigParser(interpolation=None)
        cp.read(_CREDENTIALS_PATH, encoding="utf-8")
        return cp.get("default", "token", fallback="").strip()
    except Exception:  # nosec B110  # noqa: BLE001
        return ""


_iap_token_cache: str | None = None
_iap_token_fetched = False


def _resolve_iap_token() -> str | None:
    """Mint (once per process) the Google ID-token IAP requires (ADR-0076).

    Mirrors src/lodge/mcp/server.py::_resolve_iap_token: ADC impersonating the
    invoker SA (granted iap.httpsResourceAccessor on the Lodge backend-service),
    audience = the IAP OAuth client ID. Never raises; cached for the process."""
    global _iap_token_cache, _iap_token_fetched  # noqa: PLW0603
    if _iap_token_fetched:
        return _iap_token_cache
    _iap_token_fetched = True

    audience = os.environ.get(_IAP_OAUTH_CLIENT_ID_ENV, _IAP_OAUTH_CLIENT_ID_DEFAULT)
    principal = os.environ.get(_KEYSTONE_INVOKER_SA_ENV, _KEYSTONE_INVOKER_SA_DEFAULT)
    token = None
    try:
        from google.auth import default, impersonated_credentials
        from google.auth.transport.requests import Request

        source_creds, _ = default()
        target = impersonated_credentials.IDTokenCredentials(
            impersonated_credentials.Credentials(
                source_credentials=source_creds,
                target_principal=principal,
                target_scopes=[],
            ),
            target_audience=audience,
            include_email=True,
        )
        for _attempt in range(3):
            try:
                target.refresh(Request())
                token = target.token
                break
            except Exception:  # nosec B112  # noqa: BLE001
                time.sleep(1)
    except Exception:  # nosec B110  # noqa: BLE001
        token = None
    _iap_token_cache = token
    return _iap_token_cache


def _auth_headers() -> dict[str, str]:
    """Best-effort auth headers for ingest behind IAP (ADR-0076):
    - Authorization: Bearer <ApiKey>          (ADR-0068 app auth)
    - Proxy-Authorization: Bearer <id-token>  (Google IAP edge, ADR-0070)
    The ApiKey source is the unified _get_api_key() (env / .env.lodge /
    ~/.cornerstone/credentials). A missing credential simply omits its header;
    the emitter stays fire-and-forget and never raises."""
    headers: dict[str, str] = {}
    api_key = _get_api_key()
    if api_key:
        headers["Authorization"] = (
            api_key if api_key.startswith("Bearer ") else f"Bearer {api_key}"
        )
    iap_token = os.environ.get(_IAP_TOKEN_VAR, "").strip() or _resolve_iap_token() or ""
    if iap_token:
        headers["Proxy-Authorization"] = f"Bearer {iap_token}"
    return headers


def read_project_slug(fallback: str = "unknown") -> str:  # noqa: CCR001
    """Read project slug from env var, .telemetry/.env.lodge, .cornerstone, or git remote."""
    env_slug = os.environ.get("PROJECT_SLUG", "").strip()
    if env_slug:
        return env_slug
    try:
        env_lodge = Path(".telemetry") / ".env.lodge"
        if env_lodge.exists():
            for line in env_lodge.read_text(encoding="utf-8").splitlines():
                if line.startswith("PROJECT_SLUG="):
                    slug = line.split("=", 1)[1].strip()
                    if slug:
                        return slug
    except Exception:  # nosec B110  # noqa: BLE001
        pass
    try:
        data = json.loads(Path(".cornerstone").read_text(encoding="utf-8"))
        slug = data.get("cookiecutter_vars", {}).get("project_slug", "")
        if slug:
            return slug
    except Exception:  # nosec B110  # noqa: BLE001
        pass
    try:
        result = subprocess.run(  # nosec B603 B607
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=False,
            timeout=3,
        )
        if result.returncode == 0 and result.stdout.strip():
            basename = re.sub(
                r"\.git$", "", result.stdout.strip().rstrip("/").rsplit("/", 1)[-1]
            )
            if basename:
                return basename
    except Exception:  # nosec B110  # noqa: BLE001
        pass
    return fallback


def _base_url() -> str:
    url = os.environ.get(_TELEMETRY_URL_VAR, "").rstrip("/")
    return url if url else _read_url_from_local_config()


def is_telemetry_enabled() -> bool:
    """Return True if AGENTIC_TELEMETRY_URL is set in env or local config."""
    return bool(_base_url())


def _debug(msg: str) -> None:
    if os.environ.get(_DEBUG_VAR):
        import sys

        print(f"[agentic-telemetry] {msg}", file=sys.stderr)


def _enrich(event: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of *event* augmented with git-context fields."""
    git_ctx = _read_git_context()
    enriched = dict(event)
    for key in ("branch", "commit_sha", "pr_number", "issue_number"):
        if enriched.get(key) is None and git_ctx.get(key) is not None:
            enriched[key] = git_ctx[key]
    return enriched


def _read_api_key_from_local_config() -> str:
    try:
        env_lodge = Path(".telemetry") / ".env.lodge"
        if env_lodge.exists():
            for line in env_lodge.read_text(encoding="utf-8").splitlines():
                if line.startswith("API_KEY=") or line.startswith("AGENTIC_TELEMETRY_API_KEY="):
                    return line.split("=", 1)[1].strip()
    except Exception:  # nosec B110  # noqa: BLE001
        pass
    return ""


def _get_api_key() -> str:
    key = (
        os.environ.get("AGENTIC_TELEMETRY_API_KEY")
        or os.environ.get("LODGE_E2E_API_KEY")
        or os.environ.get("LODGE_API_KEY")
    )
    if key:
        return key.strip()
    # .env.lodge (API_KEY=) first, then ~/.cornerstone/credentials (ADR-0076).
    return _read_api_key_from_local_config() or _read_api_token()


def _post_event(enriched: dict[str, Any]) -> None:
    """POST one enriched event. Raises on any failure so the caller decides
    whether to retry, persist, or drop (HTTPError carries the status in .code)."""
    data = json.dumps(enriched, default=str).encode("utf-8")
    req = urllib.request.Request(
        _base_url() + "/v1/events",
        data=data,
        headers={"Content-Type": "application/json", **_auth_headers()},
    )
    with urllib.request.urlopen(req, timeout=_TIMEOUT_SECONDS):  # nosec B310  # URL from config/env, not user input
        pass



def _is_permanent_failure(exc: BaseException) -> bool:
    """True for 4xx — retrying/persisting will never resolve it (poison pill)."""
    return isinstance(exc, urllib.error.HTTPError) and 400 <= exc.code < 500


def _pending_dir() -> Path:
    """~/.lodge/pending_events (indirection so tests can repoint HOME)."""
    return Path.home() / ".lodge" / _PENDING_DIR_NAME


def _unlink_quietly(path: Path) -> None:
    try:
        path.unlink()
    except OSError:  # nosec B110
        pass


def _persist_pending_event(enriched: dict[str, Any]) -> bool:
    """Write *enriched* to ~/.lodge/pending_events/<ts>-<uuid>.json. Never raises.

    Returns True when the event was durably persisted — ADR-0061 callers use
    this to decide whether the event is accounted for."""
    try:
        pending_dir = _pending_dir()
        pending_dir.mkdir(parents=True, exist_ok=True)
        fname = f"{int(time.time() * 1000)}-{uuid.uuid4().hex}.json"
        (pending_dir / fname).write_text(
            json.dumps(enriched, default=str), encoding="utf-8"
        )
        _debug(f"persisted pending event {fname}")
        return True
    except Exception as exc:  # nosec B110  # noqa: BLE001
        _debug(f"failed to persist pending event: {exc}")
        return False


def send_event_sync(event: dict[str, Any]) -> bool:
    """Synchronous POST — blocks until the request completes or times out.

    Use this in short-lived scripts (e.g. stop hooks) where a daemon thread
    would be killed before completing the request. Retries transient failures
    (ADR-0058); on final transient failure persists the event to
    ~/.lodge/pending_events/ for a later flush; drops 4xx. Never raises.

    Returns True when the event reached a final state — delivered, durably
    persisted for a later flush, or dropped as a 4xx poison pill that no retry
    can fix. Returns False when the event could not be recorded but a later
    retry may succeed (telemetry disabled, persistence failure). ADR-0061 uses
    this to decide whether to advance the per-transcript watermark.
    """
    if not is_telemetry_enabled():
        return False

    enriched = _enrich(event)
    attempts = len(_RETRY_BACKOFFS) + 1
    for i in range(attempts):
        try:
            _post_event(enriched)
            _debug(
                f"sent {enriched.get('event_type')} for {enriched.get('project_slug')}"
            )
            return True
        except Exception as exc:  # noqa: BLE001
            if _is_permanent_failure(exc):
                _debug(f"permanent failure, dropping event: {exc}")
                return True  # poison pill — final, never retry
            _debug(f"error sending event (attempt {i + 1}/{attempts}): {exc}")
            if i < len(_RETRY_BACKOFFS):
                time.sleep(_RETRY_BACKOFFS[i])

    return _persist_pending_event(enriched)


def flush_pending_events() -> None:
    """POST any events persisted in ~/.lodge/pending_events/ (ADR-0058).

    One attempt per file; delete on success; drop 4xx poison files; stop at the
    first transient failure so a Lodge outage doesn't stall the caller by
    churning every pending file × timeout. Never raises.
    """
    if not is_telemetry_enabled():
        return
    try:
        pending_dir = _pending_dir()
        if not pending_dir.is_dir():
            return
        files = sorted(pending_dir.glob("*.json"))
    except Exception as exc:  # nosec B110  # noqa: BLE001
        _debug(f"failed to list pending events: {exc}")
        return

    for path in files:
        try:
            enriched = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            _debug(f"dropping unreadable pending event {path.name}: {exc}")
            _unlink_quietly(path)
            continue
        try:
            _post_event(enriched)
            _debug(f"flushed pending event {path.name}")
            _unlink_quietly(path)
        except Exception as exc:  # noqa: BLE001
            if _is_permanent_failure(exc):
                _debug(f"dropping poison pending event {path.name}: {exc}")
                _unlink_quietly(path)
                continue
            _debug(f"flush stopped, Lodge unavailable: {exc}")
            return  # transient — leave this and the rest for next run


def send_event(event: dict[str, Any]) -> None:
    """
    Fire-and-forget POST of *event* to the telemetry service.

    Returns immediately. Swallows all exceptions. No-op when telemetry
    is disabled (AGENTIC_TELEMETRY_URL not set).
    """
    if not is_telemetry_enabled():
        return

    enriched = _enrich(event)

    def _fire() -> None:
        try:
            _post_event(enriched)
            _debug(
                f"sent {enriched.get('event_type')} for {enriched.get('project_slug')}"
            )
        except Exception as exc:  # noqa: BLE001
            _debug(f"error sending event: {exc}")

    t = threading.Thread(target=_fire, daemon=True)
    t.start()
