# Frontend Navigation and Action Permissions

## Effective permission contract

The authenticated frontend loads `GET /api/rbac/me` after sign-in and workspace-token changes. For institution users, the response's `permissions` map contains effective `module:Action` decisions calculated with the same server-side resolver used by route guards.

The endpoint includes active multi-role assignments, explicit-deny precedence, and legacy permission/default fallback. Developer remains platform-wide. The signed Developer client-workspace wrapper retains its scoped legacy workspace behavior.

## UI behavior

- Sidebar entries are shown only when the effective `module:View` decision is allowed.
- Create, edit, delete, approve, and import controls are hidden unless their corresponding effective action is allowed. Bulk import uses the module's Create permission because the existing import APIs are guarded by Create.
- Permission data is refreshed when the authenticated token changes, including entering or leaving a client workspace.
- If the permission endpoint fails, the UI fails closed for institution module/action capabilities instead of silently reverting to hard-coded role access.
- Existing parent-family navigation, Developer tools, and institution role-builder workspace boundaries are preserved.

Frontend visibility is only a usability layer. Every API request remains independently authorized by backend dependencies and tenant/relationship checks.

## Validation

Run the normal CI backend tests, frontend production build, and PostgreSQL backup create/restore verification. Add regression coverage for permission payload decisions and action visibility as the frontend test harness is expanded.
