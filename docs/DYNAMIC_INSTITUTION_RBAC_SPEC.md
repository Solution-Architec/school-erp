# EduNexus Dynamic Institution RBAC — Architecture and Delivery Specification

**Status:** Proposed architecture / implementation baseline  
**Repository:** `Solution-Architec/school-erp`  
**Base:** `main`  
**Scope:** Entire application; schools, colleges, universities, training institutes and other education institutions.

## 1. Executive decision

Implement a dynamic, multi-tenant, developer-governed RBAC system.

- Developer owns the canonical module/action catalogue, institution-type catalogue, platform-protected permissions, and published role-template versions.
- Institution administrators may create local custom roles and assign users, but only within the active institution's entitlements and Developer-approved permission ceilings.
- A published template update creates a new version. Existing institutions remain on their adopted version until an authorized institution administrator reviews and adopts the new version.
- A user may hold multiple roles in one institution. Effective permissions are calculated server-side from all active assignments.
- Existing fixed roles and `role_permissions` remain supported during migration. No destructive reset, user recreation, or removal of existing ERP functionality is permitted.

PR #105 is now merged into `main`; it is the current RBAC baseline, not the completion of dynamic role management. It introduced the position-based default matrix, additional module registration, and module permission enforcement for selected workflows. The current implementation still has a single `users.role` field and a `RolePermission(role, module_key, action, enabled, school_id)` grant model. This specification evolves that foundation rather than replacing it abruptly.

## 2. Product hierarchy and trust boundaries

1. **Platform Developer** — manages global catalogues, role templates, template versions, platform-only capabilities and institution-type applicability.
2. **Super Admin / Platform Operations** — manages institution lifecycle and platform operations. It does not implicitly receive Developer's template-authoring capability unless explicitly granted at platform level.
3. **Institution Admin** — manages institution-local roles, role assignments and template adoption, bounded by the institution's plan, type, and Developer policy.
4. **Institution users** — receive access through one or more active institution role assignments.
5. **Parent / Student** — retain relationship- and ownership-based data boundaries in addition to role permissions.

Platform identities and platform-only modules must never be grantable by tenant role templates or institution role builders. A school administrator cannot promote a tenant user to Developer or Super Admin.

## 3. Institution types

Canonical initial types:
- `school`
- `college`
- `university`
- `training_institute`
- `other`

Use stable machine keys and display labels. Adding a type must not require hard-coded role additions across the application. The institution type is an applicability and template-discovery attribute; it is not itself an authorization grant.

## 4. Permission model

### 4.1 Module catalogue

The Developer-managed module registry is the canonical source for all ERP workspaces and protected backend resources. It must cover every existing module, including Dashboard, Students, Staff, Admissions, Classes, Attendance, Timetable, Homework, Examinations, Results, Fees, Payments, Finance Reports, Library, Transport, Hostel, Documents, Maintenance, Parent Portal, Parent Relationships, Notifications, Certificates, Facility Requests, Approvals, Chatbot, Schools, and Developer Control.

Each module record has:
- immutable `module_key`
- display name and description
- supported institution types (or all)
- status (active/deprecated)
- platform-only flag
- optional dependency metadata

A module cannot be deleted while referenced by templates, roles, grants, audit records, or routes. Deprecate it and retain historical references.

### 4.2 Actions

Use a central action catalogue. Initial generic actions:
`View`, `Create`, `Edit`, `Delete`, `Approve`, `Reject`, `Publish`, `Assign`, `Import`, `Export`, `Print`, `Download`, `Manage`.

Modules may expose only relevant actions. Existing API action strings must be mapped consistently; do not silently rename a live action without compatibility mapping and tests.

### 4.3 Grants and explicit denials

Represent a permission decision as `allow`, `deny`, or `inherit` for a module/action pair. A boolean-only grant table cannot represent the required inheritance and explicit-deny semantics; migrate through a compatibility layer.

Resolution rules, in order:
1. Hard platform/security restrictions and tenant boundaries always win.
2. Explicit deny from any active assigned role wins over role-derived allows for the same module/action.
3. Otherwise, an allow from any active assigned role grants that module/action.
4. If no role decides, use the adopted template/institution role inheritance and then the legacy compatibility profile.
5. If still undecided, deny (fail closed).

Developer-defined permission ceilings and institution subscription entitlements are not ordinary grants and cannot be overridden by a tenant role. No permission may escape the current user's institution context.

### 4.4 Multiple role assignments

