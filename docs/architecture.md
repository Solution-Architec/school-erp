# Architecture and implementation notes

## Logical architecture

```mermaid
flowchart TB
  subgraph Clients
    SA[Super Admin / Developer Console]
    AD[School Admin / Staff Portal]
    PA[Parent / Student Portal]
  end
  subgraph Application
    WEB[React + TypeScript + Vite]
    API[FastAPI HTTP API]
    AUTH[JWT authentication + RBAC]
    MOD[School ERP modules]
  end
  subgraph Persistence
    PG[(PostgreSQL)]
  end
  SA --> WEB
  AD --> WEB
  PA --> WEB
  WEB -->|JSON / HTTPS| API
  API --> AUTH
  AUTH --> MOD
  MOD --> PG
```

The implementation is a **modular monolith**. The diagram's conceptual services (student, staff, finance, facilities, chatbot) are represented as API domains inside one FastAPI application. This is intentional for the current deployment size: it avoids service-discovery and distributed-transaction complexity while allowing later extraction.

## Tenancy model

- A school is represented by the `schools` table.
- School-owned records use `school_id` as their tenant discriminator.
- Super Admin is a global role and may manage schools across tenants.
- School users must be assigned to a school; endpoints apply tenant filters using the authenticated user's `school_id`.
- Creation APIs assign the caller's tenant ID rather than trusting client-supplied tenant IDs.
- Related-record validation must verify that both parent and child records belong to the same school.
- Legacy data migration assigns records without a school to a dedicated legacy school before making tenant IDs mandatory.

**Security invariant:** every read, update, delete, import, report, and relation lookup for school-level users must be scoped to their tenant. New endpoints must use the same rule and include cross-tenant negative tests.

## Module/API map

| Domain | Current API routes |
|---|---|
| Authentication | `/api/auth/login`, `/api/auth/me` |
| Dashboard | `/api/dashboard` |
| Schools / tenant onboarding | `/api/schools` |
| User administration | `/api/users` |
| Students | `/api/students`, `/api/students/import` |
| Staff | `/api/staff` |
| Classes | `/api/classes` |
| Transport | `/api/vehicles` |
| Hostel | `/api/hostels` |
| Documents | `/api/documents` |
| Facilities / maintenance | `/api/maintenance` |
| Finance | `/api/fee-structures`, `/api/student-fees`, `/api/fee-dues`, `/api/fee-reports` |
| Fee payments | `/api/student-fees/{fee_id}/payments` |

Most CRUD domains expose list, create, retrieve, update, and delete operations. See Swagger UI at `/docs` for the live OpenAPI contract.

## Deployment

Docker Compose runs the web frontend, FastAPI backend, and PostgreSQL database. Nginx serves the frontend and routes API requests. Keep PostgreSQL on a private Docker network; do not expose its port publicly in production.

Required production configuration:

- A unique long random `JWT_SECRET_KEY`
- A strong PostgreSQL password
- A non-default bootstrap admin email/password
- Exact trusted `CORS_ORIGINS`
- TLS termination at a trusted reverse proxy
- Encrypted backups and tested restore procedures
- Logs/metrics without passwords, tokens, student PII, or payment credentials

## Deliberate integration boundaries

These features require approved external services and are not enabled merely by adding a UI:

- Aadhaar identity verification
- Payment gateway authorization, capture, settlement, and reconciliation
- SMS/email/WhatsApp notifications
- AI chatbot provider and content safety controls
- Biometric attendance hardware
- GPS / vehicle tracking
- OCR and document scanning

Use provider adapters, server-side credentials, consent and compliance checks, idempotency, audit events, and integration tests when adding them.
