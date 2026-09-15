#!/usr/bin/env python3
"""Fail closed unless every imported kernel symbol has independently built CRC evidence."""
import argparse
import json
from pathlib import Path


def compare(imports, stock, computed):
    required = sorted(set(imports) | {"module_layout"})
    rows = []
    for name in required:
        expected = stock.get(name)
        candidate = computed.get(name)
        if expected is None:
            status = "not_exported"
        elif candidate is None:
            status = "missing_build_evidence"
        elif int(expected["crc"], 16) != int(candidate["crc"], 16):
            status = "mismatch"
        else:
            status = "match"
        rows.append({"symbol": name, "status": status,
                     "stock": expected, "computed": candidate})
    return {"passed": bool(imports) and all(r["status"] == "match" for r in rows),
            "required_count": len(rows), "rows": rows}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--imports", type=Path, required=True)
    p.add_argument("--stock", type=Path, required=True)
    p.add_argument("--computed", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    imports = a.imports.read_text().split()
    result = compare(imports, json.loads(a.stock.read_text()), json.loads(a.computed.read_text()))
    a.output.write_text(json.dumps(result, indent=2) + "\n")
    counts = {}
    for r in result["rows"]:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print(json.dumps({"passed": result["passed"], "counts": counts}))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
