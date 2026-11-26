# Parent identity and relationship governance

## Current access rule

Parent access is granted only by an active `ParentStudentLink` whose parent account,
student, and school IDs agree. A phone-number, guardian-name, email, or Aadhaar
match is not proof of a parent-child relationship and must never create access by
itself. The parent workspace lists only children returned by the authenticated
`GET /api/parent/children` endpoint.

## Staff relationship management

School administrators can review up to 500 parent-child links for their own
school:

- `GET /api/parent-links`
- Optional filters: `parent_user_id`, `student_id`, and `active`.
- Super Admin must supply `school_id`; school administrators are always scoped
  to their own school.

School administrators can change the relationship label or activate/deactivate
an existing link:

- `PATCH /api/parent-links/{link_id}`
- Allowed fields: `is_active` (boolean) and `relationship` (1–40 characters).

The API rejects unknown fields, invalid parent/student/school records, and
cross-school access. Every actual change writes an audit event
`parent.relationship.updated` with the affected IDs and before/after values.
Deactivating a link immediately removes that child from the parent's active
children list and causes child-specific parent endpoints to deny access.

## Mobile and Aadhaar verification boundary

The current `User` model authenticates parent accounts by email and has no
verified mobile-number field or phone OTP lifecycle. Student records contain
`guardian_phone`, but that is school-entered contact data and is not verified
identity. Therefore this change deliberately does not auto-match accounts or
create links from phone numbers.

A production mobile verification workflow still needs normalized phone storage,
OTP delivery integration, expiry/attempt/rate-limit controls, verified-at
timestamps, account recovery rules, and audit events. A phone match should
produce a staff-review candidate only; a school-authorized staff member must
confirm the relationship before a link becomes active.

Aadhaar must not be collected or stored by this application as part of ordinary
parent linking. If legally approved and genuinely required, verification must
use an authorized provider and a reviewed compliance workflow. Store only a
provider verification reference/status and minimum necessary metadata, never
raw Aadhaar numbers, scans, OTPs, or authentication secrets.

## Validation

The parent workflow tests cover school-scoped listing, deactivation/reactivation,
immediate loss of access after deactivation, invalid update rejection, and
cross-tenant denial.
