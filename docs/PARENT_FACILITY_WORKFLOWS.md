# Parent Portal Transport and Hostel Workflows

## Parent endpoints

- `GET /api/parent/children/{student_id}/facilities` returns the selected linked student's active transport and hostel allocation, when recorded.
- `GET /api/parent/children/{student_id}/facility-requests` lists requests submitted by the authenticated parent for that student.
- `POST /api/parent/children/{student_id}/facility-requests` submits a transport or hostel request. The request is pending and does not change official allocations.

All parent endpoints require the Parent role, an active `ParentStudentLink`, and matching `school_id`. Unlinked, inactive-link, and cross-school student IDs return 404.

## Staff review endpoints

- `GET /api/facility-requests?facility_type=transport` — Admin, Principal, Vice Principal, or Transport Manager.
- `GET /api/facility-requests?facility_type=hostel` — Admin, Principal, Vice Principal, or Hostel Warden.
- `POST /api/facility-requests/{request_id}/review` — approve or reject a pending request, with an optional reviewer note.

Approval applies only the supported fields supplied in the request. Vehicle and hostel IDs are checked against the staff member's school and must refer to active records. A request can be reviewed only once. Submissions, reviews, and allocation updates are audited.

## Request types

Transport: `new_allocation`, `route_change`, `pickup_change`, `drop_change`, `discontinue`.

Hostel: `new_allocation`, `room_change`, `bed_change`, `discontinue`.

The parent portal displays assignment details and request status. Parents cannot directly modify allocations. Staff still need to maintain the school's vehicle/hostel inventory and review requests.

## Database

The API registers three SQLAlchemy tables at application startup:

- `student_transport_assignments`
- `student_hostel_assignments`
- `parent_facility_requests`

The tables are created with the existing metadata startup process; no existing student, vehicle, or hostel rows are rewritten.
