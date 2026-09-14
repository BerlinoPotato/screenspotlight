@echo off
cd /d "%~dp0"
py plar\prepare_runner.py
if errorlevel 1 (
    pause
    exit /b 1
)
py -m PyInstaller --noconfirm --clean ScreenSpotlight.spec
if errorlevel 1 (
    pause
    exit /b 1
)
echo Built dist\ScreenSpotlight.exe
pause
