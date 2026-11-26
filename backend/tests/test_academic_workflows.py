from datetime import date
import pytest
from pydantic import ValidationError

from backend.app.schemas import HomeworkIn, StudentLeaveIn, StudentLeaveReviewIn, ParentTeacherMessageIn


def test_homework_requires_title_and_due_date():
    payload = HomeworkIn(class_name="5", subject="Science", title="Plants", due_date=date(2026, 11, 12))
    assert payload.title == "Plants"
    with pytest.raises(ValidationError):
        HomeworkIn(class_name="5", subject="Science", title="", due_date=date(2026, 11, 12))


def test_leave_rejects_end_before_start():
    with pytest.raises(ValidationError):
        StudentLeaveIn(student_id=12, start_date=date(2026, 11, 12),
                       end_date=date(2026, 11, 10), reason="Family function")


def test_leave_accepts_valid_date_range():
    payload = StudentLeaveIn(student_id=12, start_date=date(2026, 11, 10),
                             end_date=date(2026, 11, 12), reason="Family function")
    assert payload.end_date >= payload.start_date


def test_leave_review_only_accepts_approved_or_rejected():
    assert StudentLeaveReviewIn(status="approved").status == "approved"
    with pytest.raises(ValidationError):
        StudentLeaveReviewIn(status="pending")


def test_parent_teacher_message_requires_nonempty_bounded_body():
    payload = ParentTeacherMessageIn(student_id=1, recipient_user_id=2, body="Please call me")
    assert payload.body == "Please call me"
    with pytest.raises(ValidationError):
        ParentTeacherMessageIn(student_id=1, recipient_user_id=2, body=" ")

