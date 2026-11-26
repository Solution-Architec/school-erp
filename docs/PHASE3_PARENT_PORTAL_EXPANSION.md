# Phase 3 Parent Portal Expansion

## Goal

Extend the Parent role into a secure Family Services Portal for every actively linked student. Keep parent data access read-only unless the action is an explicitly supported parent request/application. Parents must never directly edit school-owned student, transport, hostel, exam, attendance, fee, or document records.

## Parent-facing sections

1. **Family and student profile** — switch between all actively linked children; show admission number, class, section, academic year, and school contact details. Never infer a parent-child relationship from name, phone number, or email; use active ParentStudentLink records only.
2. **Academics** — exam timetable and subject-wise schedule; published exam results with exam, subject, marks, maximum marks, grade/result, remarks, and report-card download when a published file exists; homework and attachments; class timetable; academic calendar and holidays.
3. **Attendance** — daily attendance and history for the selected linked student. Show only date and parent-safe status; do not expose staff-only remarks or internal staff identifiers.
4. **Certificates and documents** — apply for bonafide/study, conduct, transfer, and school-configured certificates. Capture purpose, copies/format, delivery preference, and optional parent note. Track submitted, under review, needs information, approved, rejected, and issued. Download only securely issued/published documents.
5. **Transport** — view assigned vehicle, route, pickup/drop point, timings, and approved contact details. Submit allocation, route, pickup/drop change, or discontinuation requests. Transport Manager reviews; authorized staff update the official allocation. Do not expose private driver information beyond approved contact fields.
6. **Hostel** — view assigned hostel, building, room/bed, warden contact, and approved rules. Submit hostel admission, room/bed change, leave/intimation, or discontinuation requests. Hostel Warden reviews; parents cannot directly change occupancy or room assignments.
7. **Fees** — fee category, academic year, total, discount, paid, balance, due date, payment history, and receipts. Payment gateway integration remains optional and must not be represented as enabled unless configured.
8. **Student services** — leave applications and status; parent–teacher messages; parent consent/permission forms for trips, activities, and events; lost-and-found or general school-office service request.
9. **Communication** — announcements, circulars, events, holidays, emergency notices, and per-student alerts. In-app notification inbox first; email/SMS/push as optional configured channels. Show request status changes and unread indicators.

## Required data and workflows

- Add explicit, school-scoped student-to-vehicle and student-to-hostel assignment relationships. Existing Student records only have transport_required and hostel_required flags; these are not assignments.
- Add school-scoped parent service requests for certificates, transport changes, and hostel changes, with requester, linked student, request type, details, status, reviewer, reviewer note, timestamps, and audit events.
- Use separate approval permissions for certificate issuance, transport allocation, and hostel allocation.
- Return exam results by joining ReportCard to Exam and filtering on the authenticated parent's active linked student and school. Only published/approved results should be visible.
- Issued certificate/report-card files must use private document storage; never expose raw storage keys or unprotected file paths.
- Every endpoint must enforce role, school, and active parent-student link checks on the backend. Unlinked, inactive-link, and cross-school student IDs must return not-found without leaking existence.
- Audit submissions, reviews, issuance, allocation changes, and document access.
- Parent actions are requests, not direct edits to authoritative school records.

## Suggested implementation sequence

- **P3.2A** Parent portal shell, multi-child selector, profile, results, homework, timetable, and calendar read views.
  - Homework and timetable read views now use `/api/parent/children/{student_id}/homework` and `/api/parent/children/{student_id}/timetable`. Both require an active parent-student link and resolve class/section from the linked student; results are school-scoped. Homework exposes only parent-safe assignment fields and HTTP(S) attachment links.
- **P3.2B** Certificate application and issuance workflow.
- **P3.2C** Transport/hostel assignment read views and parent change-request workflows.
- **P3.2D** Notifications, consent forms, service requests, accessibility, and mobile layout.
- **P3.2E** Tenant-isolation, authorization, audit, file-access, and end-to-end acceptance tests.

## Acceptance checks

- Parent can access only actively linked students in their own school.
- Switching children refreshes every section and never briefly displays the previous child's data.
- Parents cannot create, edit, delete, approve, or publish authoritative school records.
- Exam results and documents are visible only after school publication/issuance.
- Transport/hostel requests do not alter assignments until authorized staff approve and update allocation.
- Every request has a visible status and review history; sensitive actions are audited.
- Existing attendance and fee views continue to work independently if another section fails to load.