A user can have multiple active roles within their institution. Effective module/action grants are combined using the rules above. Each assignment is scoped to exactly one institution and can have optional validity dates and assignment metadata.

Do not put authoritative role lists or permission matrices in long-lived JWT claims. Resolve current active assignments and permission versions from the database on each request (a short-lived, safely invalidated cache may be considered only after correctness tests exist). Revocation must take effect without requiring the user to retain an old token.

### 4.5 Data scopes

Module/action permission is necessary but insufficient. Support explicit scopes:
- `own`
- `assigned`
- `class_section`
- `department`
- `institution`
- `selected_records`
- relationship-constrained (parent/student)

Scope assignments carry resource type and resource identifiers where required. The API must apply scope predicates in database queries, not filter already-returned data in the frontend. Cross-institution access is always denied. For multiple roles, the user receives the union of the explicitly assigned, institution-bounded resource sets for a granted action; explicit denies and hard boundaries still win. Parent access remains constrained by active ParentStudentLink records; student access remains constrained to the authenticated student's own record.

## 5. Developer role-template lifecycle

Template lifecycle:
1. Developer creates a draft template with a name, description, institution-type applicability and optional category.
2. Developer selects modules and supported actions, permission ceilings, default data scopes and approval constraints.
3. Validate that platform-only modules/actions are not exposed to tenant templates.
4. Developer publishes an immutable version (v1, v2, ...).
5. Institutions can discover applicable published templates.
6. Institution administrator adopts a specific version.
7. A later Developer publication does not silently mutate existing institutions. Show version differences and allow an authorized admin to adopt the new version.
8. Adoption must preserve local customizations only when they remain within the new template ceiling; incompatible permissions are highlighted and disabled/revoked with an auditable adoption transaction.
9. Retired templates remain readable for existing assignments and audit history; they cannot be newly adopted.

A template version is immutable after publication. Corrections require a new version.

## 6. Institution custom-role lifecycle

Institution Admin can:
- create a local role from an adopted template;
- name and describe it;
- choose only modules/actions/scopes allowed by the template and institution entitlement;
- reduce access or leave permissions disabled;
- assign the role to institution users;
- edit, deactivate, duplicate and audit local roles;
- view users and permissions affected by a role change.

Institution Admin cannot:
- add a module/action outside the active template ceiling;
- enable platform-only permissions;
- change another institution's roles;
- grant Developer/Super Admin or platform operations permissions;
- bypass protected parent/student relationship rules;
- assign roles to users outside the same institution.

A local custom role records its source template and adopted version. A role may be marked as locally customized; template adoption must present a diff before changing its inherited baseline.

## 7. Proposed persistence model

Use additive migrations and retain legacy columns/tables during the transition.

| Table | Key responsibility |
|---|---|
| `rbac_modules` | Canonical module registry |
| `rbac_actions` | Canonical action registry |
| `rbac_module_actions` | Valid module/action combinations |
| `rbac_role_templates` | Developer-owned template identity and applicability |
| `rbac_role_template_versions` | Immutable published version metadata |
| `rbac_template_permissions` | Versioned allow/deny ceilings, defaults and scopes |
| `institution_roles` | Institution-local role identity, status and source template version |
| `institution_role_permissions` | Local allow/deny/inherit choices within template ceiling |
| `user_role_assignments` | Multiple user-to-role assignments, institution scope and validity |
| `rbac_role_scopes` | Resource-level scope grants and selected resource IDs |
| `rbac_template_adoptions` | Institution's adopted template version and adoption history |
| `rbac_audit_events` | Role, assignment, template publication/adoption and permission change audit |

Exact names may be adjusted after inspecting existing naming conventions. Keep `role_permissions` as a compatibility source while old fixed-role paths remain active. Add indexes and uniqueness constraints for tenant scope, active assignments, version numbers and module/action keys.

## 8. Legacy compatibility and migration

Current baseline facts:
- `User` has `role`, `position` and `school_id`.
- `RolePermission` stores role/module/action boolean values with global and school-specific scopes.
- `RBAC_ROLES`, `DEFAULT_ROLE_MODULES` and `_default_permission_matrix` define legacy role profiles in `backend/app/main.py`.
- `require_module_permission` resolves school/global `RolePermission`, then the default matrix and route fallbacks in `backend/app/security.py`.
- Frontend navigation and Developer permission editing are currently driven by role catalogues and module arrays in `frontend/src/App.tsx`.

