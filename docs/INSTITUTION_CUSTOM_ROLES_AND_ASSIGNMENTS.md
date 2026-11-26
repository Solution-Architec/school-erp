# Institution Custom Roles and Multiple User Assignments

This change adds the persistence and domain-service foundation for institution-local custom roles and multiple role assignments.

## Data model

- `institution_roles`: institution-owned role identity, active state, creator and source published Developer template version.
- `institution_role_permissions`: enabled module/action/scope entries for a local role.
- `user_role_assignments`: institution-scoped user-to-role assignments, activation state and optional validity window.

The schema is additive. Existing `users.role`, `role_permissions`, login behavior and current permission enforcement remain unchanged.

## Guardrails

- Only an active School Admin from the target institution can create roles or manage assignments through the service layer.
- A role must reference an active Developer template and a published version applicable to the institution's `institution_type`.
- Local role permissions must be a subset of the published template's module/action ceiling and must retain the template's declared data scope.
- Platform-only modules cannot be granted because they cannot appear in a tenant template.
- Users and roles must belong to the same institution. Inactive users/roles and platform super-admin accounts cannot receive institution role assignments.
- Duplicate active assignments are rejected. Revocation preserves the assignment record; assigning the role again reactivates that same record.
- Role and assignment lifecycle changes write audit events.
- Multiple local roles can be assigned to one user without changing their legacy `User.role`.

## Service layer

`backend/app/rbac_institutions.py` provides:

- `create_institution_role`
- `assign_institution_role`
- `set_role_assignment_active`

These functions are domain/persistence helpers, not public endpoints. Developer APIs, institution APIs, template adoption, permission resolution and effective authorization are deliberately deferred to later roadmap stages.

## Schema rollout

The repository currently creates SQLAlchemy metadata during backend startup and does not use Alembic. The new tables are additive and are created by the existing `Base.metadata.create_all` lifecycle. No existing records are rewritten or deleted.

## Tests

`backend/tests/test_rbac_institutions.py` covers template ceilings, scope ceilings, same-institution administrator checks, multiple assignments, duplicate prevention, revocation/reactivation, cross-tenant rejection, platform-account rejection and assignment validity windows.
