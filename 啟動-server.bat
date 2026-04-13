@echo off
REM 關閉佔用 8765 連接埠的程式
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8765 ^| findstr LISTENING') do taskkill /f /pid %%a 2>nul
timeout /t 1 /nobreak >nul

REM 啟動服務器
cd /d %~dp0
cmd /k python server_v2.py