Migration strategy:
1. Seed canonical modules/actions from current `RBAC_MODULES` and route action usage.
2. Create compatibility role templates for every existing `RBAC_ROLES` key, preserving the current default matrix.
3. Create a default institution role/assignment corresponding to each existing non-platform `users.role` value without changing the user's login identity.
4. Translate existing global/school `RolePermission` rows into compatibility decisions with their current precedence.
5. Run shadow evaluation: calculate old and new effective decisions and log differences without changing authorization.
6. Resolve discrepancies and obtain regression test coverage.
7. Enable new resolver behind a controlled feature flag, initially for test tenants, then roll out in stages.
8. Keep legacy fallback until all protected routes and users are migrated and verified. Remove legacy paths only in a separate approved cleanup PR.

Never reset or truncate user, school, student, parent-link, fee, attendance, certificate, notification, backup or audit data.

## 9. API specification

Suggested API surface (final paths should follow existing router conventions):

### Developer / platform-only
- `GET/POST /api/platform/rbac/modules`
- `PATCH /api/platform/rbac/modules/{module_key}`
- `GET/POST /api/platform/rbac/actions`
- `GET/POST /api/platform/rbac/templates`
- `GET/PATCH /api/platform/rbac/templates/{template_id}`
- `POST /api/platform/rbac/templates/{template_id}/publish`
- `GET /api/platform/rbac/templates/{template_id}/versions`
- `GET /api/platform/rbac/template-versions/{version_id}/diff`

### Institution admin
- `GET /api/rbac/templates?institution_type=...`
- `GET/POST /api/rbac/template-adoptions`
- `POST /api/rbac/template-adoptions/{adoption_id}/adopt`
- `GET/POST /api/rbac/roles`
- `GET/PATCH /api/rbac/roles/{role_id}`
- `POST /api/rbac/roles/{role_id}/deactivate`
- `GET/PUT /api/rbac/roles/{role_id}/permissions`
- `GET/POST /api/rbac/role-assignments`
- `PATCH /api/rbac/role-assignments/{assignment_id}`
- `GET /api/rbac/users/{user_id}/effective-permissions`

All platform routes require a real platform identity and must reject a platform-owner client-workspace impersonation token. All institution routes derive school_id from the authenticated principal; tenant-provided school IDs are never trusted for ordinary school admins.

## 10. Frontend workspaces

### Developer Control Centre
- Module/action catalogue manager.
- Institution-type manager.
- Role-template designer with searchable module tree and per-action controls.
- Data-scope and approval-limit editor.
- Draft / published / retired lifecycle.
- Version history, version diff and adoption analytics.
- Preview of effective role permissions for School, College, University and Training Institute.

### Institution Admin
- Template catalogue and current adopted version.
- Template update notification and diff/accept workflow.
- Custom role builder bounded by template ceiling.
- User role assignment manager with multiple role chips and effective permission preview.
- Role impact preview before changing or deactivating a role.
- Audit history.

### All application users
- Sidebar, dashboard cards, routes and action buttons reflect effective permissions from `/api/rbac/me`.
- Frontend hiding is usability only. Every API request remains independently authorized.
- Avoid a second source of truth in frontend hard-coded role checks; use capability data from the backend, retaining only non-security presentation rules.

## 11. Entire-application enforcement inventory

Create and maintain a route-to-permission inventory. Every endpoint must be classified:
- public/authentication;
- platform-only;
- institution administration;
- module action;
- self-service;
- parent relationship constrained;
- student self constrained;
- file/document access;
- background worker/system actor.

For every module, specify View/Create/Edit/Delete/Approve/Reject/Publish/Assign/Import/Export/Print/Download/Manage as applicable. Review generic CRUD endpoints, specialized routers (`platform_control`, `platform_operations`, `parent_services`, `notifications`), certificate issuance/download, file endpoints, reports, exports, imports and worker-triggered operations. Do not assume a route is covered because its frontend module is hidden.

## 12. Audit, reliability and security

Audit:
- template draft changes and publication;
- template version adoption and rejected adoption;
- local role creation, edits, deactivation;
- role assignment/revocation/expiry;
- permission and scope changes;
- authorization denials for sensitive actions (rate-limited / sampled to avoid log flooding);
- role changes that affect existing users.

Security:
- deny by default;
- explicit deny overrides allows;
- platform-only permissions are not tenant grantable;
- tenant scope comes from authenticated identity;
- parent link and student ownership checks remain mandatory;
- protect role-management endpoints against self-escalation and last-admin lockout;
- prevent assignment cycles and privilege inheritance through role names;
- validate every referenced module/action against the canonical registry;
- use transactional writes for role/template adoption;
- no secrets or sensitive personal identifiers in audit payloads.

