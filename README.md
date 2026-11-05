# SchoolOS — Multi-Tenant School Management Platform

A modular-monolith School ERP built around the architecture in the project diagram.

## Technology stack

- **Frontend:** React + TypeScript + Vite
- **Backend:** Python + FastAPI
- **Database:** PostgreSQL (SQLite supported for local development)
- **Authentication:** JWT access tokens + password hashing + role-based permissions
- **Deployment:** Docker Compose, Nginx, Linux
- **API documentation:** OpenAPI / Swagger UI

## Run with Docker

1. Install Docker Engine and Docker Compose plugin.
2. Copy the environment template and replace all demo secrets:

```bash
cp .env.example .env
```

3. Start the stack:

```bash
docker compose up --build -d
```

4. Open:
   - Web portal: http://localhost
   - API docs: http://localhost:8000/docs
   - API health: http://localhost:8000/api/health

Default bootstrap administrator:
- Email: `admin@example.com`
- Password: `ChangeMe123!`

**Do not use the bootstrap credentials in production.** Change the password, JWT secret, database password, and CORS origins before exposing the application.

## Local development

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

Set `VITE_API_URL=http://localhost:8000` in `frontend/.env.local` when running the API separately.

## Current implemented modules

- Login, JWT access tokens, password hashing, active-user checks
- Roles: `super_admin`, `admin`, `accountant`, `teacher`, `transport_manager`, `hostel_warden`, `student`, `parent`
- Tenant / school onboarding and school assignment
- Tenant-scoped dashboard statistics and API queries
- Students, staff, classes, transport vehicles, hostels, documents, maintenance requests
- Fee structures, student fees, payment recording, fee dues and fee reports
- Parent Portal with explicit parent-to-student association and tenant-scoped fee balances
- Approved FAQ chatbot endpoint and Help Assistant UI
- Student CSV / XLSX import
- Searchable admin tables and create forms
- PostgreSQL deployment and SQLite local development

See [Architecture and implementation notes](docs/architecture.md) for component boundaries, tenant isolation, API domains, and deployment notes.

## Architecture

The app is a **modular monolith**, not a distributed microservice deployment. The React web client communicates with FastAPI over HTTP/JSON. FastAPI owns authentication, authorization, tenant scoping, validation, and persistence. PostgreSQL stores tenant data with a `school_id` discriminator. Nginx serves the frontend and proxies API traffic in Docker deployments.

This approach keeps deployment and operations simple while retaining clear module boundaries for future extraction.

## Before production

This repository is a functional ERP foundation; it should not be represented as a fully production-ready school platform yet.

- Add and run automated unit, integration, authorization, and tenant-isolation tests.
- Replace startup schema creation and ad-hoc schema adjustments with Alembic migrations.
- Configure HTTPS, strict CORS, secret management, rate limiting, MFA, and session/token revocation.
- Add audit logs, backup/restore drills, monitoring, alerting, and security review.
- Complete parent/student self-service flows and record-level access controls.
- Add payment-provider integration and reconciliation before accepting real payments.
- Integrate external Aadhaar verification only through an authorized provider and approved compliance workflow; never store Aadhaar numbers unless legally required and secured.
- Implement attendance, examinations, timetable, payroll, biometric, GPS, OCR, and statutory accounting workflows as institution-specific modules.
- Review child-data privacy, financial, employment, and school regulations for the deployment jurisdiction.

## License

See repository license if present.