# API-level tenant and participant authorization tests for the academic workflows.
@pytest.fixture
def academic_api_context():
    import asyncio
    from types import SimpleNamespace

    import httpx
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from backend.app import models
    from backend.app.database import Base, get_db
    from backend.app.main import app
    from backend.app.security import current_user

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    actor = {}
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[current_user] = lambda: actor["user"]

    with SessionLocal() as db:
        school = models.School(name="Academic Test School", code="ACADEMIC-TEST")
        other_school = models.School(name="Other Academic School", code="ACADEMIC-OTHER")
        db.add_all([school, other_school])
        db.flush()

        parent = models.User(
            name="Linked Parent", email="parent.academic@example.test",
            password_hash="unused", role="parent", school_id=school.id,
            is_active=True, approval_status="approved",
        )
        teacher = models.User(
            name="School Teacher", email="teacher.academic@example.test",
            password_hash="unused", role="teacher", school_id=school.id,
            is_active=True, approval_status="approved",
        )
        other_parent = models.User(
            name="Other Parent", email="other-parent.academic@example.test",
            password_hash="unused", role="parent", school_id=school.id,
            is_active=True, approval_status="approved",
        )
        school_admin = models.User(
            name="School Admin", email="admin.academic@example.test",
            password_hash="unused", role="admin", school_id=school.id,
            is_active=True, approval_status="approved",
        )
        db.add_all([parent, teacher, other_parent, school_admin])
        db.flush()

        linked_student = models.Student(
            school_id=school.id, admission_no="A-001", full_name="Linked Child",
            class_name="5", section="A",
        )
        unlinked_student = models.Student(
            school_id=school.id, admission_no="A-002", full_name="Other Child",
            class_name="5", section="B",
        )
        inactive_link_student = models.Student(
            school_id=school.id, admission_no="A-003", full_name="Formerly Linked Child",
            class_name="6", section="A",
        )
        cross_school_student = models.Student(
            school_id=other_school.id, admission_no="B-001", full_name="Cross School Child",
            class_name="5", section="A",
        )
        db.add_all([linked_student, unlinked_student, inactive_link_student, cross_school_student])
        db.flush()

        db.add_all([
            models.ParentStudentLink(
                school_id=school.id, parent_user_id=parent.id,
                student_id=linked_student.id, is_active=True,
            ),
            models.ParentStudentLink(
                school_id=school.id, parent_user_id=other_parent.id,
                student_id=unlinked_student.id, is_active=True,
            ),
            models.ParentStudentLink(
                school_id=school.id, parent_user_id=parent.id,
                student_id=inactive_link_student.id, is_active=False,
            ),
        ])
        for action in ("View", "Create", "Edit", "Delete", "Approve"):
            db.add(models.RolePermission(
                role="parent", module_key="student-leave", action=action,
                enabled=True, school_id=school.id,
            ))
        for action in ("View", "Create"):
            db.add(models.RolePermission(
                role="parent", module_key="parent-messages", action=action,
                enabled=True, school_id=school.id,
            ))

        leave_linked = models.StudentLeaveRequest(
            school_id=school.id, student_id=linked_student.id,
            start_date=date(2026, 11, 10), end_date=date(2026, 11, 11),
            reason="Family function", status="pending",
        )
        leave_unlinked = models.StudentLeaveRequest(
            school_id=school.id, student_id=unlinked_student.id,
            start_date=date(2026, 11, 10), end_date=date(2026, 11, 11),
            reason="Other family function", status="pending",
        )
        leave_inactive_link = models.StudentLeaveRequest(
            school_id=school.id, student_id=inactive_link_student.id,
            start_date=date(2026, 11, 10), end_date=date(2026, 11, 11),
            reason="Formerly linked", status="pending",
        )
        leave_cross_school = models.StudentLeaveRequest(
            school_id=other_school.id, student_id=cross_school_student.id,
            start_date=date(2026, 11, 10), end_date=date(2026, 11, 11),
            reason="Cross school", status="pending",
        )
        db.add_all([leave_linked, leave_unlinked, leave_inactive_link, leave_cross_school])
        db.flush()

        message_linked = models.ParentTeacherMessage(
            school_id=school.id, student_id=linked_student.id,
            sender_user_id=parent.id, recipient_user_id=teacher.id,
            subject="Linked conversation", body="Only participants should see this.",
        )
        message_other_parent = models.ParentTeacherMessage(
            school_id=school.id, student_id=unlinked_student.id,
            sender_user_id=other_parent.id, recipient_user_id=teacher.id,
            subject="Other parent", body="Not visible to the first parent.",
        )
        message_inactive_link = models.ParentTeacherMessage(
            school_id=school.id, student_id=inactive_link_student.id,
            sender_user_id=parent.id, recipient_user_id=teacher.id,
            subject="Inactive relationship", body="No longer visible after unlinking.",
        )
        db.add_all([message_linked, message_other_parent, message_inactive_link])

        attendance_linked_recent = models.AttendanceRecord(
            school_id=school.id, student_id=linked_student.id,
            attendance_date=date(2026, 11, 24), status="absent",
            remarks="Internal note must not be visible to parents.", marked_by=teacher.id,
        )
        attendance_linked_older = models.AttendanceRecord(
            school_id=school.id, student_id=linked_student.id,
            attendance_date=date(2026, 11, 20), status="present",
            remarks="Staff-only note.", marked_by=teacher.id,
        )
        attendance_unlinked = models.AttendanceRecord(
            school_id=school.id, student_id=unlinked_student.id,
            attendance_date=date(2026, 11, 24), status="late",
            remarks="Unlinked student.", marked_by=teacher.id,
        )
        attendance_inactive_link = models.AttendanceRecord(
            school_id=school.id, student_id=inactive_link_student.id,
            attendance_date=date(2026, 11, 24), status="leave",
            remarks="Inactive relationship.", marked_by=teacher.id,
        )
        attendance_cross_school = models.AttendanceRecord(
            school_id=other_school.id, student_id=cross_school_student.id,
            attendance_date=date(2026, 11, 24), status="present",
            remarks="Other tenant.", marked_by=teacher.id,
        )
        db.add_all([
            attendance_linked_recent, attendance_linked_older,
            attendance_unlinked, attendance_inactive_link, attendance_cross_school,
        ])
        exam_linked = models.Exam(
            school_id=school.id, name="Term 1", class_name="5", section="A",
            subject="Science", exam_date=date(2026, 11, 18),
            max_marks=100, pass_marks=35, academic_year="2026-27",
        )
        exam_unlinked = models.Exam(
            school_id=school.id, name="Term 1", class_name="5", section="B",
            subject="Maths", exam_date=date(2026, 11, 18),
            max_marks=100, pass_marks=35, academic_year="2026-27",
        )
        db.add_all([exam_linked, exam_unlinked])
        db.flush()
        report_linked = models.ReportCard(
            school_id=school.id, student_id=linked_student.id,
            exam_id=exam_linked.id, marks_obtained=82,
            remarks="Good progress",
        )
        report_unlinked = models.ReportCard(
            school_id=school.id, student_id=unlinked_student.id,
            exam_id=exam_unlinked.id, marks_obtained=28,
            remarks="Needs support",
        )
        db.add_all([report_linked, report_unlinked])

        homework_linked = models.Homework(
            school_id=school.id, class_name="5", section="A", subject="Science",
            title="Plant cells", description="Draw and label a plant cell.",
            assigned_by=teacher.id, due_date=date(2026, 11, 30),
            attachment_url="https://school.example.test/plant-cells.pdf",
        )
        homework_other_section = models.Homework(
            school_id=school.id, class_name="5", section="B", subject="Maths",
            title="Fractions", description="Complete exercise 4.",
            assigned_by=teacher.id, due_date=date(2026, 11, 29),
        )
        homework_cross_school = models.Homework(
            school_id=other_school.id, class_name="5", section="A", subject="English",
            title="Cross-school work", description="Must not be visible.",
            assigned_by=teacher.id, due_date=date(2026, 11, 28),
        )
        timetable_linked = models.TimetableEntry(
            school_id=school.id, class_name="5", section="A",
            day_of_week="Monday", period=1, subject="Science",
            teacher_name="Test Teacher", room="A-101",
            start_time="09:00", end_time="09:45",
        )
        timetable_other_section = models.TimetableEntry(
            school_id=school.id, class_name="5", section="B",
            day_of_week="Monday", period=1, subject="Maths",
            teacher_name="Other Teacher", room="B-101",
            start_time="09:00", end_time="09:45",
        )
        timetable_cross_school = models.TimetableEntry(
            school_id=other_school.id, class_name="5", section="A",
            day_of_week="Monday", period=2, subject="Other School",
            teacher_name="Private", room="X-1",
            start_time="09:45", end_time="10:30",
        )
        db.add_all([
            homework_linked, homework_other_section, homework_cross_school,
            timetable_linked, timetable_other_section, timetable_cross_school,
        ])

        db.commit()

        ids = {
            "school_id": school.id,
            "other_school_id": other_school.id,
            "parent_id": parent.id,
            "teacher_id": teacher.id,
            "other_parent_id": other_parent.id,
            "school_admin_id": school_admin.id,
            "linked_student_id": linked_student.id,
            "unlinked_student_id": unlinked_student.id,
            "inactive_link_student_id": inactive_link_student.id,
            "cross_school_student_id": cross_school_student.id,
            "leave_linked_id": leave_linked.id,
            "leave_unlinked_id": leave_unlinked.id,
            "leave_cross_school_id": leave_cross_school.id,
            "message_linked_id": message_linked.id,
            "attendance_linked_recent_id": attendance_linked_recent.id,
            "attendance_linked_older_id": attendance_linked_older.id,
            "attendance_unlinked_id": attendance_unlinked.id,
            "attendance_inactive_link_id": attendance_inactive_link.id,
            "attendance_cross_school_id": attendance_cross_school.id,
            "report_linked_id": report_linked.id,
            "report_unlinked_id": report_unlinked.id,
            "homework_linked_id": homework_linked.id,
            "timetable_linked_id": timetable_linked.id,
        }

    actor["user"] = SimpleNamespace(
        id=ids["parent_id"], role="parent", school_id=ids["school_id"], is_active=True,
    )

    def api_request(method, path, json_body=None):
        async def send():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                return await client.request(method, path, json=json_body)
        return asyncio.run(send())

    yield actor, ids, api_request

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_parent_leave_generic_crud_is_link_scoped(academic_api_context):
    actor, ids, api_request = academic_api_context
    response = api_request("GET", "/api/student-leave")
    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [ids["leave_linked_id"]]

    response = api_request("GET", f"/api/student-leave/{ids['leave_unlinked_id']}")
    assert response.status_code == 404


