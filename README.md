# School ERP — Starter Implementation

A runnable modular-monolith foundation for a School ERP web portal, built with:
- React + TypeScript + Vite frontend
- FastAPI backend
- PostgreSQL database
- JWT authentication and role-based permissions
- Docker Compose + Nginx deployment

This is a working foundation with implemented authentication, dashboard, student/staff/class/transport/hostel/document/maintenance CRUD APIs and a generic web admin UI. It is **not yet a fully production-complete implementation of all 20 ERP domains**. Payroll, payment gateway settlement, GPS tracking, biometric devices, OCR, and statutory accounting require institution-specific rules and integrations.

## Run with Docker

1. Install Docker Engine and Docker Compose plugin.
2. Copy `.env.example` to `.env` and change `JWT_SECRET_KEY` and database password.
3. Run:

```bash
docker compose up --build -d
```

4. Open:
   - Web portal: http://localhost
   - API docs: http://localhost:8000/docs

Default bootstrap admin:
- Email: `admin@example.com`
- Password: `ChangeMe123!`

Change these values in `.env` before exposing the app to a network. The bootstrap user is created only if the configured email does not exist.

## Run locally without Docker

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=sqlite:///./school_erp.db
export JWT_SECRET_KEY='replace-with-a-long-random-secret'
export BOOTSTRAP_ADMIN_EMAIL=admin@example.com
export BOOTSTRAP_ADMIN_PASSWORD='ChangeMe123!'
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Set `VITE_API_URL=http://localhost:8000` in `frontend/.env.local` if needed.

## Current implementation

- Login, JWT access tokens, password hashing
- Roles: super_admin, admin, accountant, teacher, transport_manager, hostel_warden, student, parent
- API permissions on module endpoints
- Dashboard counts
- CRUD endpoints for Students, Staff, Classes, Transport Vehicles, Hostels, Documents, Maintenance Requests
- Searchable module tables and create forms
- PostgreSQL in Docker; SQLite supported for local development
- Database tables auto-created on startup for easy development

## Before production

- Configure HTTPS, secure secret storage, restrictive CORS and network policy.
- Replace bootstrap credentials and set a long random JWT secret.
- Add automated tests, migrations (Alembic), rate limiting, MFA, audit-event retention, malware scanning, object storage, backup and restore drills.
- Review applicable child-data privacy, financial, employment, and school regulations.
- Implement the remaining domain workflows and integrations before representing this as a complete production ERP.
