import sqlite3
import os
import json
import logging
import sys
from logging.handlers import RotatingFileHandler
from datetime import datetime
from functools import wraps

import paths


# 程式資源（唯讀）與使用者資料（可寫）路徑
BASE_PATH = paths.app_dir()
DATA_DIR = paths.data_dir()
DB_NAME = paths.db_path()

# 日誌輪替設定：單檔上限 2MB，保留 3 個歷史檔（共最多 8MB）
LOG_MAX_BYTES = 2 * 1024 * 1024
LOG_BACKUP_COUNT = 3

# ===========================================================================
# Logging 設定
# ===========================================================================

def setup_logging():
    """設定檔案日誌（支援輪替，避免日誌無限膨脹佔用磁碟）

    打包模式為 console 版本時，額外將日誌同步輸出到 console，
    使用者可即時看到訊息而不必開啟日誌檔。
    """
    log_dir = paths.log_dir()
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, "app.log")
    
    logger = logging.getLogger("wen2")
    logger.setLevel(logging.DEBUG)
    
    # 檔案處理器（輪替）
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    
    # 格式
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    if not logger.handlers:
        logger.addHandler(file_handler)

    # Console 輸出（僅在有 console 可用時，例如打包後的 console 版本）
    if paths.is_frozen() and sys.stdout is not None:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)-7s | %(message)s',
            datefmt='%H:%M:%S'
        ))
        logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

# 定義每個表的欄位結構 (col_name: default_value)
TABLES = {
    "patients": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "name": "TEXT",
        "gender": "TEXT",
        "birthday": "TEXT",
        "phone": "TEXT",
        "mobile": "TEXT",
        "medical_record_number": "TEXT",
        "id_number": "TEXT",
        "city": "TEXT",
        "district": "TEXT",
        "address": "TEXT",
        "doctor_id": "INTEGER",
        "disease_id": "INTEGER",
        "status": "TEXT",
        "remark": "TEXT"
    },
    "doctors": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "name": "TEXT",
        "disable": "INTEGER"
    },
    "diseases": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "name": "TEXT",
        "disable": "INTEGER"
    },
    "traditional_medicines": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "name": "TEXT",
        "type": "TEXT",
        "followup_interval": "INTEGER",
        "disable": "INTEGER"
    },
    "traditional_medicine_record": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "record_id": "INTEGER",
        "patient_id": "INTEGER",
        "name": "TEXT",
        "followup_date": "TEXT DEFAULT (datetime('now', 'localtime'))",
        "next_followup_date": "TEXT DEFAULT (datetime('now', 'localtime'))",
        "remark": "TEXT",
        "additional_medicine": "TEXT"
    },
    "biological_medicines": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "name": "TEXT",
        "type": "TEXT",
        "first_apply_dose": "INTEGER",
        "continue_apply_dose": "INTEGER",
        "disable": "INTEGER"
    },
    "biological_medicine_record": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "record_id": "INTEGER",
        "patient_id": "INTEGER",
        "name": "TEXT",
        "apply_type": "TEXT",
        "remain_dose": "INTEGER",
        "followup_date": "TEXT DEFAULT (datetime('now', 'localtime'))",
        "next_followup_date": "TEXT DEFAULT (datetime('now', 'localtime'))",
        "remark": "TEXT",
        "additional_medicine": "TEXT"
    },
    "examinations": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "name": "TEXT",
        "interval": "INTEGER",
        "unit": "TEXT",
        "disable": "INTEGER"
    },
    "examination_record": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "patient_id": "INTEGER",
        "name": "TEXT",
        "check_date": "TEXT",
        "result": "TEXT",
        "remark": "TEXT"
    },
    "audit_log": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "action": "TEXT",
        "table_name": "TEXT",
        "record_id": "INTEGER",
        "old_data": "TEXT",
        "new_data": "TEXT",
        "sql_statement": "TEXT",
        "reverse_sql": "TEXT",
        "operator": "TEXT DEFAULT 'system'",
        "created_at": "TEXT DEFAULT (datetime('now', 'localtime'))",
        "ip_address": "TEXT"
    },
    "pasi_records": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "patient_id": "INTEGER",
        "pasi_score": "REAL",
        "severity": "TEXT",
        "erythema_head": "INTEGER",
        "infiltrate_head": "INTEGER",
        "desquamation_head": "INTEGER",
        "area_head": "INTEGER",
        "erythema_upper": "INTEGER",
        "infiltrate_upper": "INTEGER",
        "desquamation_upper": "INTEGER",
        "area_upper": "INTEGER",
        "erythema_trunk": "INTEGER",
        "infiltrate_trunk": "INTEGER",
        "desquamation_trunk": "INTEGER",
        "area_trunk": "INTEGER",
        "erythema_lower": "INTEGER",
        "infiltrate_lower": "INTEGER",
        "desquamation_lower": "INTEGER",
        "area_lower": "INTEGER",
        "image_path": "TEXT",
        "remark": "TEXT",
        "created_at": "TEXT DEFAULT (datetime('now', 'localtime'))"
    },
    "additional_medicines": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "name": "TEXT",
        "disable": "INTEGER"
    },
    "todos": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "content": "TEXT",
        "is_done": "INTEGER DEFAULT 0",
        "created_at": "TEXT DEFAULT (datetime('now', 'localtime'))"
    },
    "documents": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "original_name": "TEXT",
        "stored_name": "TEXT",
        "file_type": "TEXT",
        "file_size": "INTEGER",
        "created_at": "TEXT DEFAULT (datetime('now', 'localtime'))"
    },
    "patient_contacts": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "patient_id": "INTEGER",
        "relationship": "TEXT",
        "name": "TEXT",
        "phone": "TEXT",
        "created_at": "TEXT DEFAULT (datetime('now', 'localtime'))"
    }
}


