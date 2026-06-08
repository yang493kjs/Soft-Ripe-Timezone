@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

title Soft-Ripe Timezone AI Lover - Launcher

set ROOT_DIR=%~dp0
set BACKEND_DIR=%ROOT_DIR%backend
set FRONTEND_DIR=%ROOT_DIR%frontend
set BACKEND_PORT=8765

set PYTHON_CMD=python
set NPM_CMD=npm

cls

echo ============================================================
echo       Soft-Ripe Timezone AI Lover -- One-Click Start
echo ============================================================
echo.

echo [1/5] Checking environment...

where %PYTHON_CMD% >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)
python -c "import sys; exit(0) if sys.version_info >= (3,10) else exit(1)" >nul 2>&1
if %errorlevel% neq 0 (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo [WARN] %%v
) else (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo [OK] %%v
)

where %NPM_CMD% >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] npm not found. Please install Node.js 16+
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('npm --version 2^>^&1') do echo [OK] npm v%%v

echo.

echo [2/5] Installing backend dependencies...
cd /d "%BACKEND_DIR%"
pip install -r requirements.txt -q --disable-pip-version-check 2>nul
if %errorlevel% equ 0 (
    echo [OK] Backend dependencies ready
) else (
    echo [WARN] pip install failed, retrying...
    pip install -r requirements.txt --disable-pip-version-check
)
echo.

echo [3/5] Building frontend...
cd /d "%FRONTEND_DIR%"
if not exist node_modules (
    echo    Installing frontend dependencies...
    npm install --silent
)
echo    Building production frontend...
call npm run build
if !errorlevel! equ 0 (
    echo [OK] Frontend build completed
) else (
    echo [WARN] Frontend build failed. Run npm run build manually.
)
echo.

echo [4/5] Cleaning up existing processes...
cd /d "%ROOT_DIR%"

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%BACKEND_PORT%"') do (
    if not "%%a"=="" (
        echo    Killing process on port %BACKEND_PORT% PID: %%a
        taskkill /F /PID %%a >nul 2>&1
    )
)
timeout /t 1 /nobreak >nul
echo [OK] Port cleaned
echo.

echo [5/5] Starting server...
echo.

cd /d "%BACKEND_DIR%"
echo [START] Server (backend + frontend, port %BACKEND_PORT%)...
echo.
echo ============================================================
echo                SERVER STARTING...
echo.
echo   The browser will open automatically when ready.
echo.
echo   To stop: Close the server window, or press any key
echo ============================================================
echo.

start "Soft-Ripe Timezone" cmd /c "title Soft-Ripe Timezone & python main.py & pause"

echo.
echo Press any key to stop the server...
pause >nul

echo.
echo Stopping server...
taskkill /FI "WINDOWTITLE eq Soft-Ripe Timezone" /F >nul 2>&1
echo [OK] Server stopped
echo.

pause