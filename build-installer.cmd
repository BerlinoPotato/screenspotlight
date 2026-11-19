@echo off
cd /d "%~dp0"
py installer\build_installer.py %*
if errorlevel 1 (
    pause
    exit /b 1
)
pause
