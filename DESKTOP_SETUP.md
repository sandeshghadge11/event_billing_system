# Desktop Setup

This branch adds an Electron desktop shell around the existing React frontend
and FastAPI backend. The desktop app starts the backend automatically, then opens
the built frontend in a native desktop window.

## What This Solves

- You no longer need to manually run separate frontend and backend terminals.
- The React UI runs as a desktop window.
- The local FastAPI backend still uses the same MySQL database, so data remains
  shared with other devices on the same network when they point to this machine.

## Windows Prerequisites

For the friendliest setup, run:

```cmd
scripts\install-windows.bat
```

The batch installer uses `winget` to install Git, Node.js LTS, and Python when
they are missing, then downloads the project, installs dependencies, and builds
the Windows installer.

MySQL Server still needs to be installed separately before running the batch
file, because the app expects a running local server with the root password set
to `root`.

Manual setup requires these on the Windows machine:

- Git
- Node.js LTS
- Python 3.12 or newer
- MySQL Server
- Visual C++ Redistributable is commonly useful for Python/MySQL packages

Then create the MySQL database/user and configure `backend/.env` with the correct
`DATABASE_URL`.

Example:

```env
DATABASE_URL=mysql+pymysql://billing_user:billing_password@localhost:3306/event_billing
FRONTEND_ORIGIN=http://127.0.0.1:5173
```

## First-Time Setup On Windows

```powershell
git clone <your-repo-url>
cd event_billing_system
git switch branch_name_desktop_ready
.\scripts\setup-windows.ps1
```

The setup script creates `backend\.env` if missing, installs backend Python
packages into `backend\.venv`, installs frontend dependencies, and installs the
Electron desktop dependencies.

After setup, edit `backend\.env` and make sure `DATABASE_URL` matches the local
Windows MySQL database.

If PowerShell blocks the script, run this once in the same terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Manual setup commands are:

```powershell
git clone <your-repo-url>
cd event_billing_system
git switch branch_name_desktop_ready

cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python seed.py

cd ..\frontend
npm install

cd ..
npm install
```

## Run As Desktop App

From the repository root:

```powershell
.\scripts\run-windows-desktop.ps1
```

This command builds the React app, starts the FastAPI backend automatically, and
opens the Electron desktop window.

## Build A Windows Installer

From the repository root on Windows:

```powershell
.\scripts\build-windows-installer.ps1
```

The installer output goes to `release/`.

Important: this Electron packaging step includes the app code, but it does not
freeze Python or bundle MySQL. For a truly one-click installer on a fresh Windows
machine, the backend should also be packaged with PyInstaller, or the database
should be moved to an embedded database such as SQLite.

## GitHub Updates

Running code directly from GitHub every time is possible, but it is not the best
desktop-app pattern because it requires Git, Node, Python, dependency installs,
and migrations on the user machine.

Better options:

- Use GitHub for source control and manually pull updates on the Windows machine
  while the project is still in development.
- Later, publish versioned desktop installers from GitHub Releases.
- Add Electron auto-update after installers are being published. That gives the
  user updated app builds without exposing the raw source workflow.