def test_parent_leave_submission_cannot_target_unlinked_or_cross_school_student(academic_api_context):
    actor, ids, api_request = academic_api_context
    payload = {
        "school_id": ids["other_school_id"],
        "student_id": ids["unlinked_student_id"],
        "start_date": "2026-11-10",
        "end_date": "2026-11-11",
        "reason": "Family function",
    }
    response = api_request("POST", "/api/student-leave", payload)
    assert response.status_code == 404

    response = api_request("POST", "/api/parent-portal/leave", payload)
    assert response.status_code == 404

    payload["student_id"] = ids["cross_school_student_id"]
    response = api_request("POST", "/api/student-leave", payload)
    assert response.status_code == 404


def test_parent_cannot_edit_delete_or_review_leave(academic_api_context):
    actor, ids, api_request = academic_api_context
    payload = {
        "student_id": ids["linked_student_id"],
        "start_date": "2026-11-10",
        "end_date": "2026-11-11",
        "reason": "Changed request",
    }
    response = api_request("PUT", f"/api/student-leave/{ids['leave_linked_id']}", payload)
    assert response.status_code == 403

    response = api_request("DELETE", f"/api/student-leave/{ids['leave_linked_id']}")
    assert response.status_code == 403

    response = api_request(
        "POST",
        f"/api/student-leave/{ids['leave_linked_id']}/review",
        {"status": "approved", "reviewer_note": ""},
    )
    assert response.status_code == 403


