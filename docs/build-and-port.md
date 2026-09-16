# Build, provenance and porting / 建置、來源與移植

[English README](../README.md) · [繁體中文 README](../README.zh-TW.md)

## Provenance

| Input / 輸入 | Pinned value / 固定值 |
|---|---|
| Xiaomi source commit | `914ba8403bb3a957ed37b99dcecdbafce9d16121` |
| Source archive SHA-256 | `43a0d78d4b7b8460495d8cf54f9634264aab4ab8cad205e26341b66783ca54a5` |
| Android Clang | 11.0.1, r383902, Android build 6443078 |
| Toolchain archive SHA-256 | `afd99fb760191fafe933809308d16295a302ac14b36058abe2f4489f0706e7e5` |
| Original `hid-sony.c` SHA-256 | `401acf827e89df34af3fb954bfd0616bed8cddf38d69463d45ba4134d83ef835` |
| Original `hid-ids.h` SHA-256 | `6187067ca026998f33ff8a3c890b831a106df422615c0e85ce6d8eebeb0a0d51` |
| Build environment | Debian bookworm-slim, Linux x86_64; original image ID `160466e67bb85a4099d9d9c2356b4a6a64747b281a22c142efbd4539db1b8525` |

The supplied kernel config and exported-symbol evidence came from the tested firmware. They contain no controller identity. Boot images and raw device dumps are not distributed. The supplied binaries are the exact previously tested artifacts; public packaging changes do not rebuild or patch them.

附帶核心設定與匯出符號證據來自已測韌體，不包含手把識別碼。boot 與原始裝置傾印不公開。二進位為實測的原始產物，公開封裝沒有修改它們。

## Rebuild the ruby profile / 重建 ruby profile

Use a fresh Linux x86_64 container; mount an empty writable directory at `/work` and this repository at `/work/task`. Do not run package installation on an unrelated host OS. The example assumes root **inside the container**.

使用新的 Linux x86_64 容器，把空白建置目錄掛在 `/work`、專案掛在 `/work/task`。下列套件安裝以容器內 root 為前提，不要直接改動無關主機環境。

```sh
apt-get update
apt-get install -y --no-install-recommends build-essential bc bison flex libssl-dev libelf-dev python3 python3-pyelftools gcc-aarch64-linux-gnu binutils-aarch64-linux-gnu curl ca-certificates xz-utils patch
cd /work
curl --fail --location 'https://codeload.github.com/MiCode/Xiaomi_Kernel_OpenSource/tar.gz/914ba8403bb3a957ed37b99dcecdbafce9d16121' -o ruby-source.tar.gz
curl --fail --location 'https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86/+archive/refs/tags/android-11.0.0_r1/clang-r383902.tar.gz' -o clang-r383902.tar.gz
bash /work/task/tools/prepare.sh
bash /work/task/tools/build.sh
```

Preparation checks archive hashes, applies the documented power-supply header patch and uses the profile's kernel config. `olddefconfig` normalizes it against the older source: differences must be inspected for a new port, not assumed harmless. `build.sh` compiles real export units, checks independently computed CRCs, builds the module, checks its final ELF and builds the bounded FF tester. Output: `/work/driver/sony_g8ff.ko`, `/work/ff_test`, `/work/validated/`.

準備階段核對下載雜湊、套用已說明的 power_supply 標頭修補，並使用 profile 設定。`olddefconfig` 會依舊來源正規化設定；移植時必須檢視差異，不可視為必然無害。建置工具編譯真正匯出實作、比對獨立 CRC、建模組、核對最終 ELF，並建立短時間 FF 測試程式。產物位於上述路徑。

The original driver hash reproduced on a second build. Full fresh-container reproducibility also depends on available host packages; if output differs, inspect it rather than overwrite the committed profile hash to make packaging pass. Preserve the source of any change. The public ZIP itself uses fixed timestamps and uncompressed entries for byte-identical packaging across zlib versions.

原始驅動第二次建置的雜湊相同。全新容器的重現也受可取得的主機套件影響；若不同，應調查而非直接改 profile 雜湊讓封裝過關。公開 ZIP 使用固定時間與不壓縮的項目，避免不同 zlib 版本造成封裝位元組差異。

