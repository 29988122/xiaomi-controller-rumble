# Changelog / 更新紀錄

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