def test_homework_creation_records_authenticated_assigning_user(academic_api_context):
    actor, ids, api_request = academic_api_context
    actor["user"] = type(actor["user"])(
        id=ids["teacher_id"], role="teacher", school_id=ids["school_id"], is_active=True,
    )
    response = api_request("POST", "/api/homework", {
        "class_name": "5",
        "section": "A",
        "subject": "Science",
        "title": "Plant cells",
        "description": "Draw and label a plant cell.",
        "due_date": "2026-11-12",
    })
    assert response.status_code == 200
    assert response.json()["school_id"] == ids["school_id"]
    assert response.json()["assigned_by"] == ids["teacher_id"]


def test_parent_messages_only_show_active_linked_student_conversations(academic_api_context):
    actor, ids, api_request = academic_api_context
    response = api_request("GET", "/api/parent-messages")
    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [ids["message_linked_id"]]

    response = api_request("POST", "/api/parent-messages", {
        "student_id": ids["linked_student_id"],
        "recipient_user_id": ids["teacher_id"],
        "subject": "Attendance question",
        "body": "Could you please call me?",
    })
    assert response.status_code == 200
    assert response.json()["school_id"] == ids["school_id"]

    response = api_request("POST", "/api/parent-messages", {
        "student_id": ids["unlinked_student_id"],
        "recipient_user_id": ids["teacher_id"],
        "subject": "Unlinked child",
        "body": "This should be rejected.",
    })
    assert response.status_code == 404


def test_parent_attendance_is_limited_to_active_linked_student_and_safe_fields(academic_api_context):
    actor, ids, api_request = academic_api_context

    response = api_request(
        "GET",
        f"/api/parent/children/{ids['linked_student_id']}/attendance?limit=1",
    )
    assert response.status_code == 200
    records = response.json()
    assert len(records) == 1
    assert records[0] == {
        "id": ids["attendance_linked_recent_id"],
        "attendance_date": "2026-11-24",
        "status": "absent",
    }
    assert "remarks" not in records[0]
    assert "marked_by" not in records[0]

    response = api_request(
        "GET",
        f"/api/parent/children/{ids['linked_student_id']}/attendance",
    )
    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [
        ids["attendance_linked_recent_id"],
        ids["attendance_linked_older_id"],
    ]


def test_parent_attendance_rejects_unlinked_inactive_and_cross_school_students(academic_api_context):
    actor, ids, api_request = academic_api_context

    for student_key in (
        "unlinked_student_id",
        "inactive_link_student_id",
        "cross_school_student_id",
    ):
        response = api_request(
            "GET",
            f"/api/parent/children/{ids[student_key]}/attendance",
        )
        assert response.status_code == 404


