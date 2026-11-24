# EduNexus — All-in-One Education Management Platform

A modular-monolith, multi-tenant platform foundation for schools, colleges, universities, coaching centres, training institutes and other education providers. Existing school workflows remain supported while institution-type metadata enables institution-aware onboarding and future academic configuration.

## Technology stack

- **Frontend:** React + TypeScript + Vite
- **Backend:** Python + FastAPI
- **Database:** PostgreSQL (SQLite supported for local development)
  SQLite is intended for a fresh local-development database only. The automatic schema-upgrade path is PostgreSQL-specific; do not point an existing legacy SQLite database at a newer app version and assume it has been migrated. Use PostgreSQL for upgrades and production.
- **Authentication:** JWT access tokens + password hashing + role-based permissions
- **Deployment:** Docker Compose, Nginx, Linux
- **API documentation:** OpenAPI / Swagger UI

## Run with Docker

1. Install Docker Engine and Docker Compose plugin.
2. Copy the environment template and replace all demo secrets:

```bash
cp .env.example .env
```

3. Generate a unique JWT signing secret and put it in `.env` as `JWT_SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Also replace the database password and bootstrap administrator credentials with unique values before starting the stack.

4. Start the stack:

```bash
docker compose up --build -d
```

5. Open:
   - Web portal: http://localhost
   - API docs: http://localhost:8000/docs
   - API health: http://localhost:8000/api/health

**There is no default bootstrap administrator password.** Set `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD` to unique values in `.env` before first startup. Do not use example credentials in production.

## Local development

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=sqlite:///./school_erp.db
export JWT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export BOOTSTRAP_ADMIN_EMAIL=admin@example.com
export BOOTSTRAP_ADMIN_PASSWORD='set-a-unique-local-password'
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

The demo seeder creates school-workspace role accounts and a Parent account, plus sample school records. Platform Developer accounts are never seeded as client demos and must be provisioned separately for authorized platform owners. It is **manual and opt-in**; it does not run during application startup.

Docker Compose:

```bash
docker compose exec -e ENABLE_DEMO_SEED=true backend python -m app.seed_demo
```

Local backend:

```bash
cd backend
ENABLE_DEMO_SEED=true python -m app.seed_demo
```

The command generates one temporary password and prints it once along with the login emails. All seeded school-role accounts use school code `DEMO-SCHOOL`. The Parent demo is linked to the seeded demo student. Running the command again resets the demo accounts to a newly generated shared password.

Demo login emails:

- `demo.principal@jovoo.in`
- `demo.viceprincipal@jovoo.in`
- `demo.teacher@jovoo.in`
- `demo.accounts@jovoo.in`
- `demo.clerk@jovoo.in`
- `demo.officeassistant@jovoo.in`
- `demo.librarian@jovoo.in`
- `demo.labassistant@jovoo.in`
- `demo.itadmin@jovoo.in`
- `demo.transport@jovoo.in`
- `demo.warden@jovoo.in`
- `demo.security@jovoo.in`
- `demo.others@jovoo.in`
- `demo.parent@jovoo.in`

The seeder refuses to run unless `ENABLE_DEMO_SEED=true`; it also refuses production environments unless `ALLOW_DEMO_SEED_IN_PRODUCTION=true` is explicitly set. Do not enable demo accounts on a public production deployment. Remove the demo users and sample records before using the school for real operations.

### Direct demo login (testing only)

For a local/staging role-visibility review, enable these flags in your local `.env`:

```env
ENABLE_DEMO_LOGIN=true
VITE_ENABLE_DEMO_MODE=true
# Use the same strong, temporary value for both demo password settings:
DEMO_SEED_PASSWORD='set-a-local-demo-password-at-least-16-chars'
VITE_DEMO_PASSWORD='set-a-local-demo-password-at-least-16-chars'
```

Then rebuild/restart the stack:

```bash
docker compose up -d --build
```

The login page shows a **Practice with a demo role** selector for school workspace roles only. Platform Developer is intentionally excluded; authorized platform owners use their separately provisioned platform account. Selecting a demo role fills its demo email, school code, and (when `VITE_DEMO_PASSWORD` is configured) the shared demo password. Set `DEMO_SEED_PASSWORD` and `VITE_DEMO_PASSWORD` to the same strong temporary value so seeded accounts and the login page use matching credentials. If no fixed demo password is configured, the seeder generates one and prints it; enter that value manually. When `ENABLE_DEMO_LOGIN=true`, the exact seeded demo emails bypass email-verification and email-MFA challenges; normal accounts continue to use the regular verification/MFA flow. The backend flag defaults to `false` and is restricted to the known demo-account email list.

**Never enable either demo flag on a public or production deployment.** This testing shortcut intentionally weakens sign-in protections for demo accounts.

## Institution types

New institution registrations can identify as `school`, `college`, `university`, `coaching_centre`, `training_institute`, or `other`. Existing database rows default additively to `school`; existing records and tenant IDs are preserved. This release adds institution-aware onboarding and platform branding, while existing class/section-based academic workflows remain unchanged. Degree programmes, departments, semesters, credit systems and coaching batches require further domain-specific implementation before being advertised as fully supported.

## Institution types

New institution registrations can identify as `school`, `college`, `university`, `coaching_centre`, `training_institute`, or `other`. Existing database rows default additively to `school`; existing records and tenant IDs are preserved. This release adds institution-aware onboarding and platform branding, while existing class/section-based academic workflows remain unchanged. Degree programmes, departments, semesters, credit systems and coaching batches require further domain-specific implementation before being advertised as fully supported.

## Current implemented modules

- Login, JWT access tokens, password hashing, active-user checks
- Roles: `super_admin`, `admin`, `accountant`, `teacher`, `transport_manager`, `hostel_warden`, `student`, `parent`
- Tenant / school onboarding and school assignment
- Tenant-scoped dashboard statistics and API queries
- Students, staff, classes, library catalog and issue/return tracking, transport vehicles, hostels, documents, maintenance requests
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
- Review child-data privacy, financial, employment, and school regulations for the deployment jurisdiction.

## License

See repository license if present.


## Platform Owner / Developer Control Centre

The platform owner uses the existing private `super_admin` account for both platform administration and technical Developer responsibilities. This account is not part of the public demo-role selector.

The Developer Control Centre provides platform-wide institution summaries, client contact profiles, quotations, subscriptions, recorded collections, support tickets, and authenticated-user activity monitoring. Client-specific records are accessible through a signed, short-lived client-workspace token. Entering a client workspace presents the platform owner with tenant-admin permissions scoped to that single institution; platform-only routes remain unavailable until the owner exits back to the platform account. Workspace entry and exit are written to the audit log.

The activity indicator is based on authenticated application heartbeats (one per minute, considered online for five minutes). It records account and institution identifiers with a last-seen timestamp; it does not record keystrokes or page content.

Commercial collection records are manual records only. They do not initiate or verify bank, UPI, card, or payment-gateway transactions. Reconcile each entry against the actual payment provider or bank statement. Subscription dates and statuses are administrative records and do not automatically suspend client logins in this initial release.

All platform-control endpoints require the private platform-owner account, except the heartbeat endpoint and client-scoped support-ticket submission/listing. New platform tables are created by the application's SQLAlchemy metadata initialization. Back up the production database before deploying schema changes.

The System & Audit view currently checks API reachability and a simple database query and displays recorded audit events. It does not yet inspect host CPU/RAM/disk, backup completion, SSL/domain expiry, or third-party integration health; those require deployment-specific monitoring integrations.


## Automated PostgreSQL backups

Docker Compose includes a dedicated PostgreSQL backup service. It creates a compressed custom-format dump immediately after the database becomes healthy, then repeats every 24 hours by default. Before publishing a `.dump` file, the service checks the archive and restores it into a temporary verification database; a dump that fails this restore test is not published as the latest backup.

Backups are written to the host project's `./backups/` directory (excluded from Git) and mounted read-only into the API so the Developer Control Centre can report backup freshness and verification status. The default retention period is 30 days.

Optional `.env` settings:

```env
BACKUP_INTERVAL_SECONDS=86400
BACKUP_RETENTION_DAYS=30
BACKUP_MAX_AGE_HOURS=26
```

Start or update the service with:

```bash
docker compose up -d --build
docker compose ps
docker compose logs --tail=100 backup
ls -lh ./backups
```

A successful run logs that the dump passed a restore test. The infrastructure endpoint reports `healthy`, `stale`, `awaiting_first_backup`, or a configuration error and marks verified custom-format dumps as `restore_tested`.

**Recovery procedure:** stop application writes, choose the desired verified dump, create/prepare a separate recovery database, and restore with `pg_restore --exit-on-error --no-owner --no-acl -d <recovery_database> <backup_file>`. Validate the restored database before directing the application to it. Never test a recovery by restoring over the live production database.

The local backup directory is not an offsite backup. Production deployments must additionally copy encrypted backups to access-controlled offsite/object storage and periodically perform an independently witnessed recovery drill. Protect the host directory and do not commit backup files or share them publicly.
