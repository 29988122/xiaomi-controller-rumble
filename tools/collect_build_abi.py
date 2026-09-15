#!/usr/bin/env python3
"""Collect CRCs emitted from real kernel export implementation units, not header probes."""
import argparse
import json
from pathlib import Path
import re

p = argparse.ArgumentParser()
p.add_argument("out", type=Path)
p.add_argument("stock_symvers", type=Path)
p.add_argument("dest", type=Path)
a = p.parse_args()
stock = {}
for line in a.stock_symvers.read_text().splitlines():
    crc, name, owner, kind = line.split()[:4]
    stock[name] = {"crc": crc, "kind": kind}
computed = {}
for path in a.out.rglob("*.symversions"):
    for name, crc in re.findall(r"__crc_(\w+)\s*=\s*(0x[0-9a-fA-F]+)", path.read_text()):
        if name in computed and int(computed[name]["crc"], 16) != int(crc, 16):
            raise RuntimeError("Conflicting computed CRCs: " + name)
        computed[name] = {"crc": crc, "source": str(path.relative_to(a.out))}
a.dest.mkdir(parents=True, exist_ok=True)
(a.dest / "stock-symbols.json").write_text(json.dumps(stock, indent=2) + "\n")
(a.dest / "computed-symbols.json").write_text(json.dumps(computed, indent=2) + "\n")
# Only independently computed entries which agree with the running kernel.
lines = []
for name, item in sorted(computed.items()):
    expected = stock.get(name)
    if expected and int(item["crc"], 16) == int(expected["crc"], 16):
        lines.append(f'{item["crc"]}\t{name}\tvmlinux\t{expected["kind"]}\n')
(a.dest / "validated.Module.symvers").write_text("".join(lines))
print(f"Collected {len(computed)} computed symbols; {len(lines)} match the stock kernel")
