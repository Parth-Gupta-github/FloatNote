@echo off
setlocal enabledelayedexpansion
set "ELECTRON_RUN_AS_NODE="
title FloatNote Desktop
cd /d "%~dp0"

echo ========================================================
echo   FloatNote Desktop Launcher
echo ========================================================
echo Current directory: %CD%

if not exist "node_modules\electron\dist\electron.exe" (
    echo [ERROR] Electron binary not found in node_modules!
    echo Running npm install...
    call npm install
)

echo Launching FloatNote Electron window...
start "" "node_modules\electron\dist\electron.exe" .
echo [OK] Launched FloatNote!
timeout /t 3 >nul
