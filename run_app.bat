@echo off
chcp 65001 >nul
echo ========================================
echo     啟動彩券539 應用程式
echo ========================================
echo.

REM 檢查並安裝後端依賴
echo [1/3] 檢查後端依賴...
cd /d "%~dp0backend"
if not exist "venv" (
    echo     建立虛擬環境...
    python -m venv venv
)
call venv\Scripts\activate.bat
pip install -r requirements.txt -q
echo     後端依賴完成
echo.

REM 啟動後端伺服器 (在新的命令提示字元視窗)
echo [2/3] 啟動後端伺服器...
start "Backend Server - 彩券539 API" cmd /k "cd /d "%~dp0backend" && call venv\Scripts\activate.bat && uvicorn main:app --reload --host 127.0.0.1 --port 8000"

REM 等待一下讓後端啟動
timeout /t 3 /nobreak >nul

REM 啟動前端開發伺服器
echo [3/3] 啟動前端伺服器...
cd /d "%~dp0frontend"
start "Frontend Server - 彩券539" cmd /k "npm run dev"

echo.
echo ========================================
echo     應用程式已啟動！
echo     後端: http://127.0.0.1:8000
echo     前端: http://localhost:5173
echo     API文檔: http://127.0.0.1:8000/docs
echo ========================================
echo.
echo 按任意鍵關閉此視窗（伺服器將繼續執行）...
pause >nul
