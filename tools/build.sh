#!/bin/bash
set -euo pipefail
# Run in the isolated Linux build container, after unpacking pinned source/toolchain.
KERNEL_SRC=${KERNEL_SRC:-/work/kernel}
OUT_DIR=${OUT_DIR:-/work/out}
TOOLCHAIN=${TOOLCHAIN:-/work/toolchain}
TASK_SRC=${TASK_SRC:-/work/task}
DRIVER_DIR=${DRIVER_DIR:-/work/driver}
STOCK_SYMVERS=${STOCK_SYMVERS:-/work/stock.Module.symvers}
EVIDENCE=${EVIDENCE:-/work/validated}
PROFILE=${PROFILE:-$TASK_SRC/profiles/ruby-os2.0.8.0-umotwxm}
LOCAL_SUFFIX=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["localversion"])' "$PROFILE/profile.json")
export PATH="$TOOLCHAIN/bin:$PATH"
mkdir -p "$EVIDENCE"
common=(-C "$KERNEL_SRC" O="$OUT_DIR" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
    CC=clang LD=ld.lld AR=llvm-ar NM=llvm-nm OBJCOPY=llvm-objcopy
    OBJDUMP=llvm-objdump STRIP=llvm-strip HOSTCC=gcc HOSTCXX=g++)
units=(drivers/hid/hid-core.o drivers/input/ff-memless.o drivers/input/input.o kernel/module.o
    lib/ratelimit.o kernel/cfi.o lib/dynamic_debug.o lib/list_debug.o drivers/base/core.o
    kernel/locking/spinlock.o lib/string.o kernel/workqueue.o lib/crc32.o drivers/base/devres.o
    drivers/leds/led-class.o drivers/power/supply/power_supply_core.o lib/idr.o
    drivers/input/input-mt.o mm/slub.o mm/slab_common.o mm/util.o lib/kstrtox.o
    kernel/params.o kernel/printk/printk.o lib/vsprintf.o arch/arm64/kernel/arm64ksyms.o
    kernel/panic.o arch/arm64/kernel/process.o arch/arm64/lib/atomic_ll_sc.o)
make -j4 "${common[@]}" "${units[@]}"
make "${common[@]}" M="$DRIVER_DIR" sony_g8ff.o
llvm-nm -u "$DRIVER_DIR/sony_g8ff.o" | awk '$NF != "__this_module" {print $NF}' > "$EVIDENCE/imports.txt"
python3 "$TASK_SRC/tools/collect_build_abi.py" "$OUT_DIR" "$STOCK_SYMVERS" "$EVIDENCE"
python3 "$TASK_SRC/tools/verify_abi.py" --imports "$EVIDENCE/imports.txt" \
    --stock "$EVIDENCE/stock-symbols.json" --computed "$EVIDENCE/computed-symbols.json" \
    --output "$EVIDENCE/abi-check.json"
# The release suffix is applied only after every imported ABI has independently matched.
cp "$EVIDENCE/validated.Module.symvers" "$OUT_DIR/Module.symvers"
make "${common[@]}" LOCALVERSION="$LOCAL_SUFFIX" prepare
make "${common[@]}" LOCALVERSION="$LOCAL_SUFFIX" M="$DRIVER_DIR" modules
llvm-nm -u "$DRIVER_DIR/sony_g8ff.ko" | awk '{print $NF}' > "$EVIDENCE/final-imports.txt"
python3 "$TASK_SRC/tools/verify_abi.py" --imports "$EVIDENCE/final-imports.txt" \
    --stock "$EVIDENCE/stock-symbols.json" --computed "$EVIDENCE/computed-symbols.json" \
    --output "$EVIDENCE/final-abi-check.json"
python3 "$TASK_SRC/tools/verify_module.py" "$DRIVER_DIR/sony_g8ff.ko" \
    "$EVIDENCE/stock-symbols.json" "$EVIDENCE/computed-symbols.json" "$EVIDENCE/embedded-module-check.json" --profile "$PROFILE/profile.json"
llvm-readelf -h -S "$DRIVER_DIR/sony_g8ff.ko" > "$EVIDENCE/module-elf.txt"
llvm-nm "$DRIVER_DIR/sony_g8ff.ko" | grep -E '(__cfi_check|__cfi_slowpath|sony_play_effect)' > "$EVIDENCE/module-cfi.txt"
test -s "$EVIDENCE/module-cfi.txt"
sha256sum "$DRIVER_DIR/sony_g8ff.ko" > "$EVIDENCE/module.sha256"
sh "$TASK_SRC/tools/build-ff-test.sh" "${FF_TEST_OUT:-/work/ff_test}"
