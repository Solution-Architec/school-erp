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


## Demo accounts for role-wise testing

The demo seeder creates one login for every workspace role, including Developer and Parent, plus sample school records. It is **manual and opt-in**; it does not run during application startup.

Docker Compose:

```bash
docker compose exec -e ENABLE_DEMO_SEED=true backend python -m app.seed_demo
```

Local backend:

```bash
cd backend
ENABLE_DEMO_SEED=true python -m app.seed_demo
```

The command generates one temporary password and prints it once along with the login emails. All school-role accounts use school code `DEMO-SCHOOL`; Developer signs in with the school-code field left blank. The Parent demo is linked to the seeded demo student. Running the command again resets the demo accounts to a newly generated shared password.

Demo login emails:

- `demo.developer@example.test`
- `demo.principal@example.test`
- `demo.viceprincipal@example.test`
- `demo.teacher@example.test`
- `demo.accounts@example.test`
- `demo.clerk@example.test`
- `demo.officeassistant@example.test`
- `demo.librarian@example.test`
- `demo.labassistant@example.test`
- `demo.itadmin@example.test`
- `demo.transport@example.test`
- `demo.warden@example.test`
- `demo.security@example.test`
- `demo.others@example.test`
- `demo.parent@example.test`

The seeder refuses to run unless `ENABLE_DEMO_SEED=true`; it also refuses production environments unless `ALLOW_DEMO_SEED_IN_PRODUCTION=true` is explicitly set. Do not enable demo accounts on a public production deployment. Remove the demo users and sample records before using the school for real operations.

### Direct demo login (testing only)

For a local/staging role-visibility review, enable these flags in your local `.env`:

```env
ENABLE_DEMO_LOGIN=true
VITE_ENABLE_DEMO_MODE=true
```

Then rebuild/restart the stack:

```bash
docker compose up -d --build
```

The login page shows a **Demo workspace** role selector. Selecting a role fills its demo email and school code. Enter the shared password printed by the demo seeder. When `ENABLE_DEMO_LOGIN=true`, the exact seeded demo emails bypass email-verification and email-MFA challenges; normal accounts continue to use the regular verification/MFA flow. The backend flag defaults to `false` and is restricted to the known demo-account email list.

**Never enable either demo flag on a public or production deployment.** This testing shortcut intentionally weakens sign-in protections for demo accounts.

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
