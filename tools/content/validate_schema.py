#!/usr/bin/env python3
"""
tools/content/validate_schema.py — Validates liturgical JSON files against liturgical-text.json schema.
"""

import sys
import json
from pathlib import Path

# Fix Windows cp1252 console encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

def validate_file(json_path: Path, schema: dict) -> bool:
    import jsonschema
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        jsonschema.validate(instance=data, schema=schema)
        print(f"[OK] VALID: {json_path.name} (id: {data.get('id')})")

        return True
    except jsonschema.ValidationError as e:
        print(f"✗ INVALID: {json_path.name}")
        print(f"  Error: {e.message}")
        print(f"  Path: {' -> '.join(str(p) for p in e.absolute_path)}")
        return False
    except Exception as e:
        print(f"✗ ERROR reading {json_path.name}: {e}")
        return False

def main():
    root = Path(__file__).resolve().parent.parent.parent
    schema_path = root / "content" / "schema" / "liturgical-text.json"
    
    if not schema_path.exists():
        print(f"Error: Schema not found at {schema_path}", file=sys.stderr)
        sys.exit(1)
        
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
        
    samples_dir = root / "content" / "samples"
    files = list(samples_dir.glob("*.json"))
    
    if not files:
        print("Warning: No sample JSON files found to validate.")
        sys.exit(0)
        
    print(f"Validating {len(files)} file(s) against {schema_path.name}...")
    all_ok = True
    for f in sorted(files):
        if not validate_file(f, schema):
            all_ok = False
            
    if not all_ok:
        sys.exit(1)
    print("All liturgical files passed validation successfully!")

if __name__ == "__main__":
    main()
