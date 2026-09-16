# Changelog / 更新紀錄

## v0.3.0 — one reboot, deferred setup / 一次重開機、稍後設定

### English

- Fresh installs are enabled. Reboot once; Action completes setup or tests rumble without another reboot.
- No controller, multiple candidates or incomplete initialization leave setup pending instead of failing installation. Pending services neither load a driver nor choose a controller automatically.
- Migrate validated literal controller settings from v0.2.1 without executing old config code; preserve disabled state on upgrade.
- Share lifecycle logic and kernel file locks across Action and the watcher. Reject staged/same-boot activation, concurrent actions and duplicate workers. Dead processes do not leave held locks.
- Traditional Chinese/English messages explain the next step. Action is the only path that runs the bounded motor test.
- Keep the previously validated kernel `.ko` unchanged. Rebuild the userspace FF helper with an opened-device identity check before sending effects, so a recycled event number cannot target another controller.
- 36 simulated tests cover install/setup, migration, delays, disconnects, concurrency, targeting and restoration. CI checks POSIX and Magisk 30.7 BusyBox shells, final kernel ELF/CRC evidence, reproducible ZIP and the cross-built helper's fail-closed behavior under QEMU.

**No v0.3.0 phone installation, reboot or physical motor test was performed.** The owner chose delivery without a connected phone. KernelSU/Next hardware and gameplay remain untested. The Magisk shell tests use the real x86_64 BusyBox executable with simulated sysfs and installation helpers, not a booted Android system.

### 繁體中文

- 首次安裝預設啟用，重開機一次後，按「動作」完成設定或測試震動，不需再重開機。
- 沒有手把、多支候選或尚未初始化時，安裝仍完成並保留待設定狀態；背景服務不會自行挑選手把或載入驅動。
- 更新保留 v0.2.1 的有效手把設定與停用意圖；只解析合法欄位，不執行舊設定的 Shell 程式。
- 「動作」與背景服務共用生命週期與核心檔案鎖，阻止重開機前啟動、重複操作和重複服務；程序結束就釋放鎖。
- 繁體中文／英文提示直接說明下一步。只有按「動作」才執行有限時長的震動測試。
- 核心 `.ko` 完全不變。重建使用者空間的測試程式，打開輸入裝置後核對身分，防止斷線後裝置編號被重用而測到其他手把。
- 36 項模擬測試涵蓋安裝、稍後設定、更新、延遲、斷線、並行操作、選定目標與復原；CI 檢查 POSIX／Magisk 30.7 BusyBox Shell、核心 ELF／CRC、可重現封裝與 QEMU 下的拒絕錯誤輸入行為。

**本版未進行手機安裝、重開機或實體震動驗收。** 使用者選擇在手機未連線的情況下交付；KernelSU／Next 實機與遊戲仍未測。Magisk Shell 測試使用真正的 x86_64 BusyBox，但 sysfs 與安裝輔助函式為模擬，並非開機後的 Android。

## v0.2.1

### English

- Fix the misleading generic “connect exactly ONE” installation failure. Count all matching controllers before checking readiness and report distinct failure reasons.
- Wait up to 20 seconds for a single controller's Sony driver to initialize. Preserve the observed polling interval; never invent one or bypass the driver readiness check.
- Pin controller identity while waiting; stop if it changes, disconnects or a second matching controller appears. Reject duplicate identity fields.
- Keep the validated `.ko`, firmware guards, service and default-disabled behavior unchanged.
- Generate release filenames from `module.prop` to avoid a stale version in the package name.

The user's v0.2.0 failure involved exactly one DS4 device with no driver binding. Kernel logs showed calibration retrieval failure followed by failure to claim input. Rebinding the stock driver did not recover that connection; after Bluetooth/controller reconnection, normal stock-driver initialization returned with 4 ms polling. The reason the calibration exchange failed is not established. This release improves waiting and diagnosis; persistent calibration failures still require reconnection or further investigation.

Validation: 18 automated tests, shell syntax checks, plus the actual release `customize.sh` on the phone with installed Magisk 30.7 BusyBox/permission functions in a disposable staging directory. Local identity, poll interval, disabled state and permissions passed; the driver was not loaded. Full manager installation/reboot activation was not repeated. KernelSU/Next hardware and gameplay remain untested.

### 繁體中文

- 修正所有手把偵測錯誤都顯示「只連一支」的誤導訊息。先計算全部候選數量，再檢查初始化狀態，分別顯示失敗原因。
- 一支手把符合條件時，最多等待 Sony 驅動初始化 20 秒；保留實際讀到的回報間隔，不猜數值、不跳過就緒檢查。
- 等待時固定手把身分，換手把、斷線或出現第二支候選就停止；拒絕重複的識別欄位。
- 已驗證的 `.ko`、韌體限制、背景服務及預設停用行為保持原樣。
- 安裝包檔名由 `module.prop` 版本自動產生，避免版本更新後仍沿用舊檔名。

這次 v0.2.0 失敗時確實只有一支 DS4 手把，但沒有成功綁定驅動。核心紀錄顯示校正資料讀取失敗，接著無法建立輸入裝置；重新綁定原廠驅動仍失敗。藍牙／手把重新連線後恢復正常，回報間隔為 4 ms。校正交換失敗的更深層原因尚未確定；此版改善等待與診斷，持續失敗仍需重連或進一步排查。

驗證：18 項自動測試、Shell 語法檢查，以及在手機暫存目錄使用現有 Magisk 30.7 BusyBox／權限函式，執行正式 ZIP 內的 `customize.sh`。手把身分、回報間隔、停用狀態與權限均通過，未載入驅動。未重做管理器完整安裝／重開機啟用；KernelSU／Next 實機與遊戲仍未測。
