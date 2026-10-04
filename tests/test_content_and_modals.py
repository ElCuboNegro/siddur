#!/usr/bin/env python3
"""
tests/test_content_and_modals.py
Validates liturgical texts, verse extraction, and modal presenter layout.
"""

import sys
import json
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def test_kiddush_content():
    print("[TEST] Testing Kiddush Shabbat content extraction...")
    path = Path(__file__).resolve().parent.parent / "content" / "samples" / "kiddush_shabbat.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["id"] == "kiddush-leil-shabbat"
    assert len(data["sections"]) == 3

    # Check verse 1
    v1 = data["sections"][0]["paragraphs"][0]["verses"][0]
    assert v1["verse_id"] == "v-1"
    assert "יוֹם הַשִּׁשִּׁי" in v1["hebrew"]
    assert "modal_details" in v1
    assert "source_reference" in v1["modal_details"]
    assert "Génesis" in v1["modal_details"]["source_reference"]

    print(f"  [OK] Extracted verse {v1['verse_id']}: {v1['modal_details']['transliteration']}")

def test_shema_content():
    print("[TEST] Testing Shema Yisrael content extraction...")
    path = Path(__file__).resolve().parent.parent / "content" / "samples" / "shema_yisrael.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["id"] == "shema-yisrael"
    assert len(data["sections"]) == 1

    v_shema = data["sections"][0]["paragraphs"][0]["verses"][0]
    assert v_shema["verse_id"] == "v-shema-1"
    assert "שְׁמַע יִשְׂרָאֵל" in v_shema["hebrew"]
    assert "Escucha Israel" in v_shema["spanish_interlinear"]
    assert v_shema["modal_details"]["notes"] is not None

    print(f"  [OK] Extracted verse {v_shema['verse_id']}: {v_shema['modal_details']['spanish_full']}")

def simulate_modal_layout(verse: dict, max_width: int, max_height: int, line_height: int):
    details = verse.get("modal_details", {})
    lines = []

    if details.get("source_reference"):
        lines.append(f"[{details['source_reference']}]")
        lines.append("")

    max_chars = max(20, max_width // 12)

    for prefix, key in [("Traducción", "spanish_full"), ("Fonética", "transliteration"), ("Comentario", "notes")]:
        val = details.get(key)
        if val:
            full = f"{prefix}: {val}"
            words = full.split()
            cur = ""
            for w in words:
                if not cur:
                    cur = w
                elif len(cur) + 1 + len(w) <= max_chars:
                    cur += " " + w
                else:
                    lines.append(cur)
                    cur = w
            if cur:
                lines.append(cur)
            lines.append("")

    lines_per_page = max(1, max_height // line_height)
    total_pages = max(1, (len(lines) + lines_per_page - 1) // lines_per_page)
    return lines, total_pages

def test_modal_layout():
    print("[TEST] Testing modal presenter layout simulation...")
    path = Path(__file__).resolve().parent.parent / "content" / "samples" / "kiddush_shabbat.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    v1 = data["sections"][0]["paragraphs"][0]["verses"][0]
    # Simulate 800x480 screen with 700x380 modal area, 28px line height
    lines, pages = simulate_modal_layout(v1, 700, 380, 28)
    print(f"  Formatted {len(lines)} line(s) into {pages} modal page(s):")
    for idx, l in enumerate(lines[:6]):
        print(f"    Line {idx+1}: {l}")
    assert len(lines) > 0
    assert pages >= 1
    print("  [OK] Modal layout simulation passed!")

def main():
    test_kiddush_content()
    test_shema_content()
    test_modal_layout()
    print("=== ALL CONTENT & MODAL TESTS PASSED! ===")

if __name__ == "__main__":
    main()
