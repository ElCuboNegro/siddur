# ADR: 0061 — session_id + report_kind payload fields
"""
Event schema definitions for Cornerstone telemetry.

All events share a common envelope. Payload varies by event_type.
Uses stdlib dataclasses — no external dependencies required.
"""

from __future__ import annotations

import datetime
from dataclasses import asdict, dataclass, field
from typing import Any, Optional


def _now_utc() -> str:
    return (
        datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    )


# ---------------------------------------------------------------------------
# Envelope
# ---------------------------------------------------------------------------


@dataclass
class EventEnvelope:
    event_type: str
    project_slug: str
    github_username: str
    payload: dict[str, Any]
    timestamp: str = field(default_factory=_now_utc)
    schema_version: str = "1.0"
    branch: Optional[str] = None
    commit_sha: Optional[str] = None
    pr_number: Optional[str] = None
    issue_number: Optional[str] = None
    phase: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        for key in ("branch", "commit_sha", "pr_number", "issue_number", "phase"):
            if d[key] is None:
                del d[key]
        return d


# ---------------------------------------------------------------------------
# Payload helpers
# ---------------------------------------------------------------------------


@dataclass
class ProjectGeneratedPayload:
    python_version: str
    template_version: str
    cookiecutter_vars: dict[str, Any]


@dataclass
class SkillInvokedPayload:
    skill_name: str
    skill_path: str
    model: str
    provider: str  # "anthropic" | "google" | "openai" | "unknown"
    parent_skill_name: Optional[str] = None
    tokens_input: Optional[int] = None
    tokens_output: Optional[int] = None
    tokens_cache_read: Optional[int] = None  # Anthropic prompt-cache tokens read
    tokens_cache_write: Optional[int] = None  # Anthropic prompt-cache tokens written
    estimated_cost_usd: Optional[float] = None
    duration_ms: Optional[int] = None
    client: Optional[str] = None
    # ADR-0061: transcript identity + delta semantics for auditability
    session_id: Optional[str] = None
    report_kind: Optional[str] = None


@dataclass
class CiRunPayload:
    workflow: str
    run_id: str
    ref: str
    commit_sha: str
    adr_gate_passed: bool
    tests_passed: bool
    lint_passed: bool
    duration_ms: int


@dataclass
class ToolExecutedPayload:
    tool_name: str
    tool_path: str
    duration_ms: int
    exit_code: int
    invocation_count: int = 1
    skill_name: Optional[str] = None  # skill context that invoked this tool
    session_id: Optional[str] = None  # ADR-0061


@dataclass
class KnowledgeCreatedPayload:
    kind: str  # "skill" | "adr" | "domain_doc" | "tool"
    path: str
    commit_sha: Optional[str] = None


@dataclass
class KnowledgeUsedPayload:
    kind: str  # "skill" | "domain_doc" | "tool"
    path: str
    context: Optional[str] = None


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------


def make_event(
    event_type: str,
    project_slug: str,
    github_username: str,
    payload_obj: Any,
    branch: Optional[str] = None,
    phase: Optional[str] = None,
    commit_sha: Optional[str] = None,
    issue_number: Optional[str] = None,
    pr_number: Optional[str] = None,
) -> dict[str, Any]:
    """Build a ready-to-send event dict from a typed payload dataclass.

    Attribution dimensions (all optional; omitted when unresolved):
    *branch* — the git branch (feature-level cost). *phase* — the SDLC lifecycle
    phase declared by the gates (ADR-0079). *commit_sha* — the current HEAD.
    *issue_number* — the GitHub issue the work traces to (parsed from the branch
    or commit trailers). *pr_number* — the PR for the branch. Lodge groups spend
    by each so a feature's cost rolls up to its issue/PR.
    """
    return EventEnvelope(
        event_type=event_type,
        project_slug=project_slug,
        github_username=github_username,
        payload=asdict(payload_obj),
        branch=branch,
        phase=phase,
        commit_sha=commit_sha,
        issue_number=issue_number,
        pr_number=pr_number,
    ).to_dict()