def test_parent_cannot_use_staff_attendance_crud(academic_api_context):
    actor, ids, api_request = academic_api_context

    response = api_request("GET", "/api/attendance")
    assert response.status_code == 403

    response = api_request(
        "GET",
        f"/api/attendance/{ids['attendance_linked_recent_id']}",
    )
    assert response.status_code == 403




def test_parent_exam_results_are_limited_to_active_linked_student(academic_api_context):
    actor, ids, api_request = academic_api_context

    response = api_request("GET", f"/api/parent/children/{ids['linked_student_id']}/exam-results")
    assert response.status_code == 200
    assert response.json() == [{
        "id": ids["report_linked_id"],
        "exam_id": response.json()[0]["exam_id"],
        "exam_name": "Term 1",
        "subject": "Science",
        "exam_date": "2026-11-18",
        "academic_year": "2026-27",
        "max_marks": 100.0,
        "pass_marks": 35.0,
        "marks_obtained": 82.0,
        "result": "passed",
        "remarks": "Good progress",
    }]

    for student_key in ("unlinked_student_id", "inactive_link_student_id", "cross_school_student_id"):
        denied = api_request("GET", f"/api/parent/children/{ids[student_key]}/exam-results")
        assert denied.status_code == 404


def test_parent_certificate_application_requires_active_link_and_can_be_reviewed(academic_api_context):
    actor, ids, api_request = academic_api_context
    payload = {
        "student_id": ids["linked_student_id"],
        "certificate_type": "bonafide",
        "purpose": "Bank account documentation",
    }
    response = api_request(
        "POST",
        f"/api/parent/children/{ids['linked_student_id']}/certificate-applications",
        payload,
    )
    assert response.status_code == 200
    application = response.json()
    assert application["status"] == "pending"
    assert application["certificate_type"] == "bonafide"
    assert application["school_id"] == ids["school_id"]

    listed = api_request(
        "GET",
        f"/api/parent/children/{ids['linked_student_id']}/certificate-applications",
    )
    assert listed.status_code == 200
    assert [row["id"] for row in listed.json()] == [application["id"]]

    denied = api_request(
        "POST",
        f"/api/parent/children/{ids['unlinked_student_id']}/certificate-applications",
        {**payload, "student_id": ids["unlinked_student_id"]},
    )
    assert denied.status_code == 404

    parent_review = api_request(
        "POST",
        f"/api/certificate-applications/{application['id']}/review",
        {"status": "approved", "reviewer_note": "Approved"},
    )
    assert parent_review.status_code == 403

    actor["user"] = type(actor["user"])(
        id=ids["school_admin_id"], role="admin", school_id=ids["school_id"], is_active=True,
    )
    approved = api_request(
        "POST",
        f"/api/certificate-applications/{application['id']}/review",
        {"status": "approved", "reviewer_note": "Ready for school office collection"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["reviewer_note"] == "Ready for school office collection"

    repeated = api_request(
        "POST",
        f"/api/certificate-applications/{application['id']}/review",
        {"status": "rejected", "reviewer_note": "No"},
    )
    assert repeated.status_code == 409


def test_parent_message_contacts_require_active_link_and_return_only_approved_school_staff(academic_api_context):
    actor, ids, api_request = academic_api_context
    response = api_request("GET", f"/api/parent/children/{ids['linked_student_id']}/message-contacts")
    assert response.status_code == 200
    assert [contact["id"] for contact in response.json()] == [ids["teacher_id"]]
    assert response.json()[0]["role"] == "teacher"

    response = api_request("GET", f"/api/parent/children/{ids['unlinked_student_id']}/message-contacts")
    assert response.status_code == 404

    response = api_request("GET", f"/api/parent/children/{ids['cross_school_student_id']}/message-contacts")
    assert response.status_code == 404



def test_parent_homework_and_timetable_are_linked_student_class_scoped(academic_api_context):
    actor, ids, api_request = academic_api_context

    response = api_request("GET", f"/api/parent/children/{ids['linked_student_id']}/homework")
    assert response.status_code == 200
    homework = response.json()
    assert [item["id"] for item in homework] == [ids["homework_linked_id"]]
    assert homework[0]["subject"] == "Science"
    assert homework[0]["attachment_url"] == "https://school.example.test/plant-cells.pdf"
    assert "assigned_by" not in homework[0]

    response = api_request("GET", f"/api/parent/children/{ids['linked_student_id']}/timetable")
    assert response.status_code == 200
    timetable = response.json()
    assert [item["id"] for item in timetable] == [ids["timetable_linked_id"]]
    assert timetable[0]["subject"] == "Science"
    assert "school_id" not in timetable[0]


def test_parent_homework_and_timetable_reject_unlinked_inactive_and_cross_school_students(academic_api_context):
    actor, ids, api_request = academic_api_context
    for student_key in ("unlinked_student_id", "inactive_link_student_id", "cross_school_student_id"):
        student_id = ids[student_key]
        assert api_request("GET", f"/api/parent/children/{student_id}/homework").status_code == 404
        assert api_request("GET", f"/api/parent/children/{student_id}/timetable").status_code == 404


def test_parent_relationship_governance_is_school_scoped_and_audited(academic_api_context):
    actor, ids, api_request = academic_api_context
    actor["user"] = type(actor["user"])(
        id=ids["school_admin_id"], role="admin", school_id=ids["school_id"], is_active=True,
    )

    listed = api_request("GET", "/api/parent-links?active=true")
    assert listed.status_code == 200
    assert len(listed.json()) == 2
    assert all(row["school_id"] == ids["school_id"] for row in listed.json())
    assert all("guardian_phone" not in row and "aadhaar" not in row for row in listed.json())

    cross_school = api_request("PATCH", "/api/parent-links/999999", {"is_active": False})
    assert cross_school.status_code == 404

    # Deactivate the active link; the parent immediately loses child access.
    link_id = next(row["id"] for row in listed.json()
                   if row["student_id"] == ids["linked_student_id"])
    deactivated = api_request("PATCH", f"/api/parent-links/{link_id}", {"is_active": False})
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False

    actor["user"] = type(actor["user"])(
        id=ids["parent_id"], role="parent", school_id=ids["school_id"], is_active=True,
    )
    children = api_request("GET", "/api/parent/children")
    assert children.status_code == 200
    assert all(row["id"] != ids["linked_student_id"] for row in children.json())
    denied = api_request("GET", f"/api/parent/children/{ids['linked_student_id']}/attendance")
    assert denied.status_code == 404

    actor["user"] = type(actor["user"])(
        id=ids["school_admin_id"], role="admin", school_id=ids["school_id"], is_active=True,
    )
    reactivated = api_request("PATCH", f"/api/parent-links/{link_id}", {"is_active": True})
    assert reactivated.status_code == 200
    assert reactivated.json()["is_active"] is True


def test_parent_relationship_governance_rejects_invalid_updates_and_tenant_escape(academic_api_context):
    actor, ids, api_request = academic_api_context
    actor["user"] = type(actor["user"])(
        id=ids["school_admin_id"], role="admin", school_id=ids["school_id"], is_active=True,
    )
    link_list = api_request("GET", "/api/parent-links")
    link_id = next(row["id"] for row in link_list.json()
                   if row["student_id"] == ids["linked_student_id"])

    invalid = api_request("PATCH", f"/api/parent-links/{link_id}", {"is_active": "false"})
    assert invalid.status_code == 422
    extra = api_request("PATCH", f"/api/parent-links/{link_id}", {"parent_user_id": ids["other_parent_id"]})
    assert extra.status_code == 422
    blank = api_request("PATCH", f"/api/parent-links/{link_id}", {"relationship": "  "})
    assert blank.status_code == 422

    # An administrator from another tenant cannot enumerate or change this link.
    actor["user"] = type(actor["user"])(
        id=ids["school_admin_id"], role="admin", school_id=ids["other_school_id"], is_active=True,
    )
    denied = api_request("PATCH", f"/api/parent-links/{link_id}", {"is_active": False})
    assert denied.status_code == 404
    wrong_school_list = api_request("GET", f"/api/parent-links?school_id={ids['school_id']}")
    assert wrong_school_list.status_code == 404
