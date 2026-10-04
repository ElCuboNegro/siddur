---
name: Archaeology finding
about: A behaviour, defect or risk discovered in the legacy system under analysis
title: '[F-XXX] <Title>'
labels: 'architecture'
assignees: ''

---

> [!IMPORTANT]
> Findings live in `docs/knowledge/FINDINGS.md` first — that ledger is the canonical record
> and the learning gate reads it. Open an issue only when the finding needs **tracked work**
> (a fix, a decision, an escalation). Link the `F-XXX` id both ways.

## Finding id
<!-- FINDINGS.md#F-XXX -->

## Subsystem
<!-- Which part of input/ this concerns, and which output/archaeology/*.md report covers it. -->

## Evidence

<!--
Every claim must be traceable. Cite file:line, never "somewhere in the codebase".
Remember `input/` is READ-ONLY (Never Destroy): document, never modify.
-->

| Claim | Evidence (`file:line`) | Confidence |
|---|---|---|
|  |  | `verified` / `hypothesis` |

## Status

- [ ] `hypothesis` — inferred from reading code, not yet executed against the live system
- [ ] `verified` — confirmed by the `characterization-tester` or an existing test

## Impact
<!-- What breaks, for whom, and how badly. If it is a security finding, align to
     ISO 27001 / NIST CSF control families and state whether exposure is live or latent. -->

## Sensitive data

> [!WARNING]
> Never reproduce a secret value, even one found hardcoded in the legacy source. Write
> `SECRET FOUND — <file>:<line> — <type>, value redacted`. Flag PII and production config
> by location; do not quote it. Rotate credentials outside of GitHub and outside of chat.

- [ ] No sensitive data referenced
- [ ] Sensitive data referenced **by location only**, no values reproduced
