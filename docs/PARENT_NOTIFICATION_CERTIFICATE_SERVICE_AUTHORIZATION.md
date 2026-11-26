# Parent, Notification, Certificate and Service Authorization

## Scope

This stage connects service-specific staff operations to the live multi-role
permission resolver while preserving the parent identity and relationship checks
that protect family data.

## Service authorization

- Certificate queue and staff PDF access require
  `certificate-management:View`.
- Certificate review and issuance require `certificate-management:Approve`.
- Parent reminder settings use `notifications:View` and
  `notifications:Edit`; module permission is the authorization boundary rather
  than a second hard-coded list of legacy role names.
- Student leave review relies on `student-leave:Approve` plus same-school
  record scoping; custom roles can receive this capability explicitly.
- Parent/teacher messaging relies on its module permissions and continues to
  restrict parent access to actively linked children and same-school approved
  participants.

## Preserved parent safeguards

Parent-only routes still require a parent account where appropriate, and every
child-specific read or write continues to verify an active same-school
ParentStudentLink. Parent certificate downloads additionally require that the
requesting parent is the original applicant and remains linked to the student.
Parent notification visibility continues to be derived from current active
relationships. No Aadhaar or unverified phone match grants access.

## Existing guards retained

The notifications publishing and parent inbox routes already use
`require_module_permission`. Transport/hostel facility requests and parent
facility workflows also already use the shared module guard and retain their
service-level school and linked-child checks.

## Tests

- Custom-role grants for certificate view/approval, notification settings and
  leave review are accepted through the live resolver.
- Explicit custom-role denial blocks certificate approval.
- Existing parent relationship, tenant-isolation, notification read-state,
  certificate issuance and service workflow tests remain regression coverage.

Data-scope metadata is not treated as row-level filtering by itself. The
dedicated data-scope and tenant-isolation stage remains responsible for
enforcing own, assigned, class/section, department and selected-record scopes.
