@echo off
cd /d "%~dp0"
if not exist server_v2.py (
    echo [ERROR] server_v2.py not found in current directory
    echo [ERROR] Cannot start - target integrity check failed
    pause
    exit /b 1
)
python server_v2.py
if errorlevel 1 (
    echo [ERROR] server_v2.py execution failed
    pause
    exit /b 1
)
pause
