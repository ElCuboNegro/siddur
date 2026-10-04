"""Unit tests for tools/migration_sequence_gate.py (ADR-0167).

Runs in the generated project (tools/ at repo root) and in place in the
schematics template source (tools/ is a sibling of tests/).
"""

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import migration_sequence_gate as gate  # noqa: E402


# --------------------------------------------------------------------------- #
# _extract_revision — symbol parsing (INV-1)
# --------------------------------------------------------------------------- #
def test_extract_linear_child():
    src = 'revision = "0002"\ndown_revision = "0001"\n'
    assert gate._extract_revision(src) == ("0002", ("0001",))


def test_extract_base_none_down():
    src = 'revision = "0001"\ndown_revision = None\n'
    assert gate._extract_revision(src) == ("0001", ())


def test_extract_merge_tuple_and_list():
    assert gate._extract_revision('revision="m"\ndown_revision=("a","b")')[1] == ("a", "b")
    assert gate._extract_revision('revision="m"\ndown_revision=["a","b"]')[1] == ("a", "b")


def test_extract_syntax_error_is_ignored():
    assert gate._extract_revision("def (:\n") == (None, ())


def test_extract_non_string_revision():
    assert gate._extract_revision("revision = 123\n") == (None, ())


def test_extract_ignores_non_assign_nodes():
    # An import / def at module level is skipped (not an assignment).
    src = "import os\ndef f():\n    pass\nrevision = '0001'\ndown_revision = None\n"
    assert gate._extract_revision(src) == ("0001", ())


def test_extract_non_literal_down_revision_is_empty():
    # down_revision bound to a name/expression (not a literal) -> ().
    assert gate._extract_revision("revision = 'm'\ndown_revision = some_var\n") == ("m", ())


# --------------------------------------------------------------------------- #
# load_revmap
# --------------------------------------------------------------------------- #
def _write(versions: Path, name: str, revision: str, down: str) -> None:
    versions.mkdir(parents=True, exist_ok=True)
    (versions / name).write_text(
        f'revision = "{revision}"\ndown_revision = {down}\n', encoding="utf-8"
    )


def test_load_revmap_parses_and_skips_init(tmp_path):
    v = tmp_path / "versions"
    _write(v, "0001_a.py", "0001", "None")
    _write(v, "0002_b.py", "0002", '"0001"')
    (v / "__init__.py").write_text("", encoding="utf-8")
    revmap, dups = gate.load_revmap(v)
    assert revmap == {"0001": (), "0002": ("0001",)}
    assert dups == []


def test_load_revmap_detects_duplicates(tmp_path):
    v = tmp_path / "versions"
    _write(v, "a.py", "dup", "None")
    _write(v, "b.py", "dup", "None")
    revmap, dups = gate.load_revmap(v)
    assert dups == ["dup"] and set(revmap) == {"dup"}


def test_load_revmap_skips_file_without_revision(tmp_path):
    v = tmp_path / "versions"
    v.mkdir(parents=True)
    (v / "not_a_migration.py").write_text("x = 1\n", encoding="utf-8")  # no revision symbol
    _write(v, "0001.py", "0001", "None")
    revmap, dups = gate.load_revmap(v)
    assert revmap == {"0001": ()} and dups == []


# --------------------------------------------------------------------------- #
# check_graph — L1 pure logic
# --------------------------------------------------------------------------- #
def test_graph_empty_passes():
    assert gate.check_graph({}, []) == []


def test_graph_single_chain_passes():
    assert gate.check_graph({"1": (), "2": ("1",), "3": ("2",)}, []) == []


def test_graph_distinct_prefix_passes():  # INV-1
    revmap = {"0021": (), "0022_infra": ("0021",), "0022_health": ("0022_infra",)}
    assert gate.check_graph(revmap, []) == []


def test_graph_multiple_heads_blocks_with_merge_hint():  # INV-5
    errs = gate.check_graph({"1": (), "2a": ("1",), "2b": ("1",)}, [])
    assert errs and "alembic merge" in " ".join(errs)


def test_graph_missing_parent_blocks():
    errs = gate.check_graph({"2": ("1",)}, [])
    assert errs and "missing" in " ".join(errs)


