# Knowledge Bridge — Archaeology ↔ Forward-TDD Protocol

## Purpose

This file defines how the archaeology team (reverse-engineers) and the forward-TDD team
(implementors) share knowledge so that no insight is lost in the handoff.

Both teams write TO and read FROM this directory. It is the single source of truth
for everything known about the system under analysis.

---

## What Archaeology Produces

| Artifact | Location | Consumed by |
|----------|----------|-------------|
| Gherkin feature files | `output/handoff/features/*.feature` | tdd-developer (RED phase) |
| Domain concept glossary | `docs/knowledge/glossary.md` | All agents |
| Data model map | `docs/knowledge/data-models.md` | architect, tdd-developer |
| Decision trees | `docs/knowledge/decisions/` | tech-lead, architect |
| ADRs from legacy | `docs/adr/` | adr-writer (forward team) |
| Risk register | `docs/knowledge/risks.md` | qa-validator, tech-lead |
| Open questions | `output/handoff/HANDOFF.md` | tech-lead (next story intake) |

---

## What Forward Team Produces Back

| Artifact | Location | Consumed by |
|----------|----------|-------------|
| Implementation decisions | `docs/adr/` | archaeology team (context) |
| Failing test evidence | `tests/` | qa-validator |
| Discrepancies found | `docs/knowledge/discrepancies.md` | bdd-writer (rewrite specs) |
| Coverage gaps | `docs/knowledge/coverage-gaps.md` | characterization-tester |

---

## The Shared Glossary Protocol

Both teams MUST use the same domain language. If a term is first discovered by archaeology,
it goes into `docs/knowledge/glossary.md`. If the forward team finds a naming discrepancy,
they update the glossary and notify the archaeology team.

```markdown
## glossary.md format

### [Term]
- **Source:** [where found in legacy code]
- **Meaning:** [what it does]
- **Aliases:** [other names found for same concept]
- **Feature file:** [links to Gherkin scenario that covers this]
```

---

## Handoff Ceremony

When archaeology completes a module:
1. All `.feature` files for that module move to `output/handoff/features/`
2. `output/handoff/HANDOFF.md` is updated with open questions and risk areas
3. A GitHub issue is opened on the forward team's repo tagged `archaeology-handoff`
4. Forward team's `tech-lead` runs story intake on each feature file

When forward team discovers a discrepancy with the spec:
1. Document it in `docs/knowledge/discrepancies.md`
2. Notify archaeology team with a GitHub comment on the handoff issue
3. `bdd-writer` (archaeology side) revises the `.feature` file
4. Forward team re-runs the RED phase

---

## Learning Protocol Integration

Both teams use the same `learning-protocol` skill to write to this directory.
Never let a session end without persisting what was learned.

Pattern: "If I found X today, will the next agent need this? → Yes → Write it here."
