#!/usr/bin/env python3
# ADR: 0062
"""Reset legacy registry entries so the catchup cron re-reports them.

Run AFTER the ADR-0062 purge migration has deployed. Registry entries marked
with the legacy ``true`` value belong to sessions reported (or silently
dropped) by the pre-ADR-0061 hook; their server rows were purged, so they are
reset to ``{"done": false}`` and the catchup cron re-reports them with correct
attribution, delta semantics and session_id. Watermarked (post-fix) entries
are left untouched — their events survived the purge and resetting them would
double-count.

Usage: python3 reset_legacy_registry.py [--apply]   (default: dry-run)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def reset_legacy_entries(registry: dict, existing: set[str]) -> dict:
    """Return {path: new_entry} for legacy-true entries whose transcript exists."""
    return {
        key: {"done": False}
        for key, value in registry.items()
        if value is True and key in existing
    }


def main() -> int:
    apply = "--apply" in sys.argv
    registry_path = Path.home() / ".cornerstone" / "processed_transcripts.json"
    if not registry_path.exists():
        print("no registry found — nothing to do")
        return 0
    registry = json.loads(registry_path.read_text(encoding="utf-8"))

    transcripts_dir = Path.home() / ".claude" / "projects"
    existing = (
        {str(p) for p in transcripts_dir.rglob("*.jsonl")}
        if transcripts_dir.exists()
        else set()
    )

    resets = reset_legacy_entries(registry, existing)
    print(f"{len(resets)} legacy entries with a transcript still on disk")
    if not apply:
        print("dry-run — pass --apply to reset them (deploy the ADR-0062 purge FIRST)")
        return 0

    registry.update(resets)
    tmp = registry_path.with_suffix(".json.reset-tmp")
    tmp.write_text(json.dumps(registry, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(registry_path)
    print("reset applied — the catchup cron will re-report them (<=15 min)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
