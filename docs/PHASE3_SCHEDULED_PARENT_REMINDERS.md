# Phase 3 — Scheduled Parent Reminders

## Included reminders

The dedicated `parent-reminder-worker` service generates in-app reminders for:

- Outstanding student fee balances approaching their due date.
- Students marked absent for the current school-local date.

The worker checks approximately every 15 minutes by default. Set `REMINDER_POLL_SECONDS` to change the interval (minimum 60 seconds).

## School settings

School leadership (Admin, Principal, Vice Principal) can configure settings in the Notification Centre:

- Enable or pause fee due-date reminders.
- Choose 0–30 days before the fee due date (common choices are shown in the UI).
- Enable or pause same-day absence alerts.
- Select the school's IANA timezone (default `Asia/Kolkata`).

Settings are scoped to the authenticated user's school and changes are audited. Parents cannot modify school reminder schedules.

## Idempotency and security

- A unique dispatch key is stored for each fee due-date version and attendance absence record. Repeated worker cycles do not create duplicate notifications.
- Fee reminders are created only when the calculated balance (total minus discount and recorded payments) is positive.
- Notifications are student-targeted. The parent inbox resolves visibility at read time from current active same-school parent-student links.
- Parent category preferences continue to apply. Disabling a category hides its in-app notices without deleting records.
- Worker-generated notifications use a null staff creator; audit records identify them as system-generated rather than attributing them to a staff member.
- The worker waits for API schema initialization before polling.

## Operations

Compose starts `parent-reminder-worker` as a separate restartable service using the backend image and the same database configuration. Check it with:

```bash
docker compose logs -f parent-reminder-worker
docker compose ps parent-reminder-worker
```

The service does not send email, SMS, WhatsApp, or push notifications. It creates in-app inbox records only.

## Notes

- Fee reminders are generated for fees whose due date is today or within the configured look-ahead window. A later change to a fee's due date produces a new idempotency key.
- Absence alerts are generated only for records whose status is `absent`; late and leave statuses do not trigger this alert.
- School timezone is used for date matching. A reminder can be delayed by up to the configured polling interval.
