#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PyInstaller 打包腳本

建立 Windows 執行檔。設計為 onedir（資料夾模式）：
  - 啟動快（不需每次解壓到暫存目錄）
  - 更新時只需替換 exe 檔

用法：
  python build_exe.py            # 一般打包
  python build_exe.py --clean    # 先清除舊的建置產物

產出：
  dist/PatientManagementSystem/PatientManagementSystem.exe

發佈（搭配 GitHub Actions）：
  將 dist/PatientManagementSystem 打包為 zip 即可作為 Release 資產。
"""

import argparse
import os
import shutil
import subprocess
import sys

# Windows 預設的 console 編碼為 cp1252，無法輸出中文，
# 會造成 UnicodeEncodeError 使腳本無法執行（常見於 CI 環境）。
# 此處強制以 UTF-8 輸出，並在無法重新設定時忽略編碼錯誤。
def _force_utf8_output():
    """確保 stdout/stderr 能輸出中文"""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")


_force_utf8_output()

APP_NAME = "PatientManagementSystem"
ROOT = os.path.dirname(os.path.abspath(__file__))


def read_version():
    """從 pyproject.toml 讀取版本（單一真相來源）"""
    import re
    pyproject = os.path.join(ROOT, "pyproject.toml")
    with open(pyproject, "r", encoding="utf-8") as f:
        m = re.search(r'^\s*version\s*=\s*"([^"]+)"', f.read(), re.MULTILINE)
    return m.group(1) if m else "0.0.0"


def clean():
    """清除舊的建置產物"""
    for d in ("build", "dist"):
        path = os.path.join(ROOT, d)
        if os.path.exists(path):
            shutil.rmtree(path, ignore_errors=True)
            print(f"  [OK] Removed {d}/")
    # PyInstaller 自動產生的 .spec 檔
    spec = os.path.join(ROOT, f"{APP_NAME}.spec")
    if os.path.exists(spec):
        os.remove(spec)
        print(f"  [OK] Removed {APP_NAME}.spec")
    # PyInstaller 快取
    for d in ("__pycache__",):
        path = os.path.join(ROOT, d)
        if os.path.exists(path):
            shutil.rmtree(path, ignore_errors=True)


def check_requirements():
    """檢查打包所需套件是否已安裝"""
    missing = []
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        missing.append("pyinstaller")
    if missing:
        print(f"[ error ] 缺少套件: {', '.join(missing)}")
        print("  安裝指令: uv add --dev pyinstaller")
        return False
    return True


def build():
    """執行 PyInstaller 打包"""
    version = read_version()

    # 產生 version_info.txt（供程式讀取版本）
    version_file = os.path.join(ROOT, "version_info.txt")
    with open(version_file, "w", encoding="utf-8") as f:
        f.write(version)
    print(f"  [OK] version_info.txt: {version}")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name", APP_NAME,
        "--windowed",              # 不顯示 console 視窗
        "--onedir",               # 資料夾模式（啟動快、易更新）
        "--add-data", f"templates{os.pathsep}templates",
        "--add-data", f"static{os.pathsep}static",
        "--add-data", f"version_info.txt{os.pathsep}.",
        "--hidden-import", "flask",
        "--hidden-import", "werkzeug",
        "--hidden-import", "jinja2",
        "--collect-submodules", "flask",
        "--exclude-module", "tkinter",
        "--exclude-module", "matplotlib",
        "--exclude-module", "numpy",
        "--exclude-module", "pytest",
        "app.py",                 # 進入點
    ]

    print("  [..] 執行 PyInstaller ...")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        print("[ error ] PyInstaller 打包失敗")
        return False

    # 檢查產出
    dist_dir = os.path.join(ROOT, "dist", APP_NAME)
    exe_path = os.path.join(dist_dir, f"{APP_NAME}.exe")
    if not os.path.exists(exe_path):
        print(f"[ error ] 找不到產出的執行檔: {exe_path}")
        return False

    # 產生 checksum 檔（供自動更新驗證完整性）
    import hashlib
    h = hashlib.sha256()
    with open(exe_path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    checksum_file = os.path.join(dist_dir, f"{APP_NAME}.exe.sha256")
    with open(checksum_file, "w", encoding="utf-8") as f:
        f.write(f"{h.hexdigest()}  {APP_NAME}.exe\n")
    print(f"  [OK] checksum: {h.hexdigest()[:16]}...")

    print(f"\n  打包完成: {exe_path}")
    print(f"  發佈方式: 將 dist\\{APP_NAME} 整個資料夾壓縮成 zip 上傳至 GitHub Release")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", action="store_true", help="先清除舊的建置產物")
    args = parser.parse_args()

    print("=" * 50)
    print(f"  {APP_NAME} - PyInstaller 打包")
    print("=" * 50)

    if args.clean:
        print("\n[STEP 0] 清除舊產物...")
        clean()

    if not check_requirements():
        sys.exit(1)

    print("\n[STEP 1] 打包...")
    sys.exit(0 if build() else 1)