def test_graph_duplicate_blocks():
    errs = gate.check_graph({"1": ()}, ["1"])
    assert errs and "duplicate" in " ".join(errs)


def test_graph_detached_revision_blocks():
    # A cycle a<->b is unreachable from the single head '2' (neither is a head).
    revmap = {"1": (), "2": ("1",), "a": ("b",), "b": ("a",)}
    errs = gate.check_graph(revmap, [])
    assert errs and "detached" in " ".join(errs)


def test_heads_helper():
    assert gate._heads({"1": (), "2": ("1",)}) == {"2"}


# --------------------------------------------------------------------------- #
# check_superset & pair_is_governed — L2 pure logic
# --------------------------------------------------------------------------- #
def test_superset_ok():
    assert gate.check_superset({"1", "2"}, {"1", "2", "3"}, "main", "staging") == []


def test_superset_behind_blocks():  # the 2026-07-29 incident (INV-2)
    errs = gate.check_superset({"0024", "0025"}, {"0024"}, "main", "staging")
    assert errs and "BEHIND" in errs[0] and "0025" in errs[0]


@pytest.mark.parametrize(
    "base,head,expected",
    [
        ("main", "staging", True),
        ("main", "hotfix/x", True),
        ("main", "release/1.2", True),
        ("main", "feature/x", False),
        ("staging", "feature/x", False),
    ],
)
def test_pair_is_governed(base, head, expected):
    assert gate.pair_is_governed(base, head) is expected


# --------------------------------------------------------------------------- #
# Git-backed integration: run_promotion, _revs_at_ref, _materialize_versions
# --------------------------------------------------------------------------- #
def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-b", "main")
    _git(r, "config", "user.email", "t@t.io")
    _git(r, "config", "user.name", "t")
    _write(r / gate.VERSIONS_PATH, "0024.py", "0024", "None")
    _write(r / gate.VERSIONS_PATH, "0025.py", "0025", '"0024"')
    _git(r, "add", "-A")
    _git(r, "commit", "-m", "base with 0024+0025")
    monkeypatch.chdir(r)
    return r


def test_run_promotion_head_behind_base_blocks(repo, capsys):
    # main has 0024+0025; staging branch drops 0025 (the incident shape).
    _git(repo, "checkout", "-b", "staging")
    (repo / gate.VERSIONS_PATH / "0025.py").unlink()
    _git(repo, "commit", "-am", "drop 0025")
    assert gate.run_promotion("main", "staging") == 1
    assert "BEHIND" in capsys.readouterr().err


def test_run_promotion_superset_passes(repo):
    _git(repo, "checkout", "-b", "staging")
    _write(repo / gate.VERSIONS_PATH, "0026.py", "0026", '"0025"')
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "add 0026")
    assert gate.run_promotion("main", "staging") == 0


def test_run_promotion_non_governed_skips(repo, capsys):
    assert gate.run_promotion("main", "feature/x") == 0
    assert "not a governed pair" in capsys.readouterr().out


def test_run_promotion_no_migration_changes_passes(repo):
    _git(repo, "checkout", "-b", "staging")
    (repo / "README.md").write_text("x", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "docs only")
    assert gate.run_promotion("main", "staging") == 0


def test_run_promotion_missing_base_ref_fails_closed(repo, capsys):  # INV-3
    # 'staging' is a governed head but the branch was never created -> the tree
    # cannot be materialized -> fail closed (never silently pass).
    assert gate.run_promotion("main", "staging") == 1
    assert "FAILED CLOSED" in capsys.readouterr().err


# --------------------------------------------------------------------------- #
# run_graph & main
# --------------------------------------------------------------------------- #
def test_run_graph_skips_without_versions(tmp_path, monkeypatch, capsys):
    _git(tmp_path, "init", "-b", "main")
    (tmp_path / "f").write_text("x", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "-c", "user.email=t@t.io", "-c", "user.name=t", "commit", "-m", "x")
    monkeypatch.chdir(tmp_path)
    assert gate.run_graph() == 0
    assert "SKIP" in capsys.readouterr().out


def test_run_graph_passes_on_valid_tree(repo):
    assert gate.run_graph() == 0


