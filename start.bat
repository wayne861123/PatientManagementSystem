@echo off
REM ============================================================
REM  醫師門診管理系統 - 開發者一鍵啟動
REM  自動建立/更新虛擬環境後啟動程式
REM ============================================================

cd /d "%~dp0"

echo [1/3] 檢查 Python 版本...
where python >nul 2>&1
if errorlevel 1 (
    echo [錯誤] 找不到 Python，請先安裝 Python 3.11 或以上版本
    echo 下載: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [2/3] 同步相依套件...
where uv >nul 2>&1
if errorlevel 1 (
    echo [提示] 找不到 uv，改用 pip...
    python -m pip install --quiet -r requirements.txt
    if errorlevel 1 (
        echo [錯誤] 相依套件安裝失敗
        pause
        exit /b 1
    )
) else (
    uv sync --all-extras
    if errorlevel 1 (
        echo [錯誤] 相依套件安裝失敗
        pause
        exit /b 1
    )
)

echo [3/3] 啟動程式...
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe app.py
) else (
    python app.py
)

pause
