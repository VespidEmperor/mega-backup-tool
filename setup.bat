@echo off
setlocal EnableDelayedExpansion

echo === mega-backup-tool setup ===

REM 1. Python present?
where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python not found. Install from https://python.org
  exit /b 1
)

REM 2. Python deps (deps only - megatools is a binary, handled below)
echo [..] Installing Python deps...
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo [ERROR] pip install failed.
  exit /b 1
)

REM 2b. mega.py (server_copy.py dependency) --no-deps, because 1.0.8 pins a
REM tenacity<6 that is broken on Python 3.11+; we install modern tenacity above.
echo [..] Installing mega.py (server_copy.py dependency)...
python -m pip install --no-deps "mega.py==1.0.8"
if errorlevel 1 (
  echo [ERROR] mega.py install failed.
  exit /b 1
)

REM 3. megatools - standalone binary, not a pip package.
set "MTOOLS=%LOCALAPPDATA%\megatools"
set "MTOOLS_URL=https://xff.cz/megatools/builds/builds/megatools-1.11.5.20250706-win64.zip"

where megatools >nul 2>nul
if not errorlevel 1 (
  echo [OK] megatools already on PATH.
  goto :done
)

if not exist "%MTOOLS%\megatools.exe" (
  echo [..] Downloading megatools...
  if not exist "%MTOOLS%" mkdir "%MTOOLS%"
  curl.exe -sS -L -o "%MTOOLS%\megatools.zip" "%MTOOLS_URL%"
  if errorlevel 1 (
    echo [ERROR] megatools download failed. Get it manually:
    echo         %MTOOLS_URL%
    exit /b 1
  )
  echo [..] Extracting...
  powershell -NoProfile -Command "Expand-Archive -Path '%MTOOLS%\megatools.zip' -DestinationPath '%MTOOLS%' -Force"
  REM the zip extracts into a megatools-<version>-win64 subfolder; hoist the exe up
  for /r "%MTOOLS%" %%F in (megatools.exe) do copy /y "%%F" "%MTOOLS%\megatools.exe" >nul
)

if not exist "%MTOOLS%\megatools.exe" (
  echo [ERROR] megatools not found after extract. Get it from:
  echo         %MTOOLS_URL%
  exit /b 1
)

echo [..] Adding "%MTOOLS%" to your user PATH (persistent)...
powershell -NoProfile -Command "$p=[Environment]::GetEnvironmentVariable('Path','User'); if($p -notlike '*%MTOOLS%*'){ [Environment]::SetEnvironmentVariable('Path', $p.TrimEnd(';') + ';%MTOOLS%', 'User') }"

:done
echo.
echo Done. CLOSE this window and open a NEW one, then run:
echo   megatools --version
echo   python generate_accounts.py
endlocal
