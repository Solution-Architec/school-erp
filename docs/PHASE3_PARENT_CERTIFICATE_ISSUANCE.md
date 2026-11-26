# P3.8 — Parent certificate review and issuance

## Workflow
- Parents submit certificate requests only for students connected through an active, same-school parent-student relationship.
- School Admin, Principal and Vice Principal can review requests within their own school.
- Only approved requests can be issued. Issuance creates one immutable, school-unique certificate number and records the issuing staff account and timestamp.
- A certificate PDF is generated on demand; the application and issuance metadata remain in the database. No public file URL or unauthenticated storage path is created.
- Parent downloads re-check the active parent-student link and the original applicant account on every request. School staff downloads are restricted to their own school.
- Review, issuance and download actions are audited. Repeated issue attempts return a conflict rather than creating duplicate certificates.

## API
- GET /api/certificate-applications?status=pending|approved|rejected|all — school-scoped staff queue.
- POST /api/certificate-applications/{application_id}/review — existing review transition.
- POST /api/certificate-applications/{application_id}/issue — issue an approved application.
- GET /api/certificate-issues/{issue_id}/download — authorized same-school staff PDF download.
- GET /api/parent/certificates/{issue_id}/download — parent PDF download after active-link and applicant checks.

## Data and deployment
- Adds certificate_issues through SQLAlchemy metadata table creation. Existing certificate application records are not rewritten.
- Adds ReportLab to backend dependencies for server-side PDF generation.
- No external document storage, payment provider, signature image, or fabricated signatory is introduced. The PDF leaves an unsigned authorized-signatory line for the school to complete under its own process.

## Validation
- Backend tests cover review/issuance state transitions, duplicate issuance, parent link revocation, parent ownership, staff tenant scope, and PDF response content type.
- Frontend build and full repository CI are required before merge.