def test_run_graph_blocks_on_multi_head(repo, capsys):
    _write(repo / gate.VERSIONS_PATH, "0025b.py", "0025b", '"0024"')  # second head off 0024
    assert gate.run_graph() == 1
    assert "BLOCKED" in capsys.readouterr().err


def test_main_check_graph_dispatch(repo):
    assert gate.main(["--check-graph"]) == 0


def test_main_pre_commit_alias(repo):
    assert gate.main(["--pre-commit"]) == 0


def test_main_promotion_requires_base(repo):
    with pytest.raises(SystemExit):
        gate.main(["--check-promotion"])


def test_main_promotion_dispatch(repo):
    assert gate.main(["--check-promotion", "--base", "main", "--head", "feature/x"]) == 0


def test_main_promotion_with_explicit_refs(repo):
    # Governance names main<-staging, but materialize main against itself: trivial pass.
    rc = gate.main(
        [
            "--check-promotion",
            "--base",
            "main",
            "--head",
            "staging",
            "--base-ref",
            "main",
            "--head-ref",
            "main",
        ]
    )
    assert rc == 0


# --------------------------------------------------------------------------- #
# Review fixes: zero-head (#3), first-migration base (#2), merge-fix (F4),
# branch-tip vs merge-commit (F1 regression)
# --------------------------------------------------------------------------- #
def test_graph_zero_head_cycle_blocks():  # F2/#3
    errs = gate.check_graph({"a": ("b",), "b": ("a",)}, [])
    assert errs and "no Alembic head" in " ".join(errs)


def test_graph_merge_migration_resolves_multi_head():  # INV-5 / F4
    # Two heads off '1', then a merge revision with a tuple down_revision -> single head, passes.
    two_heads = {"1": (), "2a": ("1",), "2b": ("1",)}
    assert gate.check_graph(two_heads, [])  # blocked before the merge
    merged = {**two_heads, "m": ("2a", "2b")}
    assert gate.check_graph(merged, []) == []  # merge migration resolves it


def test_run_promotion_base_has_no_migrations_passes(tmp_path, monkeypatch):  # #2
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-b", "main")
    _git(r, "config", "user.email", "t@t.io")
    _git(r, "config", "user.name", "t")
    (r / "README.md").write_text("x", encoding="utf-8")  # main has NO migrations
    _git(r, "add", "-A")
    _git(r, "commit", "-m", "init, no migrations")
    _git(r, "checkout", "-b", "staging")
    _write(r / gate.VERSIONS_PATH, "0001.py", "0001", "None")  # first-ever migration
    _git(r, "add", "-A")
    _git(r, "commit", "-m", "first migration")
    monkeypatch.chdir(r)
    assert gate.run_promotion("main", "staging") == 0  # base empty-set, not fail-closed


def test_run_promotion_uses_branch_tip_not_merge_commit(tmp_path, monkeypatch):  # F1 regression
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-b", "main")
    _git(r, "config", "user.email", "t@t.io")
    _git(r, "config", "user.name", "t")
    _write(r / gate.VERSIONS_PATH, "0024.py", "0024", "None")
    _git(r, "add", "-A")
    _git(r, "commit", "-m", "0024")
    _git(r, "checkout", "-b", "staging")  # staging branches BEFORE 0025 -> behind
    _git(r, "checkout", "main")
    _write(r / gate.VERSIONS_PATH, "0025.py", "0025", '"0024"')  # main advances
    _git(r, "add", "-A")
    _git(r, "commit", "-m", "0025")
    # Simulate refs/pull/N/merge: a merge of staging+main (contains 0025).
    _git(r, "checkout", "-b", "prmerge", "staging")
    _git(r, "merge", "--no-edit", "main")
    monkeypatch.chdir(r)
    # The merge commit hides the gap (base ⊆ merge) -> FALSE pass (why CI must NOT use it).
    assert gate.run_promotion("main", "staging", base_ref="main", head_ref="prmerge") == 0
    # The real branch tip is behind -> correctly BLOCKS (what the fixed CI wiring does).
    assert gate.run_promotion("main", "staging", base_ref="main", head_ref="staging") == 1