def get_existing_columns(cursor, table_name):
    """取得資料表中已存在的欄位"""
    # 驗證 table_name 只包含允許的字元（英數字和底線），防止 SQL 注入
    import re
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
        raise ValueError(f"無效的資料表名稱: {table_name}")
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cursor.fetchall()}


def migrate_table(cursor, table_name, columns):
    """檢查並新增缺少的欄位"""
    existing = get_existing_columns(cursor, table_name)
    expected = set(columns.keys())
    missing = expected - existing
    
    for col in missing:
        col_type = columns[col]
        default = ""
        if "DEFAULT" in col_type:
            # 如果有預設值，直接使用
            sql = f"ALTER TABLE {table_name} ADD COLUMN {col} {col_type}"
        else:
            # 沒有預設值時給 NULL
            sql = f"ALTER TABLE {table_name} ADD COLUMN {col} {col_type}"
        
        try:
            cursor.execute(sql)
            print(f"[ migrated ] {table_name}: 新增欄位 {col}")
        except sqlite3.Error as e:
            print(f"[ error ] {table_name}.{col}: {e}")


def migrate_legacy_data():
    """資料遷移：從舊位置（專案根目錄）搬移到新的資料夾。

    打包後首次執行時，資料庫位於舊的程式資料夾。
    此處會將其搬移到使用者資料夾，並保留原檔作為 .migrated 備份。

    Returns:
        str or None: 遷移說明字串，未遷移則回傳 None
    """
    if not paths.is_frozen():
        return None

    target = paths.db_path()
    if os.path.exists(target):
        return None

    legacy = paths.legacy_db_path()
    if not os.path.exists(legacy):
        return None

    try:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        # 以 SQLite Online Backup API 取得一致性快照
        src = sqlite3.connect(legacy)
        dst = sqlite3.connect(target)
        src.backup(dst)
        dst.close()
        src.close()

        # 保留原檔，不刪除（避免使用者資料遺失）
        keep = legacy + ".migrated"
        if not os.path.exists(keep):
            os.replace(legacy, keep)
        return f"資料庫已從 {legacy} 遷移至 {target}（原檔保留為 {keep}）"
    except sqlite3.Error as e:
        print(f"[ error ] 資料遷移失敗: {e}")
        return None


def init_db():
    # 打包模式首次執行時，先嘗試搬移舊資料
    migration_msg = migrate_legacy_data()
    if migration_msg:
        print(f"[ migrated ] {migration_msg}")

    os.makedirs(os.path.dirname(DB_NAME), exist_ok=True)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 檢查並建立每個表
    for table_name, columns in TABLES.items():
        # 檢查表是否存在
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        exists = cursor.fetchone() is not None
        
        if not exists:
            # 建立新表
            cols_sql = ", ".join([f"{col} {ctype}" for col, ctype in columns.items()])
            cursor.execute(f"CREATE TABLE {table_name} ({cols_sql})")
            print(f"[ created ] table: {table_name}")
        else:
            # 檢查並新增缺少的欄位
            migrate_table(cursor, table_name, columns)
    
    conn.commit()
    conn.close()

def get_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_NAME)
    conn.text_factory = str
    conn.row_factory = sqlite3.Row
    return conn


def fetch_one(cursor, query, params=None):
    """安全的 fetchone，包裝空值檢查"""
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        result = cursor.fetchone()
        return dict(result) if result else None
    except sqlite3.Error as e:
        print(f"[ database error ] {e}")
        return None


def fetch_all(cursor, query, params=None):
    """安全的 fetchall，包裝空值檢查"""
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        results = cursor.fetchall()
        return [dict(row) for row in results] if results else []
    except sqlite3.Error as e:
        print(f"[ database error ] {e}")
        return []


