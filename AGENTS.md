# AGENTS.md — siddur (Archaeology)
**READ THIS FIRST. Every agent, every session, no exceptions.**

## 1. Project Mandate
* **Repository:** `github.com/ElCuboNegro/siddur`
* **Description:** Legacy system archaeology project — reverse-engineer, document, and modernize
* **Core Objective:** Reverse-engineer the legacy system bottom-up, document every behavior as executable Gherkin specs, and hand off a complete behavioral contract to the forward-TDD team.


## 2. Universal Rules
- **ADR-First:** Write an ADR in `docs/adr/` before any architectural conclusion is documented.
- **ADR Reserve-First Protocol:** Before writing an ADR, reserve its number on the `adrs` ledger branch first:
  ```bash
  git worktree add /tmp/adrs-ledger adrs
  echo "# ADR-NNNN — reserved" > /tmp/adrs-ledger/docs/adr/ADR-NNNN-<title>.md
  git -C /tmp/adrs-ledger add docs/adr/ADR-NNNN-<title>.md
  git -C /tmp/adrs-ledger commit --no-verify -m "chore: reserve ADR-NNNN — <title>"
  git push origin adrs          # fast-forward rejection = number taken — bump and retry
  git worktree remove /tmp/adrs-ledger
  ```
  Then write the full ADR on your feature branch using the reserved number.
- **ADR Gate Bypass:** For trivial fixes (bug, typo, formatting), add `[skip-adr]` as a comment in your staged change to bypass the gate. Every bypass is logged to `.adr-gate-bypasses.log`.
- **Bottom-Up Protocol:** Analysis MUST start from leaf procedures, not entry points.
- **Traceability Mandate:** Every legacy function excavated must land in `docs/knowledge/`.
- **Knowledge-First:** Before starting any sub-task, `retrieve_memory` for prior findings on the same domain.
- **Never Destroy:** Do not modify the original legacy source under analysis. Document, never overwrite.

## 3. Context Routing
| Working in...                    | Load before acting                                          |
|----------------------------------|-------------------------------------------------------------|
| `input/` (legacy binaries/code)  | `.agents/skills/software/discovery/software-archeologist/SKILL.md` |
| COBOL or mainframe code          | `.agents/skills/software/discovery/cobol-analyst/SKILL.md`  |
| Unknown/obfuscated domain        | `.agents/skills/software/discovery/unknown-domain-protocol/SKILL.md` |
| Retro-engineering DLLs or native | `.agents/skills/software/discovery/retro-engineer/SKILL.md` |
| Writing behavioral specs         | `.agents/skills/software/quality/bdd-writer/SKILL.md`       |
| Verifying behavior hypotheses    | `.agents/skills/software/quality/characterization-tester/SKILL.md` |
| Reviewing findings documents     | `.agents/skills/software/quality/code-reviewer/SKILL.md`    |
| Persisting learnings             | `.agents/skills/core/learning-protocol/SKILL.md`            |

## 3a. Universal Agent Runtime Rules
- **Memory-first:** Before acting, check `docs/knowledge/` and `output/` for prior session state.
- **3-tier model routing:** Trivial (search, grep) → no LLM; Simple → Haiku; Complex (architecture, unknown domain) → Sonnet/Opus.
- **Concurrency mandate:** Run independent sub-tasks in parallel whenever possible.
- **Anti-drift:** After every 10 sub-tasks, verify alignment with the original excavation goal.

## 4. Archaeology Workflow

```
Legacy Input
 ├── 1. software-archeologist   → map entry points, call trees, data flows
 ├── 2. specialist analysts     → domain-specific deep analysis
 │    ├── cobol-analyst         (mainframe/COBOL)
 │    ├── retro-engineer        (native DLLs, compiled binaries)
 │    └── unknown-domain-protocol (anything else)
 ├── 3. characterization-tester → verify behavior hypotheses with real system
 ├── 4. bdd-writer              → convert findings into Gherkin .feature files
 ├── 5. learning-protocol       → persist all patterns to docs/knowledge/
 └── 6. HANDOFF                 → export to forward team (see §5)
```

## 5. Knowledge Handoff to Forward Team

When an excavation is complete, export artifacts to `output/handoff/`:

```
output/handoff/
├── features/          ← .feature files ready for forward team to implement
├── knowledge/         ← domain concepts, data models, decision trees
├── adr/               ← architectural decisions discovered in legacy code
└── HANDOFF.md         ← summary + open questions + risk areas
```


See `docs/knowledge/KNOWLEDGE_BRIDGE.md` for the shared knowledge protocol.


## Token Optimisation (RTK)

RTK (Rust Token Killer) is enabled for this project. It reduces LLM token consumption
by 60–90% by filtering verbose command output before it enters the agent context window.

**Activate for this session:**
```bash
source activate_rtk.sh   # scope=project (recommended)
```
*Or, if globally initialised:* ensure `cornerstone rtk init --scope global` was run.

| Command | Purpose |
|---------|---------|
| `cornerstone rtk status` | Check installation, version, and alias state |
| `cornerstone rtk install --method binary --version <pinned>` | Install / reinstall binary |
| `cornerstone rtk init --scope project` | (Re-)generate `activate_rtk.sh` |
| `cornerstone rtk uninstall` | Remove aliases and activation script |

See `cornerstone rtk status --json` for machine-readable health output.


## Branch workflow

Use `cornerstone flow` (feature/release/hotfix `start`·`publish`·`finish`), **not** raw `git checkout -b` / `git push` / `gh pr create`. It enforces `feature/` naming, base `staging`, and the pre-push gates (ADR-0036/0077/0117).

```bash
cornerstone flow feature start <name>   # feature/<name> off staging
cornerstone flow feature publish        # push to origin
cornerstone flow feature finish [name]  # integrate (default: current branch)
```

Gitflow is `feature/* → staging → main`; `main` is PR-only and merges only from `staging`/`hotfix/*` (ADR-0107).
