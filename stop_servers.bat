@echo off
chcp 65001 >nul
echo ========================================
echo     停止彩券539 伺服器
echo ========================================
echo.

REM 終止後端伺服器 (uvicorn)
echo     正在停止後端伺服器...
taskkill /F /IM uvicorn.exe 2>nul
taskkill /F /IM python.exe 2>nul

REM 終止前端伺服器 (node/vite)
echo     正在停止前端伺服器...
taskkill /F /IM node.exe 2>nul

echo.
echo     伺服器已停止
echo ========================================
