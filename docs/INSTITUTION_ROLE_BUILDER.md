# Institution Custom Role Builder

## Overview

Adds a school/institution-admin workspace for creating custom roles from published Developer-managed templates and assigning multiple custom roles to staff accounts.

## API

All routes are under `/api/institution/rbac` and require the authenticated `admin` role. Tenant identity is taken from the authenticated account's `school_id`; callers cannot select or override another institution.

- `GET /context` — institution name and institution type.
- `GET /templates` — active Developer templates with published versions applicable to this institution type.
- `GET /roles` — local custom roles, source template/version, permission grants and active assignment counts.
- `POST /roles` — create a local role from a published template version.
- `GET /users` — active same-institution staff accounts eligible for custom role assignment; parent and platform accounts are excluded.
- `GET /assignments` — same-institution assignments; supports `user_id`, `role_id` and `include_inactive` filters.
- `POST /assignments` — assign a custom role to a staff account, with optional validity dates.
- `PATCH /assignments/{id}` — activate or revoke an assignment.

## Permission governance

- The institution can select only Developer-published template versions applicable to its institution type.
- Every submitted module/action/scope is revalidated by the existing domain service against the source version's exact permission ceiling.
- Institutions can grant a subset of the approved permissions; they cannot add modules, actions or broader scopes.
- The source template version is retained on the institution role for traceability.
- Multiple active custom roles can be assigned to one staff user. Existing `User.role` is not changed.
- The multi-role resolver's explicit-deny-wins and union-of-allows behavior remains unchanged.

## Tenant and audit controls

- The API derives the tenant from the authenticated administrator and never accepts a client-supplied school ID.
- Role and assignment reads are scoped to that tenant; cross-tenant user/role IDs are rejected by the service layer.
- Parent and platform identities cannot receive institution custom-role assignments.
- Role creation, assignment, reactivation and revocation use the existing audited domain services.
- Platform workspace impersonation does not expose this institution-admin workspace.

## UI

The School Admin sidebar includes **Custom Roles & Assignments**. The workspace provides role cards, approved-template permission selection, staff assignment management, validity dates, revoked-assignment review and confirmation before revocation/reactivation.
