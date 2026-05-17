@echo off
setlocal enabledelayedexpansion

REM One-click Windows setup for Prasad FX Billing.
REM This script can install Git, Node.js LTS, and Python with winget when missing.
REM MySQL Server must already be installed, running, and configured with root/root.

set "REPO_URL=https://github.com/sandeshghadge11/event_billing_system.git"
set "BRANCH_NAME=branch_name_desktop_ready"
set "APP_DIR=%USERPROFILE%\Desktop\event_billing_system"
set "MYSQL_ROOT_USER=root"
set "MYSQL_ROOT_PASSWORD=root"
set "MYSQL_DATABASE=event_billing"
set "DATABASE_URL=mysql+pymysql://root:root@localhost:3306/event_billing"
set "GIT_WINGET_ID=Git.Git"
set "NODE_WINGET_ID=OpenJS.NodeJS.LTS"
set "PYTHON_WINGET_ID=Python.Python.3.12"

echo.
echo ============================================================
echo  Prasad FX Billing - Windows Installer Bootstrap
echo ============================================================
echo.

call :AddCommonToolPaths

call :EnsureCommand git "Git for Windows" "%GIT_WINGET_ID%" "https://git-scm.com/download/win"
if errorlevel 1 exit /b 1

call :EnsureCommand node "Node.js LTS" "%NODE_WINGET_ID%" "https://nodejs.org"
if errorlevel 1 exit /b 1

call :EnsureCommand npm "npm" "%NODE_WINGET_ID%" "https://nodejs.org"
if errorlevel 1 exit /b 1

call :EnsurePython
if errorlevel 1 exit /b 1

call :FindMysql
if errorlevel 1 exit /b 1

if "%REPO_URL%"=="PASTE_YOUR_GITHUB_REPO_URL_HERE" (
  echo ERROR: Open this .bat file and set REPO_URL to your GitHub repository URL.
  pause
  exit /b 1
)

echo Creating or updating project folder...
if exist "%APP_DIR%\.git" (
  cd /d "%APP_DIR%"
  if errorlevel 1 (
    echo ERROR: Could not open %APP_DIR%.
    pause
    exit /b 1
  )
  git fetch origin
  if errorlevel 1 (
    echo ERROR: Could not fetch repository updates.
    pause
    exit /b 1
  )
  git switch "%BRANCH_NAME%" 2>nul
  if errorlevel 1 (
    git switch -c "%BRANCH_NAME%" --track "origin/%BRANCH_NAME%"
  )
  if errorlevel 1 (
    echo ERROR: Could not switch to branch %BRANCH_NAME%.
    pause
    exit /b 1
  )
  git pull --ff-only origin "%BRANCH_NAME%"
  if errorlevel 1 (
    echo ERROR: Could not update branch %BRANCH_NAME%.
    pause
    exit /b 1
  )
) else (
  if exist "%APP_DIR%" (
    echo ERROR: %APP_DIR% already exists but is not a git repository.
    echo Delete or rename that folder, then run this installer again.
    pause
    exit /b 1
  )
  git clone --branch "%BRANCH_NAME%" "%REPO_URL%" "%APP_DIR%"
  if errorlevel 1 (
    echo ERROR: Could not clone repository.
    pause
    exit /b 1
  )
  cd /d "%APP_DIR%"
  if errorlevel 1 (
    echo ERROR: Could not open %APP_DIR%.
    pause
    exit /b 1
  )
)

echo.
echo Creating MySQL database using root/root...
"%MYSQL_EXE%" -u%MYSQL_ROOT_USER% -p%MYSQL_ROOT_PASSWORD% -e "CREATE DATABASE IF NOT EXISTS %MYSQL_DATABASE% CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
if errorlevel 1 (
  echo ERROR: Could not create MySQL database. Confirm MySQL is running and root password is root.
  pause
  exit /b 1
)

echo.
echo Writing backend\.env...
(
  echo APP_NAME=Prasad FX Lights Billing API
  echo APP_ENV=development
  echo DATABASE_URL=%DATABASE_URL%
  echo FRONTEND_ORIGIN=http://127.0.0.1:5173
  echo SMTP_HOST=smtp.gmail.com
  echo SMTP_PORT=587
  echo SEND_MAIL=sandeshghadge301@gmail.com
  echo RECV_MAIL=sandeshghadge301@gmail.com
  echo SMTP_APP_PASSWORD=
) > "%APP_DIR%\backend\.env"

echo.
echo Installing Python backend dependencies...
cd /d "%APP_DIR%\backend"
if not exist ".venv" (
  %PYTHON_EXE% -m venv .venv
)
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
  echo ERROR: pip upgrade failed.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo ERROR: Backend dependency install failed.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" seed.py

