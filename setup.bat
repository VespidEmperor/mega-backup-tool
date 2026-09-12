@echo off
setlocal
echo === mega-backup-tool setup ===

REM 1. Python present?
python --version >nul 2>nul
if errorlevel 1 (
  echo [ERROR] python not found on PATH. Install from https://python.org
  exit /b 1
)

REM 2. Install deps into the SAME python (python -m pip, not bare pip —
REM    bare pip can point at a different Python than "python").
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo [ERROR] pip install failed.
  exit /b 1
)

REM 3. megatools on PATH?
where megatools >nul 2>nul
if errorlevel 1 (
  echo.
  echo [WARNING] megatools not found on PATH.
  echo   Download the Windows build from https://xff.cz/megatools/builds/builds/
  echo   Unzip it, then add the folder containing megatools.exe to your PATH:
  echo     Start -^> "Edit the system environment variables" -^> Environment
  echo     Variables -^> Path -^> Edit -^> New -^> C:\path\to\megatools
  echo   Then REOPEN this terminal.
  echo.
) else (
  echo [OK] megatools found.
)

echo.
echo Setup complete. Run: python generate_accounts.py
endlocal
