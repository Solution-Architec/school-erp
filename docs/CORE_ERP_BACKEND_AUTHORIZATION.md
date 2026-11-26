# Core ERP Backend Authorization

## Purpose

Wire the deterministic multi-role resolver into the shared core ERP route guard,
`require_module_permission`, without changing individual route declarations.
This is the first live authorization integration stage; parent, notification,
certificate and other service-specific routes remain scheduled for the next
service-enforcement stage.

## Live decision order

1. Platform workspace wrapper: preserve its existing scoped workspace bypass.
2. Platform super administrator: preserve the existing platform bypass.
3. Active institution role assignments: evaluate same-school, active assignments
   whose start/end window includes the current UTC instant.
   - Any matching explicit deny from an active assigned role denies the action.
   - Otherwise, one or more matching enabled grants allow the action.
   - Missing permission rows inherit and do not decide the action.
4. If no custom role decides the action, use the compatible legacy order:
   school-scoped `RolePermission`, global `RolePermission`, default role
   permission matrix, existing library restrictions and route fallback roles.

The resolver is called on each request. No permission cache or JWT permission
snapshot is introduced, so role/assignment deactivation and expiry take effect
on the next authorization evaluation.

## Scope

This change integrates the resolver at the shared module-permission guard used
by core ERP routes. It does not change `require_roles`, login/JWT claims,
`User.role`, legacy `RolePermission` storage, route-specific tenant filters,
or the resolver's data-scope metadata. Data-scope enforcement (own, assigned,
class/section, department, institution, selected records and parent/student
relationship) remains a separate hardening stage; a permission grant must not
be interpreted as proof that row-level scope filtering is complete.

Parent portal, notification, certificate, transport/hostel and other service
authorization receive their dedicated route-by-route review in the next stage.
Platform-only APIs continue to use explicit role dependencies.

## Validation

The resolver tests exercise:
- multi-role allow union and explicit-deny precedence;
- inactive, future and expired assignments;
- fallback to legacy grants/defaults when no custom role decides;
- live core guard allow/deny behavior and unassigned-user compatibility.

Run:

```bash
PYTHONPATH=.:backend pytest -q backend/tests/test_rbac_resolver.py backend/tests/test_security_authorization.py
```