## Verify / 檢查

```sh
python3 -m pip install pyelftools==0.33
python3 -m unittest discover -s tests -v
python3 tools/verify_module.py profiles/ruby-os2.0.8.0-umotwxm/sony_g8ff.ko profiles/ruby-os2.0.8.0-umotwxm/stock-symbols.json profiles/ruby-os2.0.8.0-umotwxm/computed-symbols.json /tmp/rumble-check.json --profile profiles/ruby-os2.0.8.0-umotwxm/profile.json
python3 tools/package.py
```

Installer tests provide the documented manager variables/helper-function contracts and a synthetic sysfs tree. They do **not** boot KernelSU, emulate its kernel, or establish real manager installation success. Runtime recovery/reconnect evidence is from the Magisk private predecessor with the same driver and supervisor. Public profile selection is tested through fixtures. The phone was not changed during publication.

安裝器測試提供管理器變數／輔助函式介面與假的 sysfs；**沒有**啟動 KernelSU、模擬其核心，或證明實際管理器安裝成功。復原／重連證據來自使用相同驅動及管理程式的 Magisk 私人前版。公開版選定手把流程透過測試資料驗證，發布過程沒有改動手機。

## Add a profile / 新增 profile

1. Follow the [write-up](writeup.md#7-a-workflow-another-person-or-ai-agent-can-use) / [中文流程](writeup.zh-TW.md#7-人類與後續-ai-agent-可遵循的流程). Identify the real controller protocol and root/module prerequisites first.
2. Add a separate profile directory with the exact firmware identity, toolchain/source provenance, config, independent ABI evidence, binary hashes and validation report. No device address or serial belongs in it.
3. Adapt the source patch, export-unit list, table extractor and compiler assumptions as needed. The existing absolute ARM64 table parser and power-supply patch are **not generic**.
4. Use `PROFILE=/work/task/profiles/<id>` for build/prepare and `--profile <id>` for packaging. Do not list a new profile as supported until its evidence and temporary-load/rollback tests have been reviewed.
5. Maintain a truthful matrix: package contract checked; kernel ABI checked; physical FF confirmed; reconnect/reboot/recovery checked; application testing performed or skipped.

先按文章流程確認協定與載入條件，再新增獨立 profile，附完整版本、來源、設定、獨立 ABI、雜湊與驗證報告，不能放入個人裝置識別碼。來源修補、匯出實作清單、解析布局與工具鏈都可能要調整，不能直接套用 ruby 假設。使用上述 `PROFILE`／`--profile` 選取；證據與暫時載入／復原未經檢視前，不列為已支援。驗證表應分開記錄封裝、ABI、實體 FF、生命週期與應用程式結果。

Root-manager contract references: [Magisk](https://topjohnwu.github.io/Magisk/guides.html), [KernelSU](https://kernelsu.org/guide/module.html), [KernelSU Next installer](https://github.com/KernelSU-Next/KernelSU-Next/blob/dev/userspace/ksud/src/installer.sh). No source code from those installers is redistributed in this project.


### v0.2.1 installation follow-up / 安裝追蹤

The 18 automated tests now cover unbound/late-ready controllers, identity changes during the bounded wait and specific diagnostic errors. After reconnecting the real G8+, the release ZIP's `customize.sh` passed on the phone using its installed Magisk 30.7 BusyBox and permission helpers, with `MODPATH` redirected to a disposable directory. The check verified the selected identity, 4 ms polling, root-only permissions and the disabled marker. No `.ko` was loaded, no real module directory was installed or activated, and the temporary files were removed. This is narrower than an end-to-end manager installation test. KernelSU hardware remains untested.

18 項自動測試包含驅動未綁定、延後初始化、等待期間更換手把與分類錯誤提示。實機 G8+ 重新連線後，使用手機既有 Magisk 30.7 的 BusyBox 與權限函式，在一次性暫存目錄執行 ZIP 中的 `customize.sh` 成功；核對手把識別、4 ms 回報間隔、root 專用權限及停用標記。沒有載入 `.ko`、沒有寫入真正的模組安裝目錄或啟用模組，測試後已移除暫存。這不等於管理器完整安裝的端到端驗收；KernelSU 實機仍未測試。
