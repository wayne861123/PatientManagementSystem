#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自動更新模組

流程：
  1. 下載新版（顯示進度）
  2. 驗證 SHA256 checksum（若 Release 提供）
  3. 建立「升級前快照」備份（保護使用者資料）
  4. 取代執行檔
  5. 提示使用者重啟

安全設計：
  - 更新前必定建立 DB 快照，且快照永久保留（不被淘汰）
  - 下載檔案先驗證完整性才會安裝
  - 取代失敗時保留原執行檔，不會讓程式變成無法啟動
  - 非打包模式（開發者）不提供自我更新

環境變數：
  PMS_UPDATE_DISABLED  設為 1 可停用自動更新
"""

import hashlib
import os
import shutil
import sys
import urllib.error
import urllib.request
import zipfile

import backup
import paths
import version


# 下載逾時（秒）
DOWNLOAD_TIMEOUT = 30

# 更新包檔名
UPDATE_PACKAGE_NAME = "update.zip"


def update_disabled():
    """自動更新是否停用"""
    return os.environ.get("PMS_UPDATE_DISABLED", "").lower() in ("1", "true", "yes")


def can_self_update():
    """目前環境是否支援自我更新

    只有打包後的執行檔才能自我更新（開發模式下替換自身沒有意義）。
    """
    return paths.is_frozen() and not update_disabled()


def _sha256(path, chunk=1024 * 1024):
    """計算檔案 SHA256"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            block = f.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def _expected_checksum(release):
    """從 Release 資產中找出 checksum 檔案的內容"""
    if not release:
        return None
    for asset in release.get('assets', []):
        name = asset.get('name', '').lower()
        if 'checksum' in name or name.endswith('.sha256'):
            try:
                req = urllib.request.Request(asset['url'], headers={
                    "User-Agent": f"{paths.APP_NAME}/{version.current_version()}",
                })
                with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT) as resp:
                    text = resp.read().decode('utf-8', errors='replace')
                # 格式: "<hash>  <filename>"
                return text.strip().split()[0] if text.strip() else None
            except (urllib.error.URLError, urllib.error.HTTPError, OSError):
                return None
    return None


def download_update(url, dest_dir=None, progress=None):
    """下載更新檔

    Args:
        url: 下載網址
        dest_dir: 儲存目錄（預設為 updates 資料夾）
        progress: 進度回呼函式 callback(downloaded, total)

    Returns:
        str or None: 下載後的檔案路徑；失敗時回傳 None
    """
    if not url:
        return None

    dest_dir = dest_dir or paths.updates_dir()
    try:
        os.makedirs(dest_dir, exist_ok=True)
    except OSError:
        return None

    dest = os.path.join(dest_dir, UPDATE_PACKAGE_NAME)
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": f"{paths.APP_NAME}/{version.current_version()}",
        })
        with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT) as resp:
            total = int(resp.headers.get('Content-Length') or 0)
            downloaded = 0
            with open(dest, "wb") as f:
                while True:
                    chunk = resp.read(1024 * 256)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress:
                        progress(downloaded, total)
        return dest
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        print(f"[ update error ] 下載失敗: {e}")
        if os.path.exists(dest):
            try:
                os.remove(dest)
            except OSError:
                pass
        return None


def verify_download(file_path, expected_sha256):
    """驗證下載檔的 checksum

    Args:
        file_path: 檔案路徑
        expected_sha256: 預期 checksum；None 表示略過驗證

    Returns:
        tuple: (成功與否, 訊息)
    """
    if not expected_sha256:
        return True, "（未提供 checksum，略過驗證）"
    if not file_path or not os.path.exists(file_path):
        return False, "下載檔不存在"

    actual = _sha256(file_path)
    if actual.lower() != expected_sha256.lower():
        return False, f"checksum 不符（預期 {expected_sha256[:12]}...，實際 {actual[:12]}...）"
    return True, "checksum 驗證通過"