Reliability:
- permission resolver is deterministic and unit-testable;
- avoid authorization cache until invalidation/revocation is proven;
- template adoption and role assignment changes are atomic;
- migrations are additive, restart-safe and idempotent;
- preserve all existing APIs and UI flows unless a compatibility change is separately approved.

## 13. Test and acceptance criteria

### Unit and model tests
- template draft/publish/version immutability;
- institution type applicability;
- module/action validation;
- permission ceiling enforcement;
- allow/deny/inherit resolution across multiple roles;
- scope union and tenant-boundary enforcement;
- role assignment activation, expiry, revocation and duplicate prevention;
- compatibility mapping against legacy matrix and grants.

### API authorization matrix
For each endpoint: allowed role, denied role, missing grant, explicit deny, cross-school ID, inactive user, expired assignment, workspace impersonation, parent unlinked/inactive relationship, student-other-user access.

### Regression
- existing login, MFA/OTP, password reset and school workspace;
- existing dashboard and all ERP modules;
- parent family workspace, notifications, preferences, reminders and certificates;
- fees/payments/receipts, attendance, homework, timetable, examinations/results;
- transport/hostel workflows, library, documents and reports;
- backup/restore workflow.

### Release acceptance
- No protected API is accessible solely because a frontend control is hidden.
- No user can access another institution's data.
- Role revocation takes effect on the next API request.
- Existing accounts retain equivalent effective permissions until explicitly changed.
- Institution custom roles cannot exceed the adopted Developer template or subscription entitlement.
- Template updates do not alter an institution until the institution adopts the new version.
- All sensitive changes are auditable.
- Backend tests, frontend build and backup CI all pass.

## 14. GitHub PR delivery plan

Deliver in small, sequential PRs. Each branch must start with `sde/`, target the latest `main`, and be merged before dependent work begins.

| Proposed PR | Scope | Main deliverables |
|---|---|---|
| RBAC-1 — Architecture baseline | Documentation only | This specification, route inventory template, acceptance checklist |
| RBAC-2 — Canonical catalog | Backend + tests | Module/action/institution-type registry, safe seed and validation |
| RBAC-3 — Template persistence | Backend + migration + tests | Template identities, immutable versions, template permission ceilings |
| RBAC-4 — Institution roles | Backend + migration + tests | Institution roles, local permissions, multiple role assignments |
| RBAC-5 — Permission resolver | Backend + tests | Allow/deny/inherit semantics, multiple-role resolution, legacy shadow comparison |
| RBAC-6 — Developer template APIs | Backend + tests | Draft, edit, publish, retire, version diff and platform-only guards |
| RBAC-7 — Institution role APIs | Backend + tests | Template discovery/adoption, custom roles, role assignments and effective preview |
| RBAC-8 — Developer Control Centre UI | Frontend | Catalogue and role-template designer, version lifecycle |
| RBAC-9 — Institution Admin UI | Frontend | Template adoption, custom role builder, multiple-role assignment and impact preview |
| RBAC-10 — Core ERP enforcement | Backend + tests | Generic CRUD, student/staff/classes/attendance/academics/fees/exams/library |
| RBAC-11 — Services enforcement | Backend + tests | Parent, notifications, certificates, transport, hostel, documents, reports and files |
| RBAC-12 — Frontend capability integration | Frontend + tests | Navigation, dashboards, routes and action-level capability controls |
| RBAC-13 — Data scopes and hardening | Backend + tests | Class/section/department/assigned/own/selected-record scopes, cross-tenant denial |
| RBAC-14 — Migration and rollout | Backend + docs + CI | Shadow-mode comparison, feature flag rollout, audit and rollback runbook |

PR-1 is documentation-only and should be merged first. Avoid one enormous PR that edits every API and frontend module simultaneously. Do not merge dependent PRs until CI and authorization regression tests pass.

## 15. Recommended implementation order and immediate next action

1. Merge this specification PR.
2. Build the canonical registry and schema migrations without changing live authorization.
3. Build templates and institution roles/assignments.
4. Implement and test the new resolver in shadow mode against the PR #105 behavior.
5. Add Developer and Institution Admin workflows.
6. Integrate backend route enforcement module-by-module.
7. Integrate frontend capabilities.
8. Roll out gradually after parity and security acceptance tests.

**Out of scope for the first delivery:** rewriting authentication, changing parent identity verification, replacing subscription billing, changing institution onboarding, or redesigning ERP modules. These systems should integrate with RBAC, not be rewritten as part of it.
