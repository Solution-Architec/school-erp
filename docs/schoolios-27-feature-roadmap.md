# Schoolios ERP — 27 Feature Expansion

This roadmap groups the requested 15 + 9 + 3 features into three delivery tiers. Keep existing authentication, school isolation, role permissions, and API contracts intact while implementing each item.

## 15 Core school operations
1. Attendance register with daily class-wise marking
2. Timetable and period scheduling
3. Exams, assessments, and marks entry
4. Report cards and grading
5. Homework and assignment tracking
6. Student leave requests and approvals
7. Parent-teacher communication
8. Library catalog and issue/return tracking
9. Inventory and asset register
10. School calendar and events
11. Visitor register and gate passes
12. Student health / nurse visit log (restricted access)
13. Certificates and bonafide letter generation
14. Staff attendance and leave management
15. Payroll and payslip workflow

## 9 Advanced capabilities
16. Bus route planning and GPS integration hooks
17. Hostel room allocation and occupancy
18. Online payment gateway integration with reconciliation
19. SMS / email / push notification templates
20. Multi-school analytics and benchmarking for platform admins
21. Document upload, expiry reminders, and verification
22. Approval workflow builder for common requests
23. Role-based audit log with export
24. Data import/export (CSV) with validation and error reports

## 3 Smart / AI capabilities
25. School FAQ assistant grounded in approved school documents
26. Attendance, fee, and enrollment anomaly / trend insights
27. AI-assisted timetable and resource scheduling suggestions

## Implementation guidance
- Deliver in small vertical slices: database model + migration, API, permissions, UI, tests, and documentation.
- Never expose cross-school records to school-level roles.
- Keep AI suggestions reviewable; do not auto-submit grades, payments, or sensitive decisions.
- Integrations (GPS, payment gateway, SMS/email) require school-specific credentials and consent.
- This document is a roadmap, not a claim that all 27 features are implemented.


## Phase 1 implementation status
The first four academic workflows have now been added to the application code and registered as school-scoped modules:
- Attendance register: daily student status and remarks, with one record per student per date
- Timetable: weekday periods, subject, teacher, room, and start/end times
- Exams: class/section subject schedule, maximum marks, pass marks, and academic year
- Report cards: student/exam marks and remarks, with school-consistent references and maximum-mark validation

The UI and API changes are committed. Runtime database migration, deployment, and end-to-end verification still need to run in the target environment before these features should be considered production-verified.


## Phase 2 implementation — homework, leave, and parent communication

### Homework
- School-scoped class/section/subject homework assignments with title, instructions, due date, optional attachment URL, and assigning user.
- List/create/update/delete API under `/api/homework`; tenant scoping follows the existing generic CRUD policy.

### Student leave
- School-scoped student leave applications with date-range validation and pending/approved/rejected status.
- Staff CRUD under `/api/student-leave`; approval/rejection through `POST /api/student-leave/{id}/review` with reviewer attribution.
- Parent accounts can submit and view leave requests only for students connected by an active `ParentStudentLink`, through `/api/parent-portal/leave`.

### Parent–teacher communication
- Private school-scoped messages with explicit student, sender, recipient, subject, body, and timestamps.
- `GET/POST /api/parent-messages` returns only messages where the authenticated user is sender or recipient. Parents must have an active link to the student; staff recipients and parent recipients are validated against the same school and student link.

### Schema and deployment
- New tables are created by the existing SQLAlchemy `Base.metadata.create_all` startup mechanism: `homework`, `student_leave_requests`, and `parent_teacher_messages`.
- No Alembic migration system exists in this repository. Back up the database and restart the backend so the startup table creation runs before using the new endpoints.
- Parent messaging currently uses user IDs for the recipient selector; a staff directory/teacher assignment picker and message threading/read receipts are follow-up improvements.
- Run backend tests with `cd backend && pytest`; frontend validation with `cd frontend && npm ci && npm run build`.


## Phase 3 implementation — library management

### Library catalog
- Added school-scoped book records with title, author, ISBN, publisher, category, total copies, available copies, and shelf location.
- Book creation initializes available copies from the total copy count.
- Book edits adjust available copies by the total-copy delta and reject reductions below the number currently issued.
- Book records cannot be moved between schools or deleted after loan history exists.

### Issue and return workflow
- Added school-scoped loan records linking one library book and one student in the same school.
- Issuing a book locks the book row, checks availability, decrements available copies, and records the issuing user and due date.
- Returning a book uses an explicit API state transition, restores one available copy, records the return timestamp, and writes an audit event.
- Loan history is retained; returned loans cannot be edited or deleted.
- All book and loan list/create/update operations use the existing module permission guard and tenant-scoping mechanism.

### Verification still required
- Run backend tests and frontend production build in CI.
- Exercise issue/return flows against PostgreSQL, including no-stock, duplicate-return, cross-school book/student, and book-delete-with-history cases.
- Apply the startup table creation on a backed-up staging database before production use.