def extract_package(zip_path, dest_dir=None):
    """解壓縮更新包

    為防止路徑穿越（zip slip），會檢查解壓後的路徑是否仍在目標資料夾內。

    Returns:
        str or None: 解壓目標目錄；失敗時回傳 None
    """
    dest_dir = dest_dir or paths.updates_dir()
    try:
        os.makedirs(dest_dir, exist_ok=True)
    except OSError:
        return None

    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for member in zf.namelist():
                # 防止 zip slip
                target = os.path.normpath(os.path.join(dest_dir, member))
                if not target.startswith(os.path.abspath(dest_dir)):
                    return None
            zf.extractall(dest_dir)
        return dest_dir
    except (zipfile.BadZipFile, OSError) as e:
        print(f"[ update error ] 解壓失敗: {e}")
        return None


def _find_new_exe(extracted_dir):
    """在解壓後的資料夾中找出新的執行檔"""
    for root, _dirs, files in os.walk(extracted_dir):
        for f in files:
            if f.lower().endswith('.exe'):
                return os.path.join(root, f)
    return None


def apply_update(extracted_dir):
    """套用更新：取代目前的執行檔

    步驟：
      1. 建立「升級前快照」備份（保護使用者資料）
      2. 將舊執行檔改名保留（若失敗可回退）
      3. 複製新執行檔到位

    Returns:
        tuple: (成功與否, 訊息)
    """
    if not paths.is_frozen():
        return False, "開發模式下不支援自我更新"

    new_exe = _find_new_exe(extracted_dir)
    if not new_exe:
        return False, "更新包中找不到執行檔"

    current_exe = sys.executable
    if not os.path.exists(current_exe):
        return False, "找不到目前的執行檔"

    # 1. 升級前快照（永久保留）
    snapshot = backup.create_backup("upgrade")
    if snapshot:
        print(f"[ update ] 已建立升級前快照: {os.path.basename(snapshot)}")

    # 2. 將舊執行檔改名保留（取代失敗時可回退）
    old_exe = current_exe + ".old"
    try:
        if os.path.exists(old_exe):
            os.remove(old_exe)
        os.replace(current_exe, old_exe)
    except OSError as e:
        return False, f"無法取代執行檔（請先關閉程式）: {e}"

    # 3. 複製新執行檔
    try:
        shutil.copy2(new_exe, current_exe)
    except OSError as e:
        # 失敗則回退，確保程式仍可啟動
        try:
            shutil.move(old_exe, current_exe)
            return False, f"更新失敗，已回退至原版本: {e}"
        except OSError:
            return False, f"更新失敗且回退失敗，請手動復原 {old_exe}: {e}"

    return True, "更新已安裝，請重新啟動程式"


def perform_update(release=None, progress=None):
    """完整的更新流程

    Args:
        release: 要更新的 Release dict；None 表示取最新版本
        progress: 下載進度回呼

    Returns:
        tuple: (成功與否, 訊息)
    """
    if not can_self_update():
        return False, "此環境不支援自動更新"

    if release is None:
        release = version.fetch_latest_release()
    if not release or 'error' in release:
        return False, "無法取得更新資訊"

    asset = version.find_asset(release, keyword=None, suffix=".zip")
    if not asset:
        return False, "此版本沒有可用的更新包（.zip）"

    # 1. 下載
    print(f"[ update ] 下載中: {asset['name']}")
    zip_path = download_update(asset['url'], progress=progress)
    if not zip_path:
        return False, "下載失敗"

    # 2. 驗證 checksum
    expected = _expected_checksum(release)
    ok, msg = verify_download(zip_path, expected)
    if not ok:
        return False, f"完整性驗證失敗: {msg}"
    print(f"[ update ] {msg}")

    # 3. 解壓
    extracted = extract_package(zip_path)
    if not extracted:
        return False, "解壓失敗"

    # 4. 套用
    return apply_update(extracted)

