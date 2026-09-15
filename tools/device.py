#!/usr/bin/env python3
"""Read device evidence and run a bounded, motor-only DS4 Bluetooth test."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import shlex
import struct
import subprocess
import zlib


def adb(serial, command, *, timeout=60):
    return subprocess.run(
        ["adb", "-s", serial, "exec-out", "su -c " + shlex.quote(command)],
        capture_output=True, check=True, timeout=timeout,
    ).stdout


def report(strong, weak, interval):
    if not (0 <= strong <= 80 and 0 <= weak <= 80 and 1 <= interval <= 62):
        raise ValueError("bounded motor strength and current poll interval required")
    packet = bytearray(78)
    packet[0:2] = bytes([0x11, 0xC0 | interval])
    packet[3] = 0x01  # Motor update only; do not update LED/blink state.
    packet[6:8] = bytes([weak, strong])
    struct.pack_into("<I", packet, 74, zlib.crc32(b"\xa2" + packet[:74]))
    return bytes(packet)


def inspect(serial, dest):
    dest.mkdir(parents=True, exist_ok=True)
    queries = {
        "kernel.config": "zcat /proc/config.gz",
        "version.txt": "uname -a; cat /proc/version",
        "cmdline.txt": "cat /proc/cmdline",
        "input.txt": "cat /proc/bus/input/devices; dumpsys input",
        "modules.txt": "cat /proc/modules; cat /proc/sys/kernel/modules_disabled; cat /sys/module/module/parameters/sig_enforce",
        "hid.txt": "for d in /sys/bus/hid/devices/*; do cat \"$d/uevent\"; readlink \"$d/driver\"; done",
        "kallsyms.txt": "cat /proc/kallsyms",
    }
    for name, command in queries.items():
        data = adb(serial, command)
        (dest / name).write_bytes(data)
        print(name, len(data), flush=True)
    cmdline = (dest / "cmdline.txt").read_text()
    slot = re.search(r"(?:^|\s)androidboot.slot_suffix=(_[ab])(?:\s|$)", cmdline)
    if not slot:
        raise RuntimeError("Cannot identify active boot slot")
    partition = "/dev/block/by-name/boot" + slot[1]
    original_hash = adb(serial, "sha256sum " + shlex.quote(partition)).decode().split()[0]
    boot = adb(serial, "cat " + shlex.quote(partition), timeout=180)
    if not boot.startswith(b"ANDROID!"):
        raise RuntimeError("Unexpected boot image header")
    digest = hashlib.sha256(boot).hexdigest()
    if digest != original_hash:
        raise RuntimeError("Boot image copy checksum mismatch")
    (dest / "boot-active.img").write_bytes(boot)
    (dest / "boot.json").write_text(json.dumps({"partition": partition, "bytes": len(boot), "sha256": digest}, indent=2) + "\n")
    print("boot image verified", len(boot), digest, flush=True)


def pulse(serial, expected_unique_id):
    # Resolve a fresh hidraw path: numbering changes after reconnection/rebinding.
    listing = adb(serial, "for d in /sys/class/hidraw/hidraw*; do echo NODE=$d; cat \"$d/device/uevent\"; cat \"$d/device/bt_poll_interval\"; done").decode()
    candidates = []
    for block in listing.split("NODE=")[1:]:
        lines = block.splitlines()
        fields = dict(x.split("=", 1) for x in lines[1:] if "=" in x)
        if fields.get("HID_ID") == "0005:0000054C:000005C4" and fields.get("HID_UNIQ") == expected_unique_id:
            candidates.append(("/dev/" + Path(lines[0]).name, int(lines[-1])))
    if len(candidates) != 1:
        raise RuntimeError("Expected exactly one identified G8+ Bluetooth device")
    node, interval = candidates[0]
    packets = {"stop": report(0, 0, interval), "strong": report(80, 0, interval), "weak": report(0, 80, interval)}
    commands = ["set -eu", "exec 3>" + shlex.quote(node)]
    for name, packet in packets.items():
        encoded = base64.b64encode(packet).decode()
        commands.append(f"{name}() {{ printf %s '{encoded}' | base64 -d >&3; }}")
    commands += [
        "trap 'stop; exec 3>&-' EXIT", "trap 'exit 1' HUP INT TERM",
        "stop", "sleep 1", "strong", "sleep 0.4", "stop", "sleep 1",
        "weak", "sleep 0.4", "stop", "sleep 0.4", "weak", "sleep 0.4", "stop",
        "printf 'Bounded rumble sequence sent; physical confirmation required.\\n'",
    ]
    print(adb(serial, "\n".join(commands), timeout=20).decode(), end="")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--serial", required=True)
    sub = p.add_subparsers(dest="action", required=True)
    i = sub.add_parser("inspect")
    i.add_argument("dest", type=Path)
    t = sub.add_parser("pulse")
    t.add_argument("--unique-id", required=True)
    a = p.parse_args()
    if a.action == "inspect":
        inspect(a.serial, a.dest)
    else:
        pulse(a.serial, a.unique_id)


if __name__ == "__main__":
    main()
