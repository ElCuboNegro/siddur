Feature: Migration Sequence Gate (ADR-0167)
  As a release engineer deploying against a shared database
  I want the pipeline to prove the deployed code is never behind the DB's
  applied Alembic state
  So that a promotion or deploy can never crash at `alembic upgrade` with
  "Can't locate revision".

  # ---- Layer 1: migration-graph integrity (offline) ----------------------

  Scenario: A single valid linear chain passes
    Given a migration graph with a single connected chain
    When I check graph integrity
    Then the gate passes

  Scenario: Distinct revision ids sharing a filename prefix still pass (INV-1)
    Given three migrations whose files share the "0022" prefix but declare distinct revision ids
    When I check graph integrity
    Then the gate passes

  Scenario: Multiple heads are blocked with a merge-migration hint (INV-5)
    Given a migration graph with two heads
    When I check graph integrity
    Then the gate blocks
    And the reason mentions "alembic merge"

  Scenario: An unresolved down_revision is blocked
    Given a migration whose down_revision names a missing parent
    When I check graph integrity
    Then the gate blocks
    And the reason mentions "missing"

  Scenario: A duplicate revision id is blocked
    Given two migrations declaring the same revision id
    When I check graph integrity
    Then the gate blocks
    And the reason mentions "duplicate"

  Scenario: An empty migration set is a trivial pass (INV-4)
    Given no migrations
    When I check graph integrity
    Then the gate passes

  Scenario: A headless (cyclic) graph is blocked
    Given a migration graph that is a pure cycle with no head
    When I check graph integrity
    Then the gate blocks
    And the reason mentions "no Alembic head"

  Scenario: A merge migration resolves multiple heads (INV-5 remediation)
    Given a two-head graph plus a merge migration joining both heads
    When I check graph integrity
    Then the gate passes

  # ---- Layer 2: promotion monotonicity (offline) --------------------------

  Scenario: Head that is a superset of base passes
    Given base has revisions "0001,0002" and head has revisions "0001,0002,0003"
    When I check promotion monotonicity from "main" to "staging"
    Then the gate passes

  Scenario: Head behind base is blocked — the 2026-07-29 incident (INV-2)
    Given base has revisions "0024,0025" and head has revisions "0024"
    When I check promotion monotonicity from "main" to "staging"
    Then the gate blocks
    And the reason mentions "BEHIND"

  Scenario: A non-governed branch pair is skipped
    When I check promotion monotonicity from "main" to "feature/x"
    Then the pair is not governed

  Scenario Outline: Governed promotion pairs into main are enforced
    When I check promotion monotonicity from "main" to "<head>"
    Then the pair is governed

    Examples:
      | head        |
      | staging     |
      | hotfix/x    |
      | release/1.2 |
