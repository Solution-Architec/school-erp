from datetime import date
import pytest
from pydantic import ValidationError

from app.schemas import HomeworkIn, StudentLeaveIn, StudentLeaveReviewIn, ParentTeacherMessageIn


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
