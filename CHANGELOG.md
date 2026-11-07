# Changelog

本專案遵循 [語意化版本](https://semver.org/lang/zh-TW/)。

## [未發布]

## [1.1.3] - 2026-11-07

### 修正
- 修正側邊欄出現兩個「系統設定」項目的問題：`templates/base.html` 中
  `<li><a id="settings" ...>系統設定</a></li>` 在 commit `e5895fc` 新增系統設定頁面時
  被複製貼上兩次，導致每個頁面的側邊欄都顯示兩個「系統設定」，且頁面上出現重複的
  DOM id `settings`（HTML 規範要求 id 唯一，`getElementById` 只會取到第一個）。
  移除重複的一行後即恢復正確；另補上逐頁檢查的重複 id 回歸測試
- 修正 `static/settings.js` 的 `switchVersion()` 缺少結尾 `}` 造成的括號不平衡：
  該缺陷使 `createBackup` / `checkIntegrity` / `restoreBackup` 三個函式被巢狀在
  `switchVersion()` 內部而非全域函式，導致設定頁的「立即建立備份」「檢查資料庫完整性」
  「還原」按鈕在瀏覽器中拋出 `ReferenceError` 而失效，且檔案最後的
  `DOMContentLoaded` 監聽器也從未註冊。移除「選擇版本」功能時一併修好

### 改變
- 移除「系統設定」頁面的「選擇版本」功能：移除版本下拉選單、「切換至此版本」按鈕
  與版本清單，同時移除對應的 `/api/list/versions`、`/api/switch/version` 兩個 API
  與 `settings.js` 的 `loadVersions()` / `switchVersion()`。套用更新（檢查更新／
  下載並安裝更新）與資料備份功能不受影響
- `uv.lock` 不再納入版控，改由 `uv sync` 依 `pyproject.toml` 即時解析

## [1.1.2] - 2026-10-29

### 修正
- 修正用藥歷史頁面「藥物類型」與「藥物名稱」錯配的問題：
  `traditional_medicines` 與 `biological_medicines` 兩張表的 id 各自從 1 開始，
  後端卻將兩張表的名稱載入同一個對照字典，導致生物製劑覆蓋掉同 id 的傳統用藥
  （例如「傳統用藥」顯示為 Adalimumab）。改為分別建立兩張對照表
- 修正用藥歷史分組未納入藥物類型的問題：分組鍵改為 `(類型, 藥物名稱)`，
  避免兩類藥物同名時被併為同一群組
- 修正用藥歷史頁面 DOM id 重複的問題：兩張用藥紀錄表的 id 會重複，
  導致「編輯／保存／取消」作用到錯誤的記錄。DOM id 改為帶上類型前綴
  （如 `form-traditional-4`）
- 修正用藥歷史頁面刪除生物製劑時刪錯資料表的問題：刪除按鈕未傳入藥物類型，
  後端一律視為傳統用藥
- 解除 `tests/test_history_grouping.py` 的 skip（原註解所述的模板結構問題並不存在），
  並新增藥物名稱與類型對應的回歸測試

## [1.1.1] - 2026-10-23

### 改變
- **執行檔改為 console 版本**：保留黑色視窗顯示即時訊息（啟動資訊、資料位置、
  日誌位置），方便使用者與管理員排查問題。啟動訊息並會提示
  「請勿關閉此視窗，關閉將會停止服務」與停止方式（Ctrl+C）
- 日誌同步輸出至 console（打包模式下，INFO 以上等級）

### 修正
- 打包時若先前的執行檔仍在執行，會自動結束該程序後再清理，
  避免因檔案被鎖定而打包失敗

## [1.1.0] - 2026-10-20

### 新增
- **Windows 執行檔打包**：透過 PyInstaller 產出 onedir 形式的執行檔，
  使用者免安裝 Python 即可使用（`build_exe.py`）
- **GitHub Actions 自動發佈**：推送 `v*` tag 後自動測試、打包、產生 Release
  與 SHA256 checksum（`.github/workflows/release.yml`）
- **CI 流程**：push / PR 時自動執行測試與打包驗證（`.github/workflows/ci.yml`）
- **系統設定頁面**（`/settings`）：查看版本、檢查更新、選擇版本切換、
  管理資料庫備份
- **自動更新功能**：從 GitHub Releases 檢查新版本、下載、驗證 checksum
  並安裝（`version.py` / `updater.py`）
- **版本切換**：可切換至任何已發布的歷史版本
- **資料庫備份機制**（`backup.py`）：
  - 每日自動備份（啟動時補建立）
  - 升級前快照（永久保留）
  - 完整性檢查與自動還原
  - zlib 壓縮 + 保留上限控制（預設 14 份，約 170KB）
- **路徑管理模組**（`paths.py`）：程式資源與使用者資料分離

### 改變
- **資料與程式分離**：資料庫、上傳檔案、日誌、備份改存於
  `%LOCALAPPDATA%\PatientManagementSystem`（打包模式），更新程式不影響資料
- **日誌輪替**：`FileHandler` 改為 `RotatingFileHandler`（2MB × 3），
  避免日誌無限膨脹
- 修正 `pyproject.toml` 的 entry point（`app:main` 原本不存在導致無法安裝執行）
- 新增 `main()` 進入點，支援 `PMS_HOST` / `PMS_PORT` / `PMS_DEBUG` 環境變數
- 打包模式下自動開啟瀏覽器

### 修正
- 修正用藥歷史群組標題顯示數字 id 而非藥物名稱的問題
  （`name` 欄位為 TEXT 型別，與 INTEGER id 比對時型別不符）
- 修正 PASI 照片寫入 `static/uploads`（打包後為唯讀暫存目錄會遺失），
  改為寫入使用者資料夾

### 資料
- 測試資料每位病患的用藥紀錄提升至 24 筆（傳統用藥 3 種 + 生物製劑 2 種）
- 種子資料的病患狀態與性別對齊系統實際列舉值

## [1.0.0]

- 初始版本：病患管理、用藥紀錄、檢查項目、PASI 計算機、審計日誌
