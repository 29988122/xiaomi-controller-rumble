#!/bin/sh
# Linux cross-build; no kernel tree or full kernel build is required.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
aarch64-linux-gnu-gcc -nostdlib -static -fno-stack-protector -ffreestanding \
    -fno-builtin -fno-ident -O2 -Wl,--build-id=none -s \
    "$ROOT/tools/ff_test.c" -o "${1:?Output path required}"
