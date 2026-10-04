## Description
<!-- Why was this PR created? -->

## Development notes
<!-- What changed, and how was it tested? -->

> [!IMPORTANT]
> Every PR should link to a GitHub issue, or to the ADR Discussion that authorised the change.
> Architectural changes without an ADR will be blocked by the ADR gate — write the ADR first.

Closes #

## Checklist

### Gates (see `.agents/AGENTS.gates.md`)

- [ ] **ADR-first** — architectural changes have an ADR Discussion, referenced as `# ADR: NNNN`
      in the changed files. Trivial fix? Use a typed bypass (`[skip-adr: trivial]`) — every
      bypass is logged to `.adr-gate-bypasses.log`
- [ ] **Learning protocol** — new findings recorded in `docs/knowledge/FINDINGS.md` (next
      sequential `F-XXX`) and appended to `docs/knowledge/learning_log.md`
- [ ] **Knowledge-first** — queried the KDB (`kdb_search`) before designing; reuse beats
      re-derivation
- [ ] `pre-commit run --all-files` passes
- [ ] Test suite passes (`pytest tests/ -v --tb=short`)

### Archaeology-specific

- [ ] **`input/` is untouched** — the Never Destroy mandate. Verify with `git status`:
      nothing under `input/` may appear as modified or deleted
- [ ] Generated specs carry an explicit maturity marker: `# status: hypothesis` until the
      `characterization-tester` verifies them, then `# status: verified`
- [ ] Every excavated behaviour cites evidence (`file:line`), not prose
- [ ] Verified specs are not silently edited — a verified `.feature` is a contract and needs
      team review to change

### Security

- [ ] No credentials, tokens, API keys or secrets in the diff — including in tests and
      fixtures. Secrets found in legacy source are reported **by location only**
      (`SECRET FOUND — <file>:<line> — <type>, value redacted`)
- [ ] No PII or production configuration (GCP project ids, buckets, internal hostnames,
      corporate emails) in code, specs or fixtures — use generic doubles
- [ ] Security-sensitive change? Ran the `security-expert` / `code-reviewer` skill over the diff

### Conventions

- [ ] Conventional Commits in English (`feat:`, `fix:`, `docs:`, `refactor:`)
- [ ] Atomic commits — one logical change each
- [ ] Documentation updated to reflect the change
