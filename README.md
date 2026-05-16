# Event Billing System

Python/MySQL billing system for event managers and FX light suppliers.

Current focus:

- Frontend pages for bookings, linked wedding events, material master, and invoice preview.
- FastAPI backend scaffold for clients, bookings, linked events, materials, and payments.
- Frontend still uses mock data while the user flow is being finalized.

Planned stack:

- Frontend: React + Vite
- Backend: Python FastAPI
- Database: MySQL

## Frontend

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1
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
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Load starter materials and the sample Waghmare wedding:

```bash
python seed.py
```

API health check:

```text
http://127.0.0.1:8000/api/health
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
