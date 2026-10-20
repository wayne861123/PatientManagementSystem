#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""路徑管理模組

集中管理程式資源（唯讀）與使用者資料（可寫）的路徑，支援兩種執行模式：

1. 開發模式（直接執行 python app.py）
   - 程式資源：專案根目錄
   - 使用者資料：專案根目錄（保持既有行為，資料就近存放）

2. 打包模式（PyInstaller 產生的 .exe）
   - 程式資源：sys._MEIPASS（唯讀，隨 exe 散佈）
   - 使用者資料：%LOCALAPPDATA%\\PatientManagementSystem（可寫，不隨程式更新）

設計原則：**資料與程式分離**。更新程式只會替換程式資源，
使用者資料（資料庫、上傳檔案、日誌、備份）完全不受影響。

環境變數：
  PMS_DATA_DIR   覆寫使用者資料夾位置（測試與進階使用者使用）
"""

import os
import sys

APP_NAME = "PatientManagementSystem"
APP_TITLE = "醫師門診管理系統"


def is_frozen():
    """是否為 PyInstaller 打包後的執行環境"""
    return bool(getattr(sys, "frozen", False))


def app_dir():
    """程式資源根目錄（唯讀）

    - 打包模式：sys._MEIPASS（單檔模式會解壓到暫存目錄）
    - 開發模式：目前檔案所在目錄
    """
    if is_frozen():
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def _default_data_dir():
    """作業系統慣用的使用者資料夾"""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return os.path.join(base, APP_NAME)


def data_dir():
    """使用者資料根目錄（可寫）

    - 打包模式：%LOCALAPPDATA%\\PatientManagementSystem
    - 開發模式：專案根目錄
    - 皆可由環境變數 PMS_DATA_DIR 覆寫
    """
    override = os.environ.get("PMS_DATA_DIR")
    if override:
        return os.path.abspath(override)
    if is_frozen():
        return _default_data_dir()
    return app_dir()


def ensure_data_dirs():
    """建立所有需要的資料夾，回傳建立結果的 dict"""
    targets = {
        "data": data_dir(),
        "backups": backup_dir(),
        "logs": log_dir(),
        "documents": documents_dir(),
        "uploads": uploads_dir(),
        "updates": updates_dir(),
    }
    for path in targets.values():
        os.makedirs(path, exist_ok=True)
    return targets


def db_path():
    """資料庫檔案路徑"""
    return os.path.join(data_dir(), "patients.db")


def backup_dir():
    """資料庫備份資料夾"""
    return os.path.join(data_dir(), "backups")


def log_dir():
    """日誌資料夾"""
    return os.path.join(data_dir(), "logs")


def documents_dir():
    """使用者上傳文件（PDF）資料夾"""
    return os.path.join(data_dir(), "documents")


def uploads_dir():
    """PASI 照片等上傳檔案資料夾"""
    return os.path.join(data_dir(), "uploads")


def pasi_upload_dir(record_id):
    """PASI 照片依紀錄分資料夾"""
    return os.path.join(uploads_dir(), f"pasi_record_{record_id}")


def updates_dir():
    """更新檔案暫存資料夾"""
    return os.path.join(data_dir(), "updates")


def config_path():
    """設定檔路徑"""
    return os.path.join(data_dir(), "config.json")


def templates_dir():
    """模板資料夾（程式資源）"""
    return os.path.join(app_dir(), "templates")


def static_dir():
    """靜態資源資料夾（程式資源）"""
    return os.path.join(app_dir(), "static")


def legacy_db_path():
    """舊版資料庫位置（打包前的專案根目錄），供資料遷移使用"""
    return os.path.join(app_dir(), "patients.db")


if __name__ == "__main__":
    print(f"frozen      : {is_frozen()}")
    print(f"app_dir     : {app_dir()}")
    print(f"data_dir    : {data_dir()}")
    print(f"db_path     : {db_path()}")
    print(f"backup_dir  : {backup_dir()}")
    print(f"log_dir     : {log_dir()}")
    print(f"documents   : {documents_dir()}")
    print(f"uploads     : {uploads_dir()}")
    print(f"config      : {config_path()}")
