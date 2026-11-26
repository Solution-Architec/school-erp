# Phase 3 — Automatic Parent Event Alerts

This increment builds on the in-app notification inbox from PR #96. It generates parent-facing notifications inside the same database transaction as the underlying school record change.

## Events covered

- Attendance: a new attendance mark and a change to the marked status/date generate a student-targeted alert.
- Homework: new assignments and edits to the title, description, or due date generate class/section-targeted alerts.
- Examination results: a new report card and a marks change generate a student-targeted alert.
- Fees: a new fee assignment and changes to amount, discount, or due date generate a student-targeted alert.
- Fee payments: recording a payment generates a student-targeted receipt/balance alert.

## Delivery and security

- Alerts are in-app only and are created in the same transaction as the source event. A failed source transaction therefore does not leave a notification behind.
- Parent recipients are not snapshotted. The parent inbox re-evaluates active parent-student links and school scope on every read, so revoked links lose access immediately.
- Homework notices target the assigned class and optional section. Other alerts target one student.
- Fee and examination details are visible only to currently linked parents through the parent inbox.
- Event generation is audited using the existing audit log.
- No phone, Aadhaar, email, SMS provider, or external push service is used.

## Deliberate boundaries

- This is event-triggered in-app messaging, not a background scheduler.
- No repeated daily overdue-fee reminders, absence escalation rules, attendance threshold alerts, or email/SMS/push channels are enabled.
- Bulk attendance imports are not part of this increment; the normal attendance create/update workflow is covered.
