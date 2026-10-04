## Mandatory Initialization — Every Session, No Exceptions

**Step 1 — Read AGENTS.md**
Read `AGENTS.md` immediately. It is the Supreme Mandate for this project.

**Step 2 — Verify environment**
Check if `.venv` exists. If not, run:
```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cornerstone --mode runtime init
cornerstone --mode runtime sync
```

**Step 3 — Load context file**
Run `git status --porcelain | awk '{print $2}' | head -20`, then apply the routing table in AGENTS.md to load the correct context file.

**Step 4 — GitOps & Commit Policies**
- **Gitflow:** Follow Gitflow (main/staging).
- **Semantic Versioning:** Adhere to Semantic Versioning.
- **Commits:** Use Atomic and Conventional Commits.


**Step 5 — Hooks**
Run `cornerstone hooks install --dir ~` to register this project's Lodge Stop hook in the global Claude/Gemini configuration. This ensures session costs are reported correctly even when a session starts outside this project's folder.

Do not proceed until all five steps are complete.

# siddur — Archaeology Project

## What This Is
Legacy system archaeology project — reverse-engineer, document, and modernize

This project reverse-engineers the legacy system and produces a behavioral contract
(Gherkin `.feature` files + `docs/knowledge/`) that the forward-TDD team uses to
implement the modern replacement.

## Key Directories
- `input/` — legacy artifacts under analysis (binaries, source, exports)
- `output/` — analysis results (reports, BDD specs, characterization tests)
- `docs/knowledge/` — persistent knowledge database (shared with forward team)
- `docs/adr/` — architectural decisions discovered in legacy code

## Commands
- **Run characterization tests:** `pytest tests/ -v --tb=short`
- **View all findings:** `cat output/retro-report.md`
- **Sync knowledge to forward team:** see `docs/knowledge/KNOWLEDGE_BRIDGE.md`

## Core Directives
Read @AGENTS.md for full routing directives and the archaeology workflow.

## First Steps
1. Drop legacy artifacts into `input/`
2. Update `context/run_context.md` with what you know about the system
3. Invoke `software-archeologist` skill to begin the excavation