echo.
echo Installing frontend dependencies...
cd /d "%APP_DIR%\frontend"
npm install
if errorlevel 1 (
  echo ERROR: Frontend npm install failed.
  pause
  exit /b 1
)

echo.
echo Installing Electron desktop dependencies...
cd /d "%APP_DIR%"
npm install
if errorlevel 1 (
  echo ERROR: Electron npm install failed.
  pause
  exit /b 1
)

echo.
echo Building Windows executable installer...
npm run desktop:dist:win
if errorlevel 1 (
  echo ERROR: Windows executable build failed.
  pause
  exit /b 1
)

echo.
echo ============================================================
echo  Done.
echo  Installer/executable output:
echo  %APP_DIR%\release
echo ============================================================
echo.
pause
exit /b 0

:AddCommonToolPaths
set "PATH=%ProgramFiles%\Git\cmd;%ProgramFiles%\nodejs;%ProgramFiles%\Python312;%LocalAppData%\Programs\Python\Python312;%LocalAppData%\Microsoft\WindowsApps;%PATH%"
exit /b 0

:EnsureCommand
set "TOOL_COMMAND=%~1"
set "TOOL_NAME=%~2"
set "TOOL_WINGET_ID=%~3"
set "TOOL_DOWNLOAD_URL=%~4"

where %TOOL_COMMAND% >nul 2>nul
if not errorlevel 1 (
  echo Found %TOOL_NAME%.
  exit /b 0
)

echo %TOOL_NAME% was not found. Trying to install it with winget...
where winget >nul 2>nul
if errorlevel 1 (
  echo ERROR: %TOOL_NAME% is not installed and winget is not available.
  echo Install it manually: %TOOL_DOWNLOAD_URL%
  pause
  exit /b 1
)

winget install --id "%TOOL_WINGET_ID%" -e --source winget --silent --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
  echo ERROR: winget could not install %TOOL_NAME%.
  echo Install it manually: %TOOL_DOWNLOAD_URL%
  pause
  exit /b 1
)

call :AddCommonToolPaths
where %TOOL_COMMAND% >nul 2>nul
if errorlevel 1 (
  echo ERROR: %TOOL_NAME% was installed, but this terminal cannot find %TOOL_COMMAND% yet.
  echo Close this window, open a new Command Prompt, and run this .bat file again.
  pause
  exit /b 1
)

echo Installed %TOOL_NAME%.
exit /b 0

:EnsurePython
set "PYTHON_EXE=python"
python --version >nul 2>nul
if not errorlevel 1 (
  echo Found Python.
  exit /b 0
)

where py >nul 2>nul
if not errorlevel 1 (
  py -3 --version >nul 2>nul
  if not errorlevel 1 (
    set "PYTHON_EXE=py -3"
    echo Found Python through the py launcher.
    exit /b 0
  )
)

call :EnsureCommand python "Python 3.12" "%PYTHON_WINGET_ID%" "https://www.python.org/downloads/windows/"
if errorlevel 1 exit /b 1

set "PYTHON_EXE=python"
python --version >nul 2>nul
if not errorlevel 1 (
  exit /b 0
)

echo ERROR: Python was installed, but python.exe still cannot run in this terminal.
echo Close this window, open a new Command Prompt, and run this .bat file again.
pause
exit /b 1

:FindMysql
set "MYSQL_EXE="
where mysql >nul 2>nul
if not errorlevel 1 (
  set "MYSQL_EXE=mysql"
  echo Found MySQL client.
  exit /b 0
)

if exist "%ProgramFiles%\MySQL\MySQL Server 8.4\bin\mysql.exe" set "MYSQL_EXE=%ProgramFiles%\MySQL\MySQL Server 8.4\bin\mysql.exe"
if not defined MYSQL_EXE if exist "%ProgramFiles%\MySQL\MySQL Server 8.0\bin\mysql.exe" set "MYSQL_EXE=%ProgramFiles%\MySQL\MySQL Server 8.0\bin\mysql.exe"
if not defined MYSQL_EXE if exist "%ProgramFiles(x86)%\MySQL\MySQL Server 8.0\bin\mysql.exe" set "MYSQL_EXE=%ProgramFiles(x86)%\MySQL\MySQL Server 8.0\bin\mysql.exe"

if defined MYSQL_EXE (
  echo Found MySQL client at %MYSQL_EXE%.
  exit /b 0
)

echo ERROR: MySQL client is not installed or not in PATH.
echo Install MySQL Server, set the root password to root, and make sure MySQL is running.
echo Download: https://dev.mysql.com/downloads/installer/
pause
exit /b 1
