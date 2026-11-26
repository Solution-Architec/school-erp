# Phase 3 — Parent Notification Centre

## Delivered foundation

- School staff can publish in-app notifications for all linked parents, a class/section, or one student’s linked parent(s).
- Categories include announcements, attendance, homework, examination, fees, and general updates.
- Parent inbox shows only published notifications from the parent's own school.
- Eligibility is resolved against active parent–student links on every inbox and read request. Deactivating a relationship immediately removes access.
- Read receipts are stored per parent and notification. Publishing and reading are written to the existing audit log.
- No phone, Aadhaar, or other identity secrets are copied into notification records.

## API

- `GET /api/school/notifications` — authorized school staff list.
- `POST /api/school/notifications` — authorized school staff publish.
- `GET /api/parent/notifications` — parent inbox, filtered to active linked students.
- `POST /api/parent/notifications/{notification_id}/read` — mark an eligible notification read.

## Delivery scope

This increment is in-app only. Staff can publish notices using the attendance, homework, examination, and fees categories. Automatic event-triggered generation (for example, generating an alert every time attendance is marked or a fee payment becomes overdue), email, SMS, and push delivery are intentionally separate follow-up work; no external delivery is implied.
