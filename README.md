

cd /Users/sandesh/Developer/Python/event_billing_system/backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000

cd /Users/sandesh/Developer/Python/event_billing_system/frontend
npm run dev -- --host 0.0.0.0 --port 5173



# Event Billing System

Python/MySQL billing system for event managers and FX light suppliers.

Current focus:

- Frontend pages for bookings, linked wedding events, material master, payment entry, and invoice preview.
- FastAPI backend for clients, bookings, linked events, materials, and payments.
- Frontend loads live API data when the backend is running, with sample data as an offline fallback.

Planned stack:

- Frontend: React + Vite
- Backend: Python FastAPI
- Database: MySQL

## Frontend

```bash
cd /Users/sandesh/Developer/Python/event_billing_system/frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

Open:

```text
http://127.0.0.1:5173/
```

## Backend

Create a MySQL database/user, then copy the environment file:

```bash
cd backend
cp .env.example .env
```

Update `DATABASE_URL` in `.env` with your local MySQL username, password, host, and database name.

Install and run:

```bash
cd /Users/sandesh/Developer/Python/event_billing_system/backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

For a fresh setup, create the virtual environment and install dependencies once:

```bash
cd /Users/sandesh/Developer/Python/event_billing_system/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 seed.py
```

API health check:

```text
http://127.0.0.1:8000/api/health
```

## Desktop App Branch

Windows desktop setup lives on:

```bash
git switch branch_name_desktop_ready
```

See `DESKTOP_SETUP.md` for the Electron-based Windows setup. For the easiest
Windows bootstrap, install MySQL Server with root password `root`, then run:

```cmd
scripts\install-windows.bat
```

For manual PowerShell setup, install Git, Node.js LTS, Python 3.12+, and MySQL
Server, then run:

```powershell
.\scripts\setup-windows.ps1
.\scripts\run-windows-desktop.ps1
```

## Data Model

```text
Client
  Booking
    Booking Event
      Event Line Item
    Payment
```

One wedding booking can contain Sangeet, Haldi, Saptpadi, Reception, and any other linked events. The final bill is calculated from all linked event line items minus recorded payments.
