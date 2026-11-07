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
