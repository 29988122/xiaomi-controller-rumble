#!/bin/bash
set -euo pipefail
# A fresh /work directory inside the documented Linux x86_64 container is required.
cd /work
PROFILE=${PROFILE:-/work/task/profiles/ruby-os2.0.8.0-umotwxm}
cp "$PROFILE/kernel.config" kernel.config
cp "$PROFILE/stock.Module.symvers" stock.Module.symvers
test ! -e kernel && test ! -e out && test ! -e toolchain && test ! -e driver
python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); print(p["source_sha256"]+"  ruby-source.tar.gz"); print(p["toolchain_sha256"]+"  clang-r383902.tar.gz")' "$PROFILE/profile.json" | sha256sum -c -
mkdir kernel out toolchain driver
tar -xzf ruby-source.tar.gz --strip-components=1 -C kernel
tar -xzf clang-r383902.tar.gz -C toolchain
patch -d kernel -p1 < task/compat/power-supply-ruby-hyperos2.patch
cp kernel.config out/.config
cp task/driver/sony_g8ff.c task/driver/hid-ids.h task/driver/Makefile driver/
export PATH="/work/toolchain/bin:$PATH"
make -C kernel O=/work/out ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \
    CC=clang LD=ld.lld AR=llvm-ar NM=llvm-nm OBJCOPY=llvm-objcopy \
    OBJDUMP=llvm-objdump STRIP=llvm-strip HOSTCC=gcc HOSTCXX=g++ olddefconfig modules_prepare
