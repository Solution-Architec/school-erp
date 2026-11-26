# Parent Portal Leave and Messaging

## Leave applications

The Parent Portal uses the existing parent leave API:

- `GET /api/parent-portal/leave` lists requests for all currently linked students; the UI filters to the selected child.
- `POST /api/parent-portal/leave` submits a request for the selected student.
- Existing staff review endpoint: `POST /api/student-leave/{item_id}/review`.

The parent form validates the date range in the browser; the API schema also rejects an end date earlier than the start date. Parents can see pending, approved, or rejected status and the reviewer note. Parents cannot edit, delete, or review submitted requests. Cancellation is not offered because the backend does not currently expose a safe pending-only cancellation endpoint.

## Parent–teacher messages

- `GET /api/parent/children/{student_id}/message-contacts` returns active, approved school staff contacts for a student linked to the authenticated parent.
- `GET /api/parent-messages` lists messages in which the authenticated user is a sender or recipient.
- `POST /api/parent-messages` sends a message about a linked student to an approved school staff account.

The contacts endpoint is school-scoped and verifies an active parent–student link. Message submission uses the existing participant and school checks. The Parent Portal filters the message history to the selected student and labels the sender/recipient. Messages are stored in the existing in-app messaging table; no email or SMS delivery is implied.

## Limitations / next improvements

- No attachment upload/download, read receipt action, or push/email/SMS notification is added in this batch.
- The contact list currently includes approved active teachers and school leadership/admin roles in the same school; class-specific teacher mapping is not assumed.
- The leave API currently has no parent cancellation operation; add one only with an explicit pending-only authorization rule and audit event.
