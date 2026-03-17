@echo off
chcp 65001 >nul
echo ========================================
echo     啟動彩券539 後端伺服器
echo ========================================
echo.

cd /d "%~dp0backend"

REM 檢查虛擬環境是否存在
if not exist "venv" (
    echo     建立虛擬環境...
    python -m venv venv
)

REM 啟動虛擬環境
call venv\Scripts\activate.bat

REM 安裝依賴
echo     安裝依賴...
pip install -r requirements.txt -q

echo.
echo     啟動伺服器中...
echo     API 文檔: http://127.0.0.1:8000/docs
echo.

REM 啟動 FastAPI 伺服器
uvicorn main:app --reload --host 127.0.0.1 --port 8000
