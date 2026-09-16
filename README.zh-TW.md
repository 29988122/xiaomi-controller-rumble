# Xiaomi Controller Rumble

[English](README.md) · [技術文章](docs/writeup.zh-TW.md) · [建置與移植](docs/build-and-port.md) · [更新紀錄](CHANGELOG.md)

透過替代 Sony HID 驅動，補回指定紅米韌體缺少的藍牙手把震動，保留原本的 boot 映像。**附帶驅動限定韌體；調查方法可供其他機型移植參考。** 修復對象是手把馬達。

## 下載與安裝

下載 [v0.3.0 預覽版](https://github.com/29988122/xiaomi-controller-rumble/releases/tag/v0.3.0) 與 `SHA256SUMS`。[dist](dist/) 保留相同檔案。

1. 核對下方相容表。在 Magisk 或相容的 KernelSU 系列管理器選 ZIP 安裝，不用解壓縮。
2. **重新開機一次。** 首次安裝預設啟用。
3. 安裝時如果只有一支符合條件、已準備好的手把，程式會記住它。否則請把 G8+ 切成 DS4 藍牙模式，只連接這支符合條件的手把。
4. 按模組的 **「動作／Action」**，完成設定或檢查。它會測試左側一下、右側兩下的短震動，請確認是否有感覺。**不需要再重開機。**

安裝時沒有手把、初始化還沒完成，或連著多支候選，都能先完成安裝，保持「手把待設定」。尚未記住手把，或手把尚未就緒時，不載入替代驅動；背景服務也不會自行選擇其他手把。

按「動作」後，最多等待初始化 20 秒。若仍未成功，請把手把完全關機再開機，以 DS4 模式重新連線，再按一次。藍牙顯示「已連線」不代表 Sony 驅動已初始化；模組不會自行切換手機藍牙，也不跳過校正失敗。

**v0.3.0 的安裝、「動作」與服務流程尚未經手機實測。** 依使用者要求，本版以自動測試交付。核心 `.ko` 與先前實體測試過的驅動相同，但不能據此宣稱新流程已通過實機驗收。請保留 USB ADB 與自己的復原方式。

## 相容範圍

| 項目 | 範圍 |
|---|---|
| 手機 | Redmi Note 12 Pro 5G，`ruby`，`22101316G` |
| ROM | HyperOS `OS2.0.8.0.UMOTWXM`，Android 14 |
| 核心 | `4.19.191-gdecc267868f3`，ARM64 |
| 手把 | GameSir G8+，DS4 藍牙 `054C:05C4` |
| 過去的驅動實機驗證 | Magisk Alpha 30700，使用相同 `.ko` 的前版 |
| v0.3.0 新流程 | 模擬安裝／執行測試；**未實測手機安裝、重開機或「動作」震動** |
| KernelSU／Next | 共用 ZIP／腳本介面；**沒有實機驗證** |
| 其他手機、韌體或協定 | 此二進位不支援 |

本版沒有加入 Nintendo、Xbox、Steam Controller 的其他協定。Android／核心版本相近不代表相容；同一支手機換成 KernelSU 修補過的核心，也可能不再符合這份 profile。

模組不掛載 `/system`，不需要掛載用途的 metamodule 或 Zygisk。請使用支援「動作」按鈕、提供 BusyBox `flock`／`setsid` 的近期管理器；Shell 相容測試以 Magisk 30.7 為基準。手機上的模組不連網、不回傳資料，手把識別碼只留在手機。

## 更新與日常使用

- 安裝新版 ZIP 後重開機一次。模組 ID 維持 `sony_g8ff_ruby`，合法的舊手把設定會保留，更新時不必連著手把。
- 原本已停用的模組會維持停用。更新重開機後，開啟模組開關、按「動作」即可啟動，無須再重開機。
- 安裝／更新尚未重開機時按「動作」，會提醒先重開機，不會從暫存目錄啟動驅動。
- 開機與重新連線不主動測試馬達；只有按「動作」才短震動。
- 接上另一支手把，不會自動取代已記住的手把。本版尚無更換手把介面。
- 中文系統顯示繁體中文，其餘顯示英文。

## 停用與復原

在 root 管理器關閉模組。背景服務會在進行中的震動測試結束後，嘗試恢復原廠 Sony 驅動。若手把尚未恢復，請斷線重連，或保持模組停用並重新開機。

需要 root shell 診斷時：

```sh
sh /data/adb/modules/sony_g8ff_ruby/bin/g8ffctl status
```

立即停止並阻止下次開機啟動：

```sh
touch /data/adb/modules/sony_g8ff_ruby/disable
sh /data/adb/modules/sony_g8ff_ruby/bin/g8ffctl stop
```

ROM／核心不符會拒絕啟動，不要改檢查或 vermagic 強行安裝。其他復原方式參考 [Magisk](https://topjohnwu.github.io/Magisk/faq.html)／[KernelSU](https://kernelsu.org/guide/rescue-from-bootloop.html)。

## 驗證到哪裡

前版由使用者確認直接 HID 指令與標準 FF 都能讓兩邊馬達震動，並檢查三次藍牙重連、螢幕休眠喚醒、開機載入和停用恢復原廠。boot 雜湊未變，SELinux、CFI、MODVERSIONS 均未停用；這不是深度休眠耐久測試。Steam Link、遊戲操作／延遲和 30 分鐘遊戲測試仍未執行。

v0.3.0 沿用相同 `.ko`，但修改安裝／服務腳本與使用者空間的 FF 測試程式。測試程式會在打開輸入裝置後再次核對手把身分，避免斷線後輸入編號被其他裝置重用。它通過可重現交叉編譯及 QEMU 拒絕無法辨識裝置的檢查；新增的身分確認尚未在實體手把上測試。

自動測試模擬稍後設定、更新、停用、斷線、重複按鈕／服務和復原；CI 另使用 Magisk 真正的 x86_64 BusyBox Shell 與 `flock` 檢查腳本。sysfs 和管理器安裝輔助函式仍是模擬資料，不等於 Android 開機或管理器端到端驗收。詳見[建置與驗證說明](docs/build-and-port.md)。

## 開發與貢獻

```sh
python3 -m pip install pyelftools==0.33
python3 -m unittest discover -s tests -v
python3 tools/package.py
```

完整調查見[中文](docs/writeup.zh-TW.md)／[English](docs/writeup.md)，移植請看[建置指南](docs/build-and-port.md)。驅動的 61 個必要符號 CRC 與獨立證據吻合，624 個計算出的匯出符號與原廠吻合；這些是相容性證據，不能取代全部 ABI 與實機驗證。

[回報問題](https://github.com/29988122/xiaomi-controller-rumble/issues) 請附機型、ROM／核心、手把模式、管理器版本與最小化錯誤紀錄。請去除序號、藍牙位址，不上傳 boot 或完整系統傾印。新 profile 需要自己的建置、ABI 與實機證據。

## 致謝與授權

專案及實體測試由 [29988122](https://github.com/29988122) 主導，AI 協助調查、實作與文件；實體震動由使用者確認。專案不宣稱發明 Linux force feedback。

驅動源自 [Xiaomi 公開的 Sony HID 程式](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/914ba8403bb3a957ed37b99dcecdbafce9d16121/drivers/hid/hid-sony.c)，保留上游宣告。新增程式採 GPL-2.0-or-later，匯入檔案遵循各自授權。詳見 [LICENSE](LICENSE) 與[來源紀錄](docs/build-and-port.md#provenance)。
