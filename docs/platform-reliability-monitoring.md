# Platform reliability monitoring and offsite backups

## PostgreSQL recovery points

The backup job keeps the newest verified recovery point per UTC day for 7 days, per ISO week for 4 weeks, and per calendar month for 12 months. Configure `BACKUP_DAILY_RETENTION_DAYS`, `BACKUP_WEEKLY_RETENTION_WEEKS`, and `BACKUP_MONTHLY_RETENTION_MONTHS`.

For offsite S3-compatible storage, configure the following in the untracked project-root `.env` file:

```dotenv
BACKUP_S3_URI=s3://your-private-bucket/edunexus/postgres
AWS_DEFAULT_REGION=ap-south-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
# Optional for S3-compatible storage:
AWS_ENDPOINT_URL=https://s3.example-provider.com
```

Use a dedicated least-privilege bucket identity. Never commit credentials. Uploads request server-side AES256 encryption; the job downloads the remote object again, validates the archive and restores it into a temporary isolated PostgreSQL instance before reporting success. A failed upload or remote restore leaves the attempt failed. Configure independent bucket versioning/lifecycle retention; local retention does not remove remote objects.

## Platform monitoring

The `platform-monitor` service checks:
- Application/API health at `/api/health` (including the API's reported database state).
- TLS certificate expiry for configured hostnames.
- Domain expiry using RDAP.
- SMTP connection, TLS and authentication. If `MONITOR_SMTP_TEST_EMAIL` is set, it sends one actual delivery test per 24 hours.
- Razorpay API authentication using a read-only payment-list request.
- Razorpay webhook endpoint reachability and signature enforcement by submitting an invalid signature and expecting HTTP 400. This does not create or modify a payment.

Configure in `.env`:

```dotenv
MONITOR_INTERVAL_SECONDS=900
MONITOR_APP_URL=http://backend:8000
MONITOR_TLS_HOSTS=school.example.com,api.school.example.com
MONITOR_DOMAINS=school.example.com
MONITOR_ALERT_EMAIL=developer@example.com
MONITOR_SMTP_TEST_EMAIL=developer@example.com
```

The monitor reuses `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_USE_SSL`, and `SMTP_USE_TLS`. Razorpay checks run only when `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` are configured. Email alerts are sent on new warning/critical states and recovery transitions. State is persisted in the `platform_monitor_state` volume.

## Start and inspect

```bash
docker compose up -d --build db-backup platform-monitor
docker compose logs --tail=100 db-backup platform-monitor
docker compose exec platform-monitor cat /state/monitor-state.json
docker compose exec db-backup cat /backups/backup-status.json
```

## Operational limitations

- TLS and RDAP checks need outbound network access. Some registries omit expiration events; the monitor reports the check as unavailable rather than guessing.
- Empty TLS/domain configuration is reported as not configured, not healthy.
- SMTP alerting depends on SMTP itself; it cannot report SMTP failure through itself.
- Offsite verification becomes active only after an operator supplies a real bucket and credentials. CI cannot validate cloud-account configuration without secrets.
- The monitor does not inspect Razorpay's webhook delivery queue or prove that a real payment webhook was delivered; it verifies API access and the local webhook endpoint's signature rejection behavior.
- Automatic Developer Control Centre incident creation and host-level CPU/disk monitoring are not included.
- Validate certificate/domain alerts, SMTP delivery and cloud restore against the actual production environment before relying on them.
