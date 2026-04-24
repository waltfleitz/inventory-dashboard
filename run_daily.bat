@echo off
cls

echo ============================================================
echo  SNAPSHOT INVENTORY ENGINE - DAILY RUN
echo ============================================================
echo.

REM ---------------- CONFIG ----------------
set SCRIPT_DIR=C:\Users\walt\SCRAPER\Inventory Scraper
set PYTHON_CMD=py -3.12
set LOG_FILE=%SCRIPT_DIR%\run_log.txt

REM ---------------- CHANGE DIRECTORY ----------------
cd /d "%SCRIPT_DIR%"

echo Running from:
echo %SCRIPT_DIR%
echo.

REM ---------------- START LOG ----------------
echo ============================================================ >> "%LOG_FILE%"
echo RUN START: %DATE% %TIME% >> "%LOG_FILE%"
echo ============================================================ >> "%LOG_FILE%"

REM ---------------- RUN SCRAPER ----------------
echo ============================================================
echo Step 1: Inventory Scraper (API Engine)
echo ============================================================
echo.

%PYTHON_CMD% inventory_scraper.py >> "%LOG_FILE%" 2>&1

IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Scraper failed. Check run_log.txt
    echo ERROR at %DATE% %TIME% >> "%LOG_FILE%"
    pause
    exit /b
)

echo.
echo [OK] Scraper completed
echo.

REM ---------------- RUN ANALYSIS ----------------
echo ============================================================
echo Step 2: Inventory Analysis
echo ============================================================
echo.

%PYTHON_CMD% analyze_inventory.py >> "%LOG_FILE%" 2>&1

IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Analysis failed. Check run_log.txt
    echo ERROR at %DATE% %TIME% >> "%LOG_FILE%"
    pause
    exit /b
)

echo.
echo [OK] Analysis completed
echo.

REM ---------------- COMPLETE ----------------
echo ============================================================
echo RUN COMPLETE
echo ============================================================
echo.

echo Output files:
echo - inventory_history.csv
echo - model_trim_breakdown.csv
echo - HOT_OPPORTUNITIES.csv
echo.

echo RUN END: %DATE% %TIME% >> "%LOG_FILE%"
echo ============================================================ >> "%LOG_FILE%"

REM ---------------- AUTO OPEN HOT FILE (OPTIONAL) ----------------
REM Uncomment this line if you want it to auto-open after run
REM start "" "%SCRIPT_DIR%\HOT_OPPORTUNITIES.csv"

pause