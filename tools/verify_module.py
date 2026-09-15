#!/usr/bin/env python3
"""Check the final ARM64 ELF's embedded MODVERSIONS, imports and CFI symbols."""
import argparse
import json
from pathlib import Path
import struct
from elftools.elf.elffile import ELFFile

p = argparse.ArgumentParser()
p.add_argument("module", type=Path)
p.add_argument("stock", type=Path)
p.add_argument("computed", type=Path)
p.add_argument("output", type=Path)
p.add_argument("--profile", type=Path, required=True)
a = p.parse_args()
profile = json.loads(a.profile.read_text())
stock = json.loads(a.stock.read_text())
computed = json.loads(a.computed.read_text())
with a.module.open("rb") as file:
    elf = ELFFile(file)
    if elf["e_machine"] != "EM_AARCH64" or elf.elfclass != 64 or not elf.little_endian:
        raise RuntimeError("Expected little-endian ELF64 AArch64")
    symbols = list(elf.get_section_by_name(".symtab").iter_symbols())
    imports = {s.name for s in symbols if s.name and s["st_shndx"] == "SHN_UNDEF"}
    defined = {s.name for s in symbols if s["st_shndx"] != "SHN_UNDEF"}
    if not {"__cfi_check", "__cfi_check_fail"}.issubset(defined) or "__cfi_slowpath" not in imports:
        raise RuntimeError("Missing kernel CFI instrumentation")
    data = elf.get_section_by_name("__versions").data()
    if not data or len(data) % 64:
        raise RuntimeError("Unexpected MODVERSIONS table")
    versions = {}
    for offset in range(0, len(data), 64):
        crc = struct.unpack_from("<Q", data, offset)[0]
        name = data[offset + 8:offset + 64].split(b"\0", 1)[0].decode()
        if name in versions:
            raise RuntimeError("Duplicate version record: " + name)
        versions[name] = crc
    if set(versions) != imports | {"module_layout"}:
        raise RuntimeError("Version table does not exactly cover final imports")
    for name, crc in versions.items():
        if crc != int(stock[name]["crc"], 16) or crc != int(computed[name]["crc"], 16):
            raise RuntimeError("Embedded ABI CRC mismatch: " + name)
    modinfo = elf.get_section_by_name(".modinfo").data().split(b"\0")
    vermagic = [v.decode().split("=", 1)[1] for v in modinfo if v.startswith(b"vermagic=")]
    if len(vermagic) != 1 or vermagic[0].strip() != profile["vermagic"]:
        raise RuntimeError("Unexpected kernel vermagic")
report = {"passed": True, "embedded_crcs_verified": len(versions), "cfi": True, "vermagic": vermagic[0]}
a.output.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report))
