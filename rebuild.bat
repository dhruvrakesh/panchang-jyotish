@echo off
setlocal
cd /d "%~dp0"
title Jyotish Panchang — Rebuild venv

echo.
echo  =========================================
echo   Full environment rebuild
echo  =========================================
echo.
echo  This will DELETE .venv and reinstall everything from requirements.txt.
echo  Press Ctrl+C to cancel, or
pause

REM ── Tear down ─────────────────────────────────────────────────────────────────
if exist ".venv" (
    echo [REBUILD] Removing old virtual environment...
    rmdir /s /q .venv
)

REM ── Locate Python (py launcher → python3 → python) ───────────────────────────
set PYTHON=
for %%P in (py python3 python) do (
    %%P --version >nul 2>&1 && set PYTHON=%%P && goto :found
)
echo [ERROR] Python not found. Install Python 3.10+ and add it to PATH.
pause & exit /b 1

:found
echo [REBUILD] Using: %PYTHON%
%PYTHON% --version

REM ── Create fresh venv ─────────────────────────────────────────────────────────
echo [REBUILD] Creating virtual environment...
%PYTHON% -m venv .venv
if errorlevel 1 ( echo [ERROR] venv creation failed. & pause & exit /b 1 )

REM ── Install deps ──────────────────────────────────────────────────────────────
echo [REBUILD] Upgrading pip...
.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel -q

echo [REBUILD] Installing requirements...
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 ( echo [ERROR] Install failed. & pause & exit /b 1 )

echo. > .venv\.deps_installed

echo.
echo [REBUILD] Done. Run run.bat to start the app.
echo.
pause
endlocal
