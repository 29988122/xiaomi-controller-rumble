#!/usr/bin/env python3
"""Extract the stock kernel's absolute ARM64 export table and power attribute order.

Input: an ELF recovered from the locally backed-up kernel using vmlinux-to-elf.
This performs no writes to the phone and rejects unexpected table layouts.
"""
import argparse
import json
from pathlib import Path
import re
import struct
from elftools.elf.elffile import ELFFile

p = argparse.ArgumentParser()
p.add_argument("kernel_elf", type=Path)
p.add_argument("dest", type=Path)
a = p.parse_args()
a.dest.mkdir(parents=True, exist_ok=True)
with a.kernel_elf.open("rb") as f:
    elf = ELFFile(f)
    symbols = {s.name: s["st_value"] for s in elf.get_section_by_name(".symtab").iter_symbols()}

    def read(address, size):
        for seg in elf.iter_segments():
            if seg["p_vaddr"] <= address and address + size <= seg["p_vaddr"] + seg["p_filesz"]:
                f.seek(seg["p_offset"] + address - seg["p_vaddr"])
                return f.read(size)
        raise ValueError(f"Unmapped address: {address:x}")

    rows, mapping = [], {}
    for suffix, kind in [("", "EXPORT_SYMBOL"), ("_gpl", "EXPORT_SYMBOL_GPL")]:
        start = symbols["__start___ksymtab" + suffix]
        end = symbols["__stop___ksymtab" + suffix]
        crcs = symbols["__start___kcrctab" + suffix]
        assert (end - start) % 16 == 0
        assert (end - start) // 16 * 4 == symbols["__stop___kcrctab" + suffix] - crcs
        for index, address in enumerate(range(start, end, 16)):
            value, name_ptr = struct.unpack("<QQ", read(address, 16))
            name = read(name_ptr, 256).split(b"\0")[0].decode()
            assert symbols.get("__ksymtab_" + name) == address
            crc = struct.unpack("<I", read(crcs + index * 4, 4))[0]
            rows.append(f"0x{crc:08x}\t{name}\tvmlinux\t{kind}\n")
            mapping[name] = {"crc": f"0x{crc:08x}", "kind": kind}
    (a.dest / "stock.Module.symvers").write_text("".join(rows))
    (a.dest / "stock-symbols.json").write_text(json.dumps(mapping, indent=2) + "\n")

    start, end = symbols["power_supply_attrs"], symbols["power_supply_attr_group"]
    assert (end - start) % 32 == 0
    attributes, callbacks = [], None
    for address in range(start, end, 32):
        name_ptr, mode, show, store = struct.unpack("<QQQQ", read(address, 32))
        if callbacks is None:
            callbacks = show, store
        assert (show, store) == callbacks
        name = read(name_ptr, 120).split(b"\0")[0].decode()
        assert re.fullmatch("[a-z0-9_]+", name)
        attributes.append(name)
    (a.dest / "power-supply-attributes.json").write_text(json.dumps(attributes, indent=2) + "\n")
    print(f"Validated {len(rows)} exports and {len(attributes)} power supply attributes")
