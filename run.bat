@echo off
setlocal EnableDelayedExpansion

REM run.bat - Jyotish Panchang launcher (v12, 2026-07-20)
REM Rewritten pure-ASCII with CRLF line endings: cmd.exe misparses LF-only
REM batch files and executes line fragments ('rnet', '6.', '-m' errors).

title Jyotish Panchang - Launching...
cd /d "%~dp0"

echo.
echo  =========================================
echo   Jyotish Panchang ^& Horoscope  v12
echo  =========================================
echo.

REM -- 1. Locate Python ------------------------------------------------------
set PYTHON=
if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
    goto :check_deps
)

REM Try py launcher (preferred on Windows), then bare python3/python
for %%P in (py python3 python) do (
    %%P --version >nul 2>&1 && set PYTHON=%%P && goto :create_venv
)
echo [ERROR] Python not found. Install Python 3.10+ and add it to PATH.
pause & exit /b 1

REM -- 2. Create venv (first run only) ---------------------------------------
:create_venv
echo [SETUP] Creating virtual environment...
%PYTHON% -m venv .venv
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    pause & exit /b 1
)
set PYTHON=.venv\Scripts\python.exe
echo [SETUP] Virtual environment created.
echo.

REM -- 3. Check / install dependencies ---------------------------------------
:check_deps
REM Re-install if requirements.txt is newer than the sentinel stamp file
set STAMP=.venv\.deps_installed
set NEEDS_INSTALL=0

if not exist "%STAMP%" set NEEDS_INSTALL=1

if "%NEEDS_INSTALL%"=="0" (
    REM Compare timestamps: if requirements.txt is newer, reinstall
    for %%F in (requirements.txt) do set REQ_DATE=%%~tF
    for %%F in ("%STAMP%")       do set STP_DATE=%%~tF
    if "!REQ_DATE!" GTR "!STP_DATE!" set NEEDS_INSTALL=1
)

if "%NEEDS_INSTALL%"=="1" (
    echo [DEPS] Installing / updating dependencies...
    %PYTHON% -m pip install --upgrade pip setuptools wheel -q
    %PYTHON% -m pip install -r requirements.txt -q
    if errorlevel 1 (
        echo [ERROR] Dependency installation failed. Check the network connection.
        pause & exit /b 1
    )
    echo. > "%STAMP%"
    echo [DEPS] Dependencies up to date.
    echo.
) else (
    echo [DEPS] Dependencies already up to date.
    echo.
)

REM -- 4. Verify app.py exists -----------------------------------------------
if not exist "app.py" (
    echo [ERROR] app.py not found in %CD%
    pause & exit /b 1
)

REM -- 5. Run tests (optional - uncomment to enable) --------------------------
REM echo [TEST] Running regression tests...
REM %PYTHON% -m pytest tests\test_panchang.py tests\test_dasha.py -q --tb=short

REM -- 6. Launch Streamlit ----------------------------------------------------
echo [LAUNCH] Starting Streamlit on http://localhost:8501
echo          Press Ctrl+C in this window to stop the server.
echo.
%PYTHON% -m streamlit run app.py --server.headless false --browser.gatherUsageStats false

if errorlevel 1 (
    echo.
    echo [ERROR] Streamlit exited with an error. See output above.
    pause
)

endlocal
