---
name: ADR proposal (design decision)
about: Propose and request comments on an architectural decision
title: '<Title>'
labels: 'architecture'
assignees: ''

---

> [!IMPORTANT]
> ADRs are **GitHub Discussions** in the `ADR` category — that is the canonical record
> (numbering is automatic, `max+1`). Use this issue only to *socialise* a proposal or track
> the work of writing it. Create the real ADR with:
> ```
> cornerstone adr new "<title>"
> ```
> ADRs are immutable once accepted: supersede, never edit (`cornerstone adr supersede <old> <new>`).

## Introduction
<!-- High-level, short overview of the problem being solved. -->

## Background
<!-- Context surrounding the problem. What exists today? -->

## Problem

### In scope

### Not in scope

## Design
<!-- The proposed solution. Diagrams welcome (mermaid renders on GitHub). -->

### Alternatives considered
<!-- Trade-offs between alternatives. An ADR without rejected options is not an ADR. -->

## Testing
<!-- How will correctness be verified? For legacy behaviour, does this need a
     characterization test to lock in current behaviour first? -->

## Rollout strategy
<!-- Backward compatible? If not, what is the migration path? -->

## Future iterations

## Checklist

- [ ] Searched the KDB first (`kdb_search`) — this decision may already be documented
- [ ] Checked for a conflicting existing ADR (`cornerstone adr list`)
- [ ] Linked the ADR Discussion here once opened
