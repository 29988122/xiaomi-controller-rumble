# Xiaomi Controller Rumble

[English](README.md) · [完整技術文章](docs/writeup.zh-TW.md) · [建置與移植](docs/build-and-port.md)

在**經過驗證的小米／紅米原廠核心**上補回藍牙手把的震動能力，保留原有 boot 映像。這個專案包含 Redmi `ruby` 的成功案例、限定韌體版本的替代驅動，以及原始碼與現行韌體不完全相符時的調查方法。

**方法可以移植，附帶的 `.ko` 並非小米全機型通用驅動。** 年代接近、Android 版本相同或核心都以 `4.19` 開頭，都不足以證明 ABI 相容。修復的對象是手把馬達，不是手機本身的震動馬達。

## 支援範圍

| 項目 | 已驗證案例 |
|---|---|
| 手機 | Redmi Note 12 Pro 5G，`ruby`，`22101316G` |
| 系統 | HyperOS `OS2.0.8.0.UMOTWXM`，Android 14 |
| 核心 | `4.19.191-gdecc267868f3`，ARM64 |
| 手把 | GameSir G8+，DS4 藍牙模式 `054C:05C4` |
| 實體／執行驗證 | Magisk Alpha 30700，使用完全相同 `.ko` 的私人前版 |
| 公開 v0.2.0 安裝程式 | 自動化安裝介面契約測試；沒有重新安裝到手機 |
| KernelSU／KernelSU Next | ZIP 與腳本介面已查核、測試；**沒有實機驗證** |
| 其他 root fork／手機／ROM | 未驗證；沒有相符 profile 就拒絕安裝 |

原廠 Sony 驅動未啟用 `CONFIG_SONY_FF`。替代驅動 `sony_g8ff` 補上標準 `FF_RUMBLE` 後，Android 能辨識手把的震動能力。`.ko` 在**核心空間**執行；使用者空間的腳本負責載入、切換綁定與復原。

## 下載與安裝

從 [v0.2.0 預覽版](https://github.com/29988122/xiaomi-controller-rumble/releases/tag/v0.2.0) 下載限定韌體的 ZIP 與 `SHA256SUMS`；[dist](dist/) 保存相同檔案。Magisk 與 KernelSU 系列共用 ZIP，但封裝相容不代表其中的核心二進位能用於不同核心。

1. 核對支援表全部條件，準備可用的 USB ADB 復原連線與自己手機的 boot 備份。
2. 連上**恰好一支** `054C:05C4` 的 DS4 藍牙手把，等一般輸入初始化完成；G8+ 是已實測型號。先斷開其他符合條件的手把。
3. 從正在運作的 root 管理器安裝；不支援 recovery 安裝。核心／ROM 不符、驅動毀損、零支／多支候選或初始化未完成，都會停止安裝。
4. 安裝程式只在**手機本機**記錄選定手把的識別碼，並預設**停用**。先重開機完成安裝，確認相容性及復原方式，再從管理器啟用並重開機。
5. 開機與藍牙重連後會重新接管；保留原有回報間隔，不擅自套用其他調校值。

手機上的模組不連網、不回傳資料，也不掛載或替換 `/system`，不需要為它安裝掛載用途的 metamodule 或 Zygisk。模組 ID 保留 `sony_g8ff_ruby`，避免與私人前版同時安裝兩個背景程序。更新會重新選定當下唯一已連線的手把，並再次預設停用。

### 查詢、停止與復原

在 root shell 中查詢：

```sh
sh /data/adb/modules/sony_g8ff_ruby/bin/g8ffctl status
```

立即停用並阻止下次開機載入：

```sh
touch /data/adb/modules/sony_g8ff_ruby/disable
sh /data/adb/modules/sony_g8ff_ruby/bin/g8ffctl stop
```

也可以從管理器關閉模組後重開機。`stop` 會停止本模組的背景程序、將指定手把交回原廠 `sony` 並卸載 `sony_g8ff`。若 Android 無法正常開機，請依管理器的復原文件處理：[Magisk](https://topjohnwu.github.io/Magisk/faq.html)、[KernelSU](https://kernelsu.org/guide/rescue-from-bootloop.html)。

ROM／核心更新後，版本不符就不載入。不要改版本檢查或 vermagic 強行安裝，應建立並驗證新的 profile。同一支手機改用整合 KernelSU 的核心，也可能需要重新建置。

## 實際驗證到哪裡

- 使用者先確認直接 HID 輸出的兩側震動，再確認標準 `FF_RUMBLE` 的兩側震動。
- Android 出現震動輸入映射器。修正初始化競爭後，連續三次藍牙重連通過。
- 螢幕 `Dozing → Awake`、重開機自動載入、停用恢復原廠及重新啟用通過；這不是深度休眠耐久測試。
- 該測試環境保持 4 ms 回報間隔，boot 雜湊未變；SELinux、CFI、MODVERSIONS 均未停用。
- 原有輸入介面仍存在。依使用者要求，**Steam Link、遊戲中的操作／延遲及 30 分鐘遊戲穩定性未測**。該環境先前已關閉 Low Latency Video，處理的是另一個延遲問題。
- `.ko` 重新建置的位元組完全一致；61 個必要匯出符號的 CRC 與獨立建置證據吻合，624 個計算出的匯出符號也都吻合。這些檢查不能取代執行驗證。

完整 [繁體中文](docs/writeup.zh-TW.md)／[English](docs/writeup.md) 文章記錄成功路徑、失敗的探測方法、九個列舉項目的還原，以及證據的限制。

## 開發與貢獻

```sh
python3 -m pip install pyelftools==0.33
python3 -m unittest discover -s tests -v
python3 tools/package.py
```

[建置與移植指南](docs/build-and-port.md) 包含固定來源／工具鏈、Linux 容器指令、ABI 檢查與新增 profile 的要求。profile 將版本假設和產物與共同安裝器分開，但現有建置、匯出表解析仍是 **ruby ARM64 的案例實作**，不是自動逆向所有核心的工具。

[回報問題](https://github.com/29988122/xiaomi-controller-rumble/issues) 時提供機型代號、ROM 指紋、核心版本、手把模式／VID:PID、root 管理器版本、失敗階段及最小化的去識別紀錄。不要上傳 boot、裝置位址、序號或完整系統傾印。新增 profile 必須有獨立 ABI 證據及暫時載入／復原結果，才能列為已支援；無法安全實測時先提交調查草稿。

## 致謝與授權

專案與實體測試由 [29988122](https://github.com/29988122) 主導，AI 協助調查、實作與文件。馬達實際運作由使用者確認，沒有把指令成功當成實體驗收；本專案不宣稱發明 Linux FF 或首次使用驅動重新綁定。

驅動源自 [Xiaomi 公開的 Sony HID 驅動](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/914ba8403bb3a957ed37b99dcecdbafce9d16121/drivers/hid/hid-sony.c)，保留上游作者與授權。新增程式採 GPL-2.0-or-later；匯入檔案遵循各自宣告。詳見 [LICENSE](LICENSE) 與[來源紀錄](docs/build-and-port.md#provenance)。
