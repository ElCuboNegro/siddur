"""
Unit tests for .telemetry SDK.

Run with: pytest tests/test_telemetry.py -v
No network calls are made — urllib.request.urlopen is mocked.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch
import importlib.util
from pathlib import Path
import types

# --- Hack to load .telemetry modules since Python doesn't support dot-prefixed directories natively ---
telemetry_dir = Path(__file__).parent.parent / ".telemetry"
telemetry_pkg = types.ModuleType("telemetry")
telemetry_pkg.__path__ = [str(telemetry_dir)]
telemetry_pkg.__package__ = "telemetry"
sys.modules["telemetry"] = telemetry_pkg

for mod in ["client", "cost_rates", "schema", "decorators", "otel"]:
    spec = importlib.util.spec_from_file_location(f"telemetry.{mod}", telemetry_dir / f"{mod}.py")
    module = importlib.util.module_from_spec(spec)
    module.__package__ = "telemetry"
    sys.modules[f"telemetry.{mod}"] = module
    setattr(telemetry_pkg, mod, module)

for mod in ["client", "cost_rates", "schema", "decorators", "otel"]:
    sys.modules[f"telemetry.{mod}"].__spec__.loader.exec_module(sys.modules[f"telemetry.{mod}"])

import telemetry.client as client
import telemetry.cost_rates as cost_rates
import telemetry.decorators as decorators
import telemetry.schema as schema

def _reload_client(env: dict) -> object:
    with patch.dict("os.environ", env, clear=True):
        spec = importlib.util.spec_from_file_location("telemetry.client", telemetry_dir / "client.py")
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = "telemetry"
        spec.loader.exec_module(mod)
        return mod

def test_no_op_when_env_var_absent():
    # cornerstone ADR-0230 / cornerstone#1255: is_telemetry_enabled() answers
    # "set in env OR local config", so clearing os.environ is not isolation. On
    # every machine where telemetry actually works, `.telemetry/.env.lodge`
    # (Lodge-delivered, ADR-0198) still answers and this test failed — it passed
    # only where telemetry was broken. Both sources have to be silenced here.
    with (
        patch.dict("os.environ", {}, clear=True),
        patch.object(client, "_read_url_from_local_config", return_value=""),
    ):
        assert not client.is_telemetry_enabled()
        with patch("urllib.request.urlopen") as mock_open:
            client.send_event({"event_type": "skill.invoked", "project_slug": "test"})
            import time
            time.sleep(0.05)
            mock_open.assert_not_called()

def test_enabled_from_local_config_without_env_var():
    """The normal runtime shape: no env var, URL delivered in local config."""
    with (
        patch.dict("os.environ", {}, clear=True),
        patch.object(
            client, "_read_url_from_local_config", return_value="https://lodge.invalid"
        ),
    ):
        assert client.is_telemetry_enabled()

def test_sends_when_env_var_set():
    import os
    os.environ["AGENTIC_TELEMETRY_URL"] = "http://localhost:9999"
    try:
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_response) as mock_open:
            # `send_event` dispatches to a background thread that first resolves
            # git context via subprocesses and may attempt an IAP token mint, then
            # retries with 0.5/1.0/2.0s backoffs. Sleeping 100ms and asserting was
            # a race the test lost on every host — which is why every generated
            # project shipped with this failing. `send_event_sync` is the seam the
            # module documents for exactly this, with the backoffs disabled so a
            # single attempt is made and nothing sleeps.
            client._RETRY_BACKOFFS = ()
            client.send_event_sync({
                "event_type": "skill.invoked",
                "project_slug": "my-project",
                "github_username": "myuser",
                "timestamp": "2026-03-17T00:00:00Z",
                "schema_version": "1.0",
                "payload": {},
            })
            assert mock_open.called
            req_arg = mock_open.call_args[0][0]
            assert req_arg.full_url == "http://localhost:9999/v1/events"
            assert req_arg.get_header("Content-type") == "application/json"
    finally:
        os.environ.pop("AGENTIC_TELEMETRY_URL", None)

def test_swallows_network_errors():
    import os
    import time
    os.environ["AGENTIC_TELEMETRY_URL"] = "http://unreachable.invalid"
    try:
        with patch("urllib.request.urlopen", side_effect=ConnectionRefusedError("refused")):
            client.send_event({"event_type": "test", "project_slug": "p"})
            time.sleep(0.1)
    finally:
        os.environ.pop("AGENTIC_TELEMETRY_URL", None)

def test_cost_estimation_claude_sonnet():
    cost = cost_rates.estimate_cost("claude-sonnet-4-6", input_tokens=1_000_000, output_tokens=1_000_000)
    assert cost == 18.0

def test_cost_estimation_precise():
    cost = cost_rates.estimate_cost("claude-sonnet-4-6", input_tokens=1_000, output_tokens=500)
    assert cost == round((1_000 * 3.00 + 500 * 15.00) / 1_000_000, 8)

def test_cost_estimation_unknown_model():
    # The model name must match no family prefix. "gpt-99-ultra" used to be the
    # subject here and stopped being unknown on 2026-06-10, when the longest-
    # prefix FAMILY_RATES fallback was added so a model missing from the table
    # degrades to an approximate cost instead of a silent $0. It matched the
    # `gpt` family and returned a price, so this assertion had been failing in
    # every generated project ever since.
    assert cost_rates.estimate_cost("zzz-nonexistent-9000", 100, 50) is None


def test_cost_estimation_falls_back_to_family_for_unlisted_model():
    """The behaviour the 2026-06-10 incident added: never a silent $0."""
    cost = cost_rates.estimate_cost("gpt-99-ultra", 100, 50)
    assert cost is not None and cost > 0

def test_skill_span_decorator():
    import os
    os.environ["AGENTIC_TELEMETRY_URL"] = "http://localhost:9999"
    try:
        events_sent: list[dict] = []
        with patch.object(decorators, "send_event", side_effect=events_sent.append):
            @decorators.skill_span("test-skill", ".agents/skills/test/SKILL.md")
            def my_skill(model: str = "claude-sonnet-4-6", input_tokens: int = 100, output_tokens: int = 50):
                return "done"
            result = my_skill(model="claude-sonnet-4-6", input_tokens=100, output_tokens=50)
        assert result == "done"
        assert len(events_sent) == 1
        evt = events_sent[0]
        assert evt["event_type"] == "skill.invoked"
        assert evt["payload"]["skill_name"] == "test-skill"
        assert evt["payload"]["model"] == "claude-sonnet-4-6"
    finally:
        os.environ.pop("AGENTIC_TELEMETRY_URL", None)

def test_tool_span_decorator():
    import os
    os.environ["AGENTIC_TELEMETRY_URL"] = "http://localhost:9999"
    try:
        events_sent: list[dict] = []
        with patch.object(decorators, "send_event", side_effect=events_sent.append):
            @decorators.tool_span("sql_topology", "tools/software/discovery/sql_topology.py")
            def run_tool():
                return 42
            result = run_tool()
        assert result == 42
        assert len(events_sent) == 1
        evt = events_sent[0]
        assert evt["event_type"] == "tool.executed"
        assert evt["payload"]["tool_name"] == "sql_topology"
    finally:
        os.environ.pop("AGENTIC_TELEMETRY_URL", None)

def test_project_generated_event_schema():
    payload = schema.ProjectGeneratedPayload(
        python_version="3.11",
        template_version="1.0.0",
        cookiecutter_vars={"project_name": "My Project", "project_slug": "my-project"},
    )
    event = schema.make_event("project.generated", "my-project", "myuser", payload)
    assert event["event_type"] == "project.generated"
    assert event["project_slug"] == "my-project"
    assert event["payload"]["python_version"] == "3.11"


# ---------------------------------------------------------------------------
# SDLC phase resolution (ADR-0079) — env var > .telemetry/.phase marker > None
# ---------------------------------------------------------------------------


def _fresh_stop_reporter() -> object:
    """Load a pristine stop_reporter module so its per-process phase cache resets."""
    spec = importlib.util.spec_from_file_location(
        "telemetry_stop_reporter_fresh", telemetry_dir / "stop_reporter.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_current_phase_from_env():
    with patch.dict("os.environ", {"LODGE_SDLC_PHASE": "ci"}, clear=False):
        sr = _fresh_stop_reporter()
        assert sr._current_phase() == "ci"


def test_current_phase_from_marker():
    import os
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / ".telemetry").mkdir()
        (Path(tmp) / ".telemetry" / ".phase").write_text("architecture\n", encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if k != "LODGE_SDLC_PHASE"}
        cwd = os.getcwd()
        try:
            os.chdir(tmp)
            with patch.dict("os.environ", env, clear=True):
                sr = _fresh_stop_reporter()
                assert sr._current_phase() == "architecture"
        finally:
            os.chdir(cwd)


def test_current_phase_env_overrides_marker():
    import os
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / ".telemetry").mkdir()
        (Path(tmp) / ".telemetry" / ".phase").write_text("architecture\n", encoding="utf-8")
        cwd = os.getcwd()
        try:
            os.chdir(tmp)
            with patch.dict("os.environ", {"LODGE_SDLC_PHASE": "review"}, clear=False):
                sr = _fresh_stop_reporter()
                assert sr._current_phase() == "review"
        finally:
            os.chdir(cwd)


def test_current_phase_none_when_unset():
    import os
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        env = {k: v for k, v in os.environ.items() if k != "LODGE_SDLC_PHASE"}
        cwd = os.getcwd()
        try:
            os.chdir(tmp)
            with patch.dict("os.environ", env, clear=True):
                sr = _fresh_stop_reporter()
                assert sr._current_phase() is None
        finally:
            os.chdir(cwd)
