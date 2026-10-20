# Doctor's Clinic Management System

A Flask-based patient management system for tracking patient information, medical history, medication records, and doctor assignments.

## 快速開始

### 一般使用者（不需要安裝 Python）

1. 到 [Releases](https://github.com/wayne861123/PatientManagementSystem/releases) 下載最新版
2. 解壓縮到任意資料夾（例如 `C:\PatientManagementSystem`）
3. 執行 `PatientManagementSystem.exe`
4. 瀏覽器開啟 http://127.0.0.1:5000

> 程式啟動後會自動開啟瀏覽器視窗（若未開啟請手動開啟上述網址）。

首次啟動時資料庫為空，可直接開始建立病患資料。

### 開發者

```bash
# 1. 建立虛擬環境（Python 3.11）
uv venv --python 3.11
uv sync --all-extras

# 2. 啟動
uv run python app.py

# 3. 執行測試
uv run pytest

# 4. 建立測試資料（開發者工具，不會打包進執行檔）
uv run python scripts/seed_data.py --clean
```

Windows 使用者可直接執行 `start.bat` 一鍵啟動。

## 資料存放位置

**程式與資料完全分離** — 更新程式不會影響您的資料。

| 執行模式 | 資料位置 |
|---|---|
| 打包執行檔 | `%LOCALAPPDATA%\PatientManagementSystem\` |
| 原始碼開發 | 專案根目錄 |

資料夾結構：

```
PatientManagementSystem\
├── patients.db      # 資料庫
├── backups\         # 自動備份（壓縮）
├── documents\       # 上傳的 PDF 文件
├── uploads\         # PASI 照片
├── logs\            # 執行日誌（自動輪替）
└── updates\         # 更新檔暫存
```

可用環境變數 `PMS_DATA_DIR` 自訂位置。

## 版本與更新

在「**系統設定**」頁面（側邊欄最下方）可：

- 查看目前版本與最新版本
- **檢查更新**並一鍵下載安裝（更新前自動建立資料庫快照）
- **選擇版本**：切換至任何已發布的歷史版本
- 查看與還原資料庫備份

### 發佈新版本（維護者）

```bash
# 1. 更新版本號（pyproject.toml 的 version 是單一真相來源）
#    version = "1.2.0"

# 2. 更新 CHANGELOG.md

# 3. 打包驗證
uv run python build_exe.py --clean

# 4. 提交並打 tag（GitHub Actions 會自動發佈 Release）
git commit -am "release: v1.2.0"
git tag v1.2.0
git push origin main --tags
```

推上 tag 後，[`.github/workflows/release.yml`](.github/workflows/release.yml) 會自動：

1. 執行測試
2. 打包成 Windows 執行檔
3. 壓縮成 zip 並計算 SHA256
4. 建立 GitHub Release

## 資料備份與還原

系統提供多層資料保護：

| 機制 | 說明 |
|---|---|
| **每日備份** | 程式啟動時若今天尚未備份則自動建立 |
| **升級前快照** | 更新／切換版本前必定建立，且永久保留 |
| **完整性檢查** | 每次啟動執行 `PRAGMA integrity_check` |
| **自動還原** | 偵測到資料庫損毀時自動從最新備份還原 |
| **手動備份** | 設定頁可隨時建立備份 |

備份使用 zlib 壓縮（SQLite 資料庫壓縮比約 8.6%），139KB 的資料庫僅佔約 12KB。
預設保留 14 份每日備份，總用量約 170KB。

```bash
# 命令列工具
uv run python backup.py list     # 列出備份
uv run python backup.py check    # 檢查完整性
uv run python backup.py stats    # 統計資訊
```

可用環境變數調整：

| 變數 | 說明 | 預設 |
|---|---|---|
| `PMS_BACKUP_KEEP` | 每日備份保留份數 | `14` |
| `PMS_BACKUP_DISABLE` | 設為 `1` 停用自動備份 | 停用 |
| `PMS_DATA_DIR` | 自訂資料夾位置 | 依執行模式 |
| `PMS_OFFLINE` | 設為 `1` 停用所有網路請求 | 停用 |
| `PMS_UPDATE_DISABLED` | 設為 `1` 停用自動更新 | 停用 |
| `PMS_HOST` / `PMS_PORT` | 監聽位址與埠號 | `127.0.0.1:5000` |
| `PMS_DEBUG` | 設為 `1` 開啟除錯模式 | 關閉 |
| `PMS_NO_BROWSER` | 設為 `1` 不自動開啟瀏覽器 | 開啟 |

## Features

### Patient Management
- **Patient Registration** - Register new patients with personal info, doctor assignment, and disease diagnosis
- **Patient Search & Filter** - Find patients by doctor, disease type, or keyword search (name, medical record number, ID number)
- **Patient Profile** - View complete patient history including demographics, medications, and examinations

### Dashboard & Reminders
- **Home Dashboard** (`/`) - Overview of all doctors with color-coded reminders:
  - Red alerts: Follow-up within 1 day OR biological drug dose depleted
  - Yellow alerts: Follow-up within 3 days OR biological drug dose ≤ 1
  - Only shows active patients (not "discharged")

### Medication Management
- **Traditional Medicine Records** - Track follow-up dates with configurable intervals
- **Biological Agent Records** - Track injection doses, application types (first/continue), and remaining doses
- **Additional Medications** - Support for supplementary medicines

### Examination Tracking
- **Examination Management** - Configurable examination items with follow-up intervals
- **Examination Records** - Log and track patient examination results over time
- **Examination History** - View all past examination records for a patient

### Clinical Tools
- **PASI Score Calculator** (`/pasi`) - Psoriasis Area and Severity Index assessment tool
- **Injection Frequency Calculator** (`/injection-frequency`) - Calculate injection schedules

### Data Management
- **Management Pages** - CRUD operations for doctors, diseases, examinations, and medicines
- **Audit Log System** - Records all database changes with timestamp, operator, and IP address
- **Data Rollback** - Revert any incorrect changes via CLI tools

## Pages & Routes

| Page | Route | Description |
|------|-------|-------------|
| **Home** | `/` | Dashboard showing all doctors with follow-up and dose reminders |
| **All Patients** | `/all-patients` | Filterable patient list by doctor, disease, or keyword |
| **Doctor Detail** | `/doctor/<id>` | View doctor's assigned diseases and patient counts |
| **Doctor's Patients** | `/doctor/<id>/disease/<id>` | List patients for a specific doctor-disease combination |
| **Patient Detail** | `/patient/<id>` | Full patient profile with medication & examination history |
| **Add Patient** | `/add_patient` | Register new patient with doctor and disease assignment |
| **Examination History** | `/history/examination/<id>` | All examination records for a patient |
| **Medicine History** | `/history/medicine/<id>` | Timeline of all medication records (traditional & biological) |
| **PASI Score** | `/pasi` | Calculator for Psoriasis Area and Severity Index |
| **Injection Frequency** | `/injection-frequency` | Tool to calculate injection schedules |
| **Manage Doctors** | `/management/doctors` | Add/edit/delete doctor records |
| **Manage Diseases** | `/management/diseases` | Add/edit/delete disease types |
| **Manage Examinations** | `/management/examinations` | Add/edit/delete examination items |
| **Manage Medicines** | `/management/medicines` | Add/edit/delete traditional & biological medicines |

## Setup

本專案使用 Python 3.11 + [uv](https://github.com/astral-sh/uv) 管理環境與依賴。

### 前置需求

- Python 3.11+
- [uv](https://github.com/astral-sh/uv)（建議安裝：`pip install uv` 或 `curl -LsSf https://astral.sh/uv/install.sh | sh`）

### 環境建置

```bash
# 1. 建立虛擬環境（Python 3.11）
uv venv --python 3.11

# 2. 啟動虛擬環境（Windows PowerShell）
.venv\Scripts\activate.ps1
# 或 CMD：
# .venv\Scripts\activate.bat

# 3. 安裝依賴（會自動解析並鎖定版本到 uv.lock）
uv sync

# 4. 初始化資料庫（首次執行時自動建立）
python app.py

# 5. 開啟瀏覽器
# http://localhost:5000
```

### 更新依賴

```bash
# 新增或更新 dependencies 後，重新 lock 並安裝
uv lock
uv sync
```

## CLI Tools

The system includes a command-line tool for managing audit logs and data rollback:

```bash
# Query audit logs
python cli.py logs --table patients --limit 20
python cli.py logs --action INSERT --limit 50

# View log details
python cli.py log 123

# Preview rollback SQL (dry-run)
python cli.py revert 123 --dry-run

# Execute data rollback
python cli.py revert 123 --execute

# Interactive mode
python cli.py interactive
```

### Interactive Mode Commands
- `log <id>` - View log details
- `revert <id>` - Generate and optionally execute rollback SQL
- `tables` - List all database tables
- `exit` - Exit interactive mode

## Database Tables

- `patients` - Patient demographics and assignments
- `doctors` - Doctor records
- `diseases` - Disease types
- `traditional_medicines` - Traditional medication catalog
- `traditional_medicine_record` - Traditional medication logs
- `biological_medicines` - Biological agent catalog
- `biological_medicine_record` - Biological agent injection logs
- `examinations` - Examination item definitions
- `examination_record` - Patient examination results
- `pasi_records` - PASI score history
- `additional_medicines` - Supplementary medications
- `audit_log` - System audit trail

## Tech Stack

- **Backend**: Python Flask
- **Database**: SQLite
- **Frontend**: HTML5/CSS3/JavaScript (Jinja2 templates)
- **Logging**: File-based audit logs with rotation

## Project Structure

```
PatientManagementSystem/
|-- app.py              # Flask application and routes
|-- database.py         # Database initialization and utilities
|-- paths.py            # 路徑管理（程式資源 vs 使用者資料）
|-- backup.py           # 資料庫備份／還原／完整性檢查
|-- version.py          # 版本查詢與比較
|-- updater.py          # 自動更新
|-- build_exe.py        # PyInstaller 打包腳本
|-- cli.py              # Command-line audit tools
|-- patients.db         # SQLite database (dev mode)
|-- logs/               # Application logs
|-- static/
|   |-- style.css       # Stylesheets
|   |-- script.js       # Client-side JavaScript
|   `-- settings.js     # 設定頁面 JavaScript
`-- templates/
    |-- base.html       # Base template
    |-- home.html       # Dashboard
    |-- all_patients.html
    |-- patient_detail.html
    |-- add_patient.html
    |-- doctor.html
    |-- doctor_disease_patients.html
    |-- examination_history.html
    |-- history.html
    |-- management.html
    |-- settings.html   # 版本與備份
    |-- pasi_score.html
    `-- new_medication.html
```

> `scripts/`（種子資料）、`tests/`（測試）為開發者工具，不會上傳至 GitHub，
> 也不會打包進使用者拿到的執行檔。
