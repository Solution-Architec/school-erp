# Multi-Role Permission Resolver

## Scope

This stage adds a deterministic, database-backed resolver for institution role assignments. It is a shadow-mode foundation only: `require_module_permission`, existing routes, JWT claims, frontend navigation and live authorization are not changed by this PR.

## Resolution rules

1. A real platform super-admin remains governed by the existing platform bypass; tenant role assignments do not apply to platform identities.
2. Only assignments for the authenticated user's own `school_id` are considered.
3. An assignment participates only when it is active, its role is active, and its validity window contains the current UTC time.
4. A matching `InstitutionRolePermission(enabled=True)` is an allow.
5. A matching `InstitutionRolePermission(enabled=False)` is an explicit deny. Any explicit deny across active roles overrides every role allow for the same module/action.
6. If one or more active roles allow the action and none deny it, the action is allowed. The resolver returns distinct declared scopes and contributing role/assignment IDs.
7. If no active assigned role decides the action, the existing legacy resolver order is used: school-specific RolePermission, global RolePermission, default role matrix, then route fallback roles.
8. If no rule grants access, the result is denied.

Missing permission rows mean inherit; they are not treated as denials. Scope values are returned as metadata only. This PR does not yet apply row-level scope predicates to ERP queries; that is a later data-scope hardening stage.

## Compatibility and rollout

- No automatic role assignment migration is performed.
- Existing `User.role` and `RolePermission` remain unchanged.
- Resolver queries do not cache assignments, so revocation and expiry are observed on the next evaluation.
- `compare_permission_decisions` reports legacy-vs-proposed parity without writing logs or changing request outcomes.
- The new resolver is not wired into `require_module_permission`. A later shadow-telemetry PR should add sampled, privacy-safe mismatch logging after route inventory and test coverage are complete.

## Security boundaries and limitations

- The authenticated principal's school ID is the only tenant context used.
- Cross-school assignments and roles are excluded by the join and filters.
- Parent/student relationship checks and resource-level scopes remain separate mandatory checks.
- Current `InstitutionRolePermission` schema stores a boolean. A false row is interpreted as explicit deny; future role APIs must expose deny/inherit deliberately and validate each permission against the published template ceiling.
- No JWT role/permission snapshots or permission cache are introduced.
