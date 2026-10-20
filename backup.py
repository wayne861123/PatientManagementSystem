#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""資料庫備份與還原模組

設計目標：保護使用者資料，避免版本更新或意外操作導致資料遺失，
同時控制磁碟用量。

機制：
  1. 每日備份：程式啟動時檢查今天是否已備份，沒有就補一份
  2. 升級前快照：更新程式前必定建立一份，永久保留
  3. 完整性檢查：啟動時執行 PRAGMA integrity_check，損毀時自動還原
  4. 保留上限：預設保留 14 份每日備份，淘汰舊檔

空間控制：備份使用 zlib 壓縮（實測 SQLite 資料庫壓縮比約 8.6%），
139KB 的資料庫僅佔約 12KB，保留 14 份亦僅約 170KB。

環境變數：
  PMS_BACKUP_KEEP     每日備份保留份數（預設 14）
  PMS_BACKUP_DISABLE  設為 1 可停用自動備份
"""

import os
import re
import shutil
import sqlite3
import zlib
from datetime import datetime

import paths


# 每日備份預設保留份數
DEFAULT_KEEP = 14

# 永久保留的備份原因（不參與淘汰）
PINNED_REASONS = ("upgrade", "manual", "restore")

# 備份檔名格式：<時間戳>-<原因>.db.z（同秒內多次建立會加流水號）
BACKUP_PATTERN = re.compile(r"^(\d{8}-\d{6})-(.+?)(?:-\d+)?\.db\.z$")


def _keep_count():
    """取得要保留的每日備份份數"""
    try:
        return max(1, int(os.environ.get("PMS_BACKUP_KEEP", DEFAULT_KEEP)))
    except ValueError:
        return DEFAULT_KEEP


def _disabled():
    """是否停用自動備份"""
    return os.environ.get("PMS_BACKUP_DISABLE", "").lower() in ("1", "true", "yes")


def _db_file():
    """目前資料庫檔案路徑"""
    return paths.db_path()


def backup_enabled():
    """自動備份是否啟用"""
    return not _disabled()


def _timestamp():
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _unique_dest(reason):
    """產生不重複的備份檔路徑。

    時間戳僅精確到秒，同一秒內建立的備份會互相覆蓋，
    因此需加上流水號確保唯一性。
    """
    base = _timestamp()
    dest = os.path.join(paths.backup_dir(), f"{base}-{reason}.db.z")
    seq = 1
    while os.path.exists(dest) or os.path.exists(dest + ".tmp"):
        dest = os.path.join(paths.backup_dir(), f"{base}-{reason}-{seq}.db.z")
        seq += 1
    return dest


def create_backup(reason="daily", db_path=None):
    """建立一份壓縮備份。

    使用 SQLite Online Backup API 取得一致性快照（不阻塞其他連線，
    也不會取得寫到一半的檔案），再以 zlib 壓縮。

    Args:
        reason: 備份原因（daily / upgrade / manual / restore）
        db_path: 來源資料庫（預設為目前資料庫）

    Returns:
        str or None: 備份檔路徑；失敗時回傳 None
    """
    src_path = db_path or _db_file()
    if not os.path.exists(src_path):
        return None

    try:
        os.makedirs(paths.backup_dir(), exist_ok=True)
    except OSError:
        return None

    dest = _unique_dest(reason)
    tmp_raw = dest + ".tmp"

    try:
        # 1. 一致性快照
        src = sqlite3.connect(src_path)
        dst = sqlite3.connect(tmp_raw)
        src.backup(dst)
        dst.close()
        src.close()

        # 2. 壓縮
        with open(tmp_raw, "rb") as fin:
            raw = fin.read()
        with open(dest, "wb") as fout:
            fout.write(zlib.compress(raw, 9))
        os.remove(tmp_raw)

        return dest
    except (sqlite3.Error, OSError) as e:
        print(f"[ backup error ] 建立備份失敗: {e}")
        if os.path.exists(tmp_raw):
            try:
                os.remove(tmp_raw)
            except OSError:
                pass
        return None


def list_backups():
    """列出所有備份（新的在前）

    Returns:
        list: [{'path', 'name', 'reason', 'created_at', 'size', 'pinned'}]
    """
    backup_dir = paths.backup_dir()
    if not os.path.isdir(backup_dir):
        return []

    items = []
    for fname in os.listdir(backup_dir):
        m = BACKUP_PATTERN.match(fname)
        if not m:
            continue
        stamp, reason = m.group(1), m.group(2)
        fpath = os.path.join(backup_dir, fname)
        try:
            size = os.path.getsize(fpath)
        except OSError:
            continue
        try:
            created = datetime.strptime(stamp, "%Y%m%d-%H%M%S")
        except ValueError:
            created = datetime.min
        items.append({
            'path': fpath,
            'name': fname,
            'reason': reason,
            'created_at': created,
            'size': size,
            'pinned': reason in PINNED_REASONS,
        })

    items.sort(key=lambda x: x['created_at'], reverse=True)
    return items


def prune_backups(keep=None):
    """淘汰舊的每日備份，保留最近 keep 份與所有永久保留的備份。

    Returns:
        list: 被刪除的檔案路徑
    """
    if keep is None:
        keep = _keep_count()

    daily = [b for b in list_backups() if not b['pinned']]

    removed = []
    for item in daily[keep:]:
        try:
            os.remove(item['path'])
            removed.append(item['path'])
        except OSError:
            pass
    return removed


def backup_stats():
    """備份統計資訊

    Returns:
        dict: {'count', 'total_size', 'keep', 'enabled', 'latest'}
    """
    backups = list_backups()
    return {
        'count': len(backups),
        'total_size': sum(b['size'] for b in backups),
        'keep': _keep_count(),
        'enabled': backup_enabled(),
        'latest': backups[0] if backups else None,
    }

def ensure_daily_backup():
    """確保今天已有備份（若無則建立一份）。程式啟動時呼叫。

    Returns:
        str or None: 建立的備份路徑；今日已備份或停用時回傳 None
    """
    if not backup_enabled():
        return None

    today = datetime.now().strftime("%Y%m%d")
    for item in list_backups():
        if item['created_at'].strftime("%Y%m%d") == today and item['reason'] == "daily":
            return None

    path = create_backup("daily")
    if path:
        prune_backups()
    return path


def verify_integrity(db_path=None):
    """檢查資料庫完整性

    Returns:
        dict: {'ok': bool, 'message': str}
    """
    path = db_path or _db_file()
    if not os.path.exists(path):
        return {'ok': False, 'message': '資料庫不存在'}

    try:
        conn = sqlite3.connect(path)
        result = conn.execute("PRAGMA integrity_check").fetchone()
        conn.close()
        if result and result[0] == "ok":
            return {'ok': True, 'message': 'ok'}
        return {'ok': False, 'message': result[0] if result else '未知錯誤'}
    except sqlite3.Error as e:
        return {'ok': False, 'message': str(e)}


def restore_backup(backup_path, db_path=None):
    """從備份還原資料庫。

    還原前會先為現況資料建立一份 'restore' 備份，確保可逆。

    Args:
        backup_path: 備份檔路徑
        db_path: 目標資料庫路徑（預設為目前資料庫）

    Returns:
        tuple: (成功與否, 訊息)
    """
    target = db_path or _db_file()

    if not os.path.exists(backup_path):
        return False, f"備份檔不存在: {backup_path}"

    # 還原前先保留現況
    if os.path.exists(target):
        create_backup("restore", db_path=target)

    try:
        with open(backup_path, "rb") as fin:
            raw = zlib.decompress(fin.read())

        tmp = target + ".restore.tmp"
        with open(tmp, "wb") as fout:
            fout.write(raw)

        # 驗證解壓縮後的檔案確實是有效的 SQLite
        conn = sqlite3.connect(tmp)
        check = conn.execute("PRAGMA integrity_check").fetchone()
        conn.close()
        if not check or check[0] != "ok":
            os.remove(tmp)
            return False, f"備份檔損毀: {check[0] if check else '未知'}"

        # 覆蓋（Windows 上若檔案被鎖定會失敗，此時原檔仍在）
        shutil.move(tmp, target)
        return True, "還原成功"
    except (OSError, zlib.error, sqlite3.Error) as e:
        return False, f"還原失敗: {e}"


def auto_recover_if_corrupt():
    """啟動時呼叫：若資料庫損毀，自動從最新備份還原。

    Returns:
        dict: {'recovered': bool, 'message': str}
    """
    check = verify_integrity()
    if check['ok']:
        return {'recovered': False, 'message': '資料庫正常'}

    backups = list_backups()
    if not backups:
        return {'recovered': False,
                'message': f"資料庫損毀且無備份可還原: {check['message']}"}

    latest = backups[0]
    ok, msg = restore_backup(latest['path'])
    if ok:
        return {'recovered': True, 'message': f"已從 {latest['name']} 自動還原"}
    return {'recovered': False, 'message': f"自動還原失敗: {msg}"}


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "list":
        for b in list_backups():
            flag = "*" if b['pinned'] else " "
            print(f" {flag} {b['created_at']:%Y-%m-%d %H:%M:%S}  {b['reason']:<8} "
                  f"{b['size']:>8,} bytes  {b['name']}")
    elif len(sys.argv) > 1 and sys.argv[1] == "check":
        print(verify_integrity())
    elif len(sys.argv) > 1 and sys.argv[1] == "stats":
        print(backup_stats())
    else:
        print("用法: python backup.py [list|check|stats]")
