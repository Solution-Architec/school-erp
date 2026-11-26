# Phase 3 — Parent Notification Preferences

This increment adds per-parent controls for the in-app notification inbox.

## Parent controls

- A master in-app notification switch.
- Independent controls for school announcements, attendance, homework, examinations, fees, and general messages.
- Preferences are stored per authenticated parent account and school.
- The inbox applies the parent's current preferences while continuing to evaluate active parent-student links at read time.
- Defaults are enabled for every category, preserving the existing inbox experience for parents who have not changed settings.

## API

- `GET /api/parent/notification-preferences` returns the current settings (all enabled when no settings row exists).
- `PATCH /api/parent/notification-preferences` updates one or more boolean settings. Empty updates are rejected.
- Both endpoints require the Parent role and the authenticated user's school. Changes are audited.

## Security and data behavior

- A parent can update only their own preferences; the client cannot supply a parent or school ID.
- Disabling a category filters that category from the parent's in-app inbox. It does not delete notification records, change school records, or change other parents' preferences.
- Re-enabling a category makes retained matching notifications visible again, subject to current active parent-student links.
- Email, SMS, push, and external delivery are not enabled by this change.

## Follow-up

Scheduled reminders (such as upcoming fee due dates and configurable absence follow-ups) should be implemented as a separate idempotent worker with explicit school-level schedules and auditability. They are not part of this API/UI increment.
