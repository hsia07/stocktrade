#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import yaml
from jsonschema import validate

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    args = ap.parse_args()

    manifest_path = Path(args.manifest)
    schema_path = Path("manifests/schemas/round_manifest.schema.json")
    if not manifest_path.exists():
        print(f"FAIL: manifest not found: {manifest_path}")
        sys.exit(1)
    if not schema_path.exists():
        print(f"FAIL: schema not found: {schema_path}")
        sys.exit(1)

    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate(instance=manifest, schema=schema)

    if manifest.get("status") == "passed":
        print("INFO: current round already marked passed")
    print("PASS: manifest schema valid")

if __name__ == "__main__":
    main()
