@echo off
chcp 65001 >nul
echo ========================================
echo     啟動彩券539 前端伺服器
echo ========================================
echo.

cd /d "%~dp0frontend"

REM 檢查 node_modules 是否存在
if not exist "node_modules" (
    echo     安裝 Node.js 依賴...
    call npm install
)

echo.
echo     啟動開發伺服器中...
echo     前端網址: http://localhost:5173
echo.

REM 啟動 Vite 開發伺服器
npm run dev
