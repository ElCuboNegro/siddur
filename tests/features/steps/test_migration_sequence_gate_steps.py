"""BDD step definitions for tests/features/migration_sequence_gate.feature (ADR-0167)."""

import sys
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

# The gate lives in the project's tools/ directory (repo root / tools).
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
import migration_sequence_gate as gate  # noqa: E402

scenarios("../migration_sequence_gate.feature")


@pytest.fixture
def ctx():
    return {"revmap": {}, "duplicates": [], "errors": None, "governed": None}


# ---- L1 givens -------------------------------------------------------------
@given("a migration graph with a single connected chain")
def single_chain(ctx):
    ctx["revmap"] = {"0001": (), "0002": ("0001",), "0003": ("0002",)}


@given('three migrations whose files share the "0022" prefix but declare distinct revision ids')
def distinct_prefix(ctx):
    # Distinct revision ids — the shared "0022" filename prefix is irrelevant (INV-1).
    ctx["revmap"] = {"0021": (), "0022_infra": ("0021",), "0022_health": ("0022_infra",)}


@given("a migration graph with two heads")
def two_heads(ctx):
    ctx["revmap"] = {"0001": (), "0002a": ("0001",), "0002b": ("0001",)}


@given("a migration whose down_revision names a missing parent")
def missing_parent(ctx):
    ctx["revmap"] = {"0002": ("0001",)}  # 0001 absent


@given("two migrations declaring the same revision id")
def duplicate_id(ctx):
    ctx["revmap"] = {"0001": ()}
    ctx["duplicates"] = ["0001"]


@given("no migrations")
def no_migrations(ctx):
    ctx["revmap"] = {}


@given("a migration graph that is a pure cycle with no head")
def pure_cycle(ctx):
    ctx["revmap"] = {"a": ("b",), "b": ("a",)}


@given("a two-head graph plus a merge migration joining both heads")
def merge_migration(ctx):
    ctx["revmap"] = {"1": (), "2a": ("1",), "2b": ("1",), "m": ("2a", "2b")}


# ---- L2 givens -------------------------------------------------------------
@given(parsers.parse('base has revisions "{base}" and head has revisions "{head}"'))
def revision_sets(ctx, base, head):
    ctx["base_revs"] = set(base.split(","))
    ctx["head_revs"] = set(head.split(","))


# ---- whens -----------------------------------------------------------------
@when("I check graph integrity")
def check_graph(ctx):
    ctx["errors"] = gate.check_graph(ctx["revmap"], ctx["duplicates"])


@when(parsers.parse('I check promotion monotonicity from "{base}" to "{head}"'))
def check_promotion(ctx, base, head):
    ctx["governed"] = gate.pair_is_governed(base, head)
    if ctx["governed"] and "base_revs" in ctx:
        ctx["errors"] = gate.check_superset(ctx["base_revs"], ctx["head_revs"], base, head)


# ---- thens -----------------------------------------------------------------
@then("the gate passes")
def gate_passes(ctx):
    assert ctx["errors"] == [], f"expected pass, got: {ctx['errors']}"


@then("the gate blocks")
def gate_blocks(ctx):
    assert ctx["errors"], "expected the gate to block, but it passed"


@then(parsers.parse('the reason mentions "{needle}"'))
def reason_mentions(ctx, needle):
    joined = " ".join(ctx["errors"])
    assert needle in joined, f"'{needle}' not in reasons: {joined}"


@then("the pair is not governed")
def pair_not_governed(ctx):
    assert ctx["governed"] is False, "expected the pair to be non-governed"


@then("the pair is governed")
def pair_governed(ctx):
    assert ctx["governed"] is True, "expected the pair to be governed"
