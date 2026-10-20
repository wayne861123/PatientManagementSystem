#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""版本管理模組

提供：
  - 取得目前版本（打包模式讀取 version_info.txt，開發模式讀 pyproject.toml）
  - 查詢 GitHub Releases 的最新版本與歷史版本
  - 語意化版本比較

環境變數：
  PMS_REPO         GitHub 倉庫（owner/repo），預設使用內建值
  PMS_API_BASE     GitHub API 根路徑（可改為 GHE 或測試用 mock server）
  PMS_OFFLINE      設為 1 時完全離線，不做任何網路請求
"""

import json
import os
import re
import urllib.error
import urllib.request

import paths


# 預設倉庫（打包時可由建置腳本覆寫）
DEFAULT_REPO = "wayne861123/PatientManagementSystem"
DEFAULT_API_BASE = "https://api.github.com"

# 連線逾時（秒）
REQUEST_TIMEOUT = 15

# 語意化版本格式
SEMVER_PATTERN = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:[-.]?(.+))?$")


def _repo():
    return os.environ.get("PMS_REPO", DEFAULT_REPO)


def _api_base():
    return os.environ.get("PMS_API_BASE", DEFAULT_API_BASE).rstrip("/")


def offline():
    """是否為離線模式"""
    return os.environ.get("PMS_OFFLINE", "").lower() in ("1", "true", "yes")


# ===========================================================================
# 目前版本
# ===========================================================================

def _version_from_pyproject():
    """從 pyproject.toml 讀取版本（開發模式）"""
    pyproject = os.path.join(paths.app_dir(), "pyproject.toml")
    if not os.path.exists(pyproject):
        return None
    try:
        with open(pyproject, "r", encoding="utf-8") as f:
            content = f.read()
        m = re.search(r'^\s*version\s*=\s*"([^"]+)"', content, re.MULTILINE)
        if m:
            return m.group(1)
    except OSError:
        pass
    return None


def _version_from_file():
    """從 version_info.txt 讀取版本（打包模式）"""
    info = os.path.join(paths.app_dir(), "version_info.txt")
    if not os.path.exists(info):
        return None
    try:
        with open(info, "r", encoding="utf-8") as f:
            return f.read().strip() or None
    except OSError:
        return None


def current_version():
    """取得目前版本字串

    優先序：version_info.txt（打包） > pyproject.toml（開發） > "unknown"
    """
    return _version_from_file() or _version_from_pyproject() or "unknown"


def is_frozen_build():
    """是否為打包後的執行檔"""
    return paths.is_frozen()


# ===========================================================================
# 語意化版本比較
# ===========================================================================

def parse_version(v):
    """解析版本字串為 (major, minor, patch, prerelease)

    Args:
        v: 版本字串，如 "v1.2.3" 或 "1.2.3"

    Returns:
        tuple or None: 無法解析時回傳 None
    """
    if not v:
        return None
    m = SEMVER_PATTERN.match(str(v).strip())
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)),
            m.group(4) or "")


def compare_versions(a, b):
    """比較兩個版本

    Returns:
        int: a > b 回傳 1，a < b 回傳 -1，相等回傳 0
              無法解析時回傳 0
    """
    pa, pb = parse_version(a), parse_version(b)
    if pa is None or pb is None:
        return 0

    for i in range(3):
        if pa[i] != pb[i]:
            return 1 if pa[i] > pb[i] else -1

    # 正式版 > 預覽版
    if pa[3] == pb[3]:
        return 0
    if pa[3] == "":
        return 1
    if pb[3] == "":
        return -1
    return 1 if pa[3] > pb[3] else -1


def is_newer(candidate, current):
    """candidate 是否比 current 新"""
    return compare_versions(candidate, current) > 0


# ===========================================================================
# GitHub Releases 查詢
# ===========================================================================

def _api_get(url):
    """執行 GitHub API GET 請求，回傳已解析的 JSON"""
    if offline():
        raise urllib.error.URLError("離線模式，未發出網路請求")

    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{paths.APP_NAME}/{current_version()}",
    })
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _release_summary(rel):
    """將 GitHub Release 資料轉為精簡 dict"""
    return {
        'tag': rel.get('tag_name', ''),
        'name': rel.get('name') or rel.get('tag_name', ''),
        'url': rel.get('html_url', ''),
        'published_at': rel.get('published_at', ''),
        'body': rel.get('body', ''),
        'assets': [
            {
                'name': a.get('name', ''),
                'url': a.get('browser_download_url', ''),
                'size': a.get('size', 0),
            }
            for a in rel.get('assets', [])
        ],
    }


def fetch_latest_release():
    """取得最新的 Release 資訊

    Returns:
        dict or None: {'tag', 'name', 'url', 'published_at', 'body', 'assets'}
                      查詢失敗時回傳 None
    """
    try:
        data = _api_get(f"{_api_base()}/repos/{_repo()}/releases/latest")
    except urllib.error.HTTPError as e:
        return {'error': f"HTTP {e.code} {e.reason}"}
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError):
        return None

    if not isinstance(data, dict) or 'tag_name' not in data:
        return None

    return _release_summary(data)


def fetch_all_releases():
    """取得所有 Release（新的在前）

    Returns:
        list: [{'tag', 'name', 'url', 'published_at', 'body', 'assets'}]
    """
    try:
        data = _api_get(f"{_api_base()}/repos/{_repo()}/releases")
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError,
            TimeoutError, OSError):
        return []

    if not isinstance(data, list):
        return []

    return [_release_summary(rel) for rel in data]


def find_asset(release, keyword=None, suffix=".zip"):
    """在 Release 中找到符合的資產

    Args:
        release: Release dict
        keyword: 檔名關鍵字（如 exe 平台名稱）
        suffix: 副檔名過濾（預設 .zip）

    Returns:
        dict or None: 符合的資產
    """
    if not release:
        return None
    for asset in release.get('assets', []):
        name = asset.get('name', '').lower()
        if suffix and not name.endswith(suffix):
            continue
        if keyword and keyword.lower() not in name:
            continue
        return asset
    return None


def check_for_update():
    """檢查是否有新版本

    Returns:
        dict: {'current', 'latest', 'has_update', 'error', 'release'}
    """
    current = current_version()
    latest = fetch_latest_release()

    if latest is None:
        return {'current': current, 'latest': None, 'has_update': False,
                'error': '無法連線取得版本資訊', 'release': None}

    if 'error' in latest:
        return {'current': current, 'latest': None, 'has_update': False,
                'error': latest['error'], 'release': None}

    return {
        'current': current,
        'latest': latest.get('tag', ''),
        'has_update': is_newer(latest.get('tag', ''), current),
        'error': None,
        'release': latest,
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "latest":
        print(fetch_latest_release())
    elif len(sys.argv) > 1 and sys.argv[1] == "releases":
        for r in fetch_all_releases():
            print(f"  {r['tag']:<12} {r['published_at'][:10]}  {r['name']}")
    else:
        print("目前版本:", current_version())
        print("檢查更新:", check_for_update())
