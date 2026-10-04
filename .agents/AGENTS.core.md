<!-- MANAGED BY CORNERSTONE (ADR-0161). Framework-owned governance doc: do not
hand-edit in generated projects — change the canonical source in the cornerstone
repo (cornerstone/data/starters/) with its own ADR and propagate here with
`cornerstone update`. -->
# AGENTS.core.md — Universal Contract (every Stoneworks project)

Injected every session alongside AGENTS.md. These rules apply to every agent,
every session, no exceptions. AGENTS.md holds the archetype-specific mandate;
this file holds what never changes.

## Mission

Stoneworks exists to **compress delivery time and cost while maximizing
deliverable quality** — fewer architecture and design defects, no antipatterns,
maximum reuse of existing solutions. Weigh every action against those four
axes: if a step doesn't improve quality, prevent a defect, reuse something, or
save time/tokens, question it.

## Knowledge-First (ADR-0126) — reuse before re-deriving

1. BEFORE exploring the codebase or designing anything, query the KDB:
   `kdb_search("<topic>")`, `kdb_get_project_context("<project>")`,
   `kdb_list_patterns`. One query costs 2–5k tokens; re-excavating what the
   corpus already documents costs 100–500k.
2. A proposal that contradicts a documented ADR is an architecture defect.
   Check `docs/adr/` and `kdb_get_org_adr` before proposing.
3. When a new decision is confirmed or a reusable finding emerges, persist it
   (ADR, FINDINGS entry, or `kdb_ingest`). Knowledge is the only layer with
   compound ROI — never let it die with the session.
4. The KDB-first gate counts exploration calls (Grep/Glob/Task); consult the
   corpus before it trips.

## Component Boundaries (ADR-0155) — build it where it belongs

The ecosystem has fixed owners; building a capability outside its owner is an
architecture defect (the buy/reuse-over-rebuild precedent is Lodge ADR-0044):

- **Cornerstone** owns scaffolded governance: gates, hooks, `tools/`,
  workflows. Files marked `MANAGED BY CORNERSTONE` are copies — the ADR gate
  denies local edits; change `cornerstone/data/starters/` upstream (with its
  own ADR) and propagate with `cornerstone update`.
- **cornerstone-agents** owns skills (`.agents/skills/`): improve them via
  `cornerstone publish`, never by local fork.
- **Keystone** owns organizational knowledge: the shared KDB and the ADR
  corpus it ingests.
- **Lodge** owns telemetry, economics and platform settings.
- **ai-gw** owns the LLM data-plane — never build a bespoke proxy.

If your diff touches another component's responsibility, the ADR and the
change belong in the owning repo; this project's AGENTS.md §Mandate defines
what is owned HERE.

## Baseline-First

Your local clone is NOT the project's state. Before auditing or designing:
`git fetch` and compare against `origin/<branch>` (a stale local branch bakes
superseded protocols into new work); review recent ADR Discussions
(`cornerstone adr list`); and before claiming the next `F-XXX` or ADR number,
check in-flight branches/PRs and note the reservation inside the artifact
itself.

## ADR-First

Write the ADR before changing source code. ADRs are GitHub Discussions in this
repo (ADR-0128): `cornerstone adr new "<title>"` — numbering is automatic
(recipe: `.agents/AGENTS.gates.md`). `[skip-adr]` only for trivial fixes —
every bypass is logged.

## Learning Protocol (ADR-0052)

Before any commit that alters source: register findings in
`docs/knowledge/FINDINGS.md` (sequential `F-XXX`) and append to
`docs/knowledge/learning_log.md`. The learning-gate blocks the commit
otherwise; `[skip-learning]` only for trivial patches.

## Execution Economics (ADR-0123)

- **Single context by default.** Target scope under ~600k tokens (code to read
  + write) → one agent, high effort, no fan-out. Fan out ONLY above the
  threshold or for high-risk changes (security-sensitive, cross-service,
  irreversible migrations).
- **3-tier model routing.** Trivial (format, rename, search) → no LLM call;
  simple/known pattern → cheapest model; architecture, security, cross-module
  reasoning → strongest model.
- **Concurrency.** Batch ALL independent operations (file reads, searches,
  agent spawns) into a single message. Never serialize independent work.
- **Anti-drift.** With 2+ parallel agents: checkpoint alignment with the
  original goal every 10 sub-tasks; max 6 concurrent agents.
- **RTK.** If installed, run shell commands through `rtk` (60–90% output
  compression). Health: `cornerstone rtk status`.

## Quality Invariants

- Verified `.feature` files are the behavioral contract — never modify them
  without tech-lead/team review.
- No implementation without a prior failing test. Tests assert observable
  usage (inputs → outputs), never implementation internals.
- Every tool/function traces back to a `.feature` file or an explicit ADR.
- Reuse before creating: check `.agents/skills/` and the shared library
  (cornerstone-agents) before writing a new tool or skill. Duplicating an
  existing capability is a defect, not a convenience.

## GitOps & Commit Definition of Done

Gitflow (`main`/`staging`) · Semantic Versioning · atomic Conventional
Commits. A commit is NOT done until the same gates CI runs have passed
locally — CI is a mirror, not a discovery mechanism:

- Run `pre-commit run --all-files` before EVERY `git commit`.
- Changed any source file → a Gherkin `.feature` (+ step defs) must be part
  of the change-set (BDD gate) and the version must be bumped (SemVer gate).
- Never use `--no-verify` or a `[skip-*]` bypass to turn a red gate green —
  fix the cause. A global commit guard (ADR-0152) enforces this even when
  the session was born outside the repo.

Gates enforce all of this mechanically — if one blocks you, read
`.agents/AGENTS.gates.md` instead of concluding you are stuck.

## Gates Are Compliance, Not Obstacles (ADR-0049/0050)

A red gate is not a blocker to route around; it is the signal that the
deliverable does not yet meet the standard. Gates *deliver* governance — opt-in
governance is not governance, so quality is made non-optional by mechanical
verification. Read a denial as an instruction: it names the standard and the
ceremony step that satisfies it. Then **meet the standard** — the compliant path
is the fast path. A `[skip-*]` token is an *audited exception* for a genuine
emergency (reason + follow-up, logged), never how you make a gate stop
complaining. If a gate itself seems wrong, that is an ADR conversation
(`cornerstone adr new`), not a bypass.