def execute_one(cursor, query, params=None):
    """執行 INSERT/UPDATE/DELETE 並返回受影響行數"""
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor.rowcount
    except sqlite3.Error as e:
        print(f"[ database error ] {e}")
        raise


def validate_required_fields(data, required_fields):
    """驗證必填欄位
    
    Args:
        data: 請求資料（dict）
        required_fields: 必填欄位列表
    
    Returns:
        (bool, str): (是否通過, 錯誤訊息)
    """
    missing = [field for field in required_fields if not data.get(field)]
    if missing:
        return False, f"缺少必填欄位: {', '.join(missing)}"
    return True, ""


def safe_int(value, default=None):
    """安全轉換為整數"""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_date(value):
    """安全解析日期格式"""
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


# ===========================================================================
# Audit Log 功能
# ===========================================================================

def log_db_action(cursor, action, table_name, record_id, old_data, new_data,
                  sql_statement="", operator="system", ip_address=None):
    """記錄資料庫操作到 audit_log

    Args:
        cursor: 資料庫 cursor
        action: 操作類型 (INSERT/UPDATE/DELETE)
        table_name: 資料表名稱
        record_id: 被操作的資料 ID
        old_data: 變更前的資料 (dict 或 None)
        new_data: 變更後的資料 (dict 或 None)
        sql_statement: 原始 SQL 語句
        operator: 操作者
        ip_address: IP 位址
    """
    # 產生反向 SQL
    reverse_sql = generate_reverse_sql(action, table_name, record_id, old_data, new_data)

    # Defensive: ensure dicts are serialized to JSON strings for SQLite binding
    def _to_json(val):
        if val is None:
            return None
        if isinstance(val, str):
            return val
        try:
            return json.dumps(val, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(val)

    # 記錄到 audit_log 表
    cursor.execute("""
        INSERT INTO audit_log (action, table_name, record_id, old_data, new_data,
                              sql_statement, reverse_sql, operator, ip_address)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        action,
        table_name,
        record_id,
        _to_json(old_data),
        _to_json(new_data),
        sql_statement if sql_statement else "",
        reverse_sql if reverse_sql else "",
        operator if operator else "",
        ip_address,
    ))

    return cursor.lastrowid


def _escape_sql_value(value):
    """跳脫 SQL 字串值（雙單引號 + 包裹）"""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    # 字串：跳脫單引號與反斜線
    escaped = str(value).replace("\\", "\\\\").replace("'", "''")
    return f"'{escaped}'"


def generate_reverse_sql(action, table_name, record_id, old_data, new_data):
    """根據操作類型產生反向 SQL
    
    Args:
        action: 操作類型 (INSERT/UPDATE/DELETE)
        table_name: 資料表名稱
        record_id: 記錄 ID
        old_data: 舊資料
        new_data: 新資料
    
    Returns:
        str: 反向 SQL 語句
    """
    if action == "INSERT":
        # INSERT 的反向是 DELETE
        return f"DELETE FROM {table_name} WHERE id = {int(record_id)}"
    
    elif action == "UPDATE":
        # UPDATE 的反向是用 old_data 覆蓋
        if old_data:
            sets = []
            for key, value in old_data.items():
                if key == "id":  # 不更新 id
                    continue
                sets.append(f"{key} = {_escape_sql_value(value)}")
            if sets:
                return f"UPDATE {table_name} SET {', '.join(sets)} WHERE id = {int(record_id)}"
        return None
    
    elif action == "DELETE":
        # DELETE 的反向是重新 INSERT
        if new_data:
            columns = list(new_data.keys())
            values = [_escape_sql_value(v) for v in new_data.values()]
            return f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(values)})"
        return None
    
    return None


def get_audit_logs(cursor, table_name=None, record_id=None, action=None, 
                   limit=50, offset=0):
    """查詢審計日誌
    
    Args:
        cursor: 資料庫 cursor
        table_name: 資料表名稱 (可選)
        record_id: 記錄 ID (可選)
        action: 操作類型 (可選)
        limit: 限制筆數
        offset: 偏移量
    
    Returns:
        list: 審計日誌列表
    """
    query = "SELECT * FROM audit_log WHERE 1=1"
    params = []
    
    if table_name:
        query += " AND table_name = ?"
        params.append(table_name)
    
    if record_id:
        query += " AND record_id = ?"
        params.append(record_id)
    
    if action:
        query += " AND action = ?"
        params.append(action)
    
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    return cursor.fetchall()


def get_audit_log_by_id(cursor, log_id):
    """根據 ID 取得單筆記錄"""
    cursor.execute("SELECT * FROM audit_log WHERE id = ?", (log_id,))
    return cursor.fetchone()


