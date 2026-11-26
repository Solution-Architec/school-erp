from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app import models
from backend.app.database import Base
from backend.app.notifications import NotificationReminderDispatch, SchoolNotification, SchoolReminderSettings
from backend.app.reminder_worker import process_due_reminders


def test_parent_reminder_worker_generates_fee_and_absence_alerts_once():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    today = date(2026, 11, 26)
    fixed_now = datetime(2026, 11, 26, 9, 0, tzinfo=timezone.utc)

    with SessionLocal() as db:
        school = models.School(name="Reminder School", code="REMIND-1")
        db.add(school)
        db.flush()
        admin = models.User(name="School Admin", email="reminder-admin@example.test",
                            password_hash="x", role="admin", school_id=school.id)
        parent = models.User(name="Parent", email="reminder-parent@example.test",
                             password_hash="x", role="parent", school_id=school.id)
        student = models.Student(school_id=school.id, admission_no="R-1",
                                 full_name="Reminder Student", class_name="5", section="A")
        db.add_all([admin, parent, student])
        db.flush()
        db.add(models.ParentStudentLink(school_id=school.id, parent_user_id=parent.id,
                                        student_id=student.id, is_active=True))
        fee = models.StudentFee(
            school_id=school.id, student_id=student.id, category="Tuition",
            description="Term fee", academic_year="2026-27", term="term-1",
            total_amount=Decimal("1200.00"), discount=Decimal("200.00"),
            due_date=today + timedelta(days=2), status="partial",
        )
        db.add(fee)
        db.flush()
        db.add(models.FeePayment(
            school_id=school.id, student_fee_id=fee.id, receipt_no="REM-REC-1",
            amount=Decimal("250.00"), payment_method="cash",
            transaction_reference="", notes="", received_by=admin.id,
        ))
        db.add(models.AttendanceRecord(
            school_id=school.id, student_id=student.id, attendance_date=today,
            status="absent", remarks="", marked_by=admin.id,
        ))
        db.add(SchoolReminderSettings(
            school_id=school.id, fee_reminders_enabled=True,
            fee_reminder_days_before=3, absence_alerts_enabled=True, timezone="UTC",
        ))
        db.commit()

        first = process_due_reminders(db, now=fixed_now)
        second = process_due_reminders(db, now=fixed_now)
        rows = db.scalars(select(SchoolNotification).order_by(SchoolNotification.category)).all()
        assert first == {"fees": 1, "attendance": 1}
        assert second == {"fees": 0, "attendance": 0}
        assert len(rows) == 2
        fee_notice = next(row for row in rows if row.category == "fees")
        assert "₹750.00" in fee_notice.body
        assert fee_notice.created_by is None
        assert db.scalar(select(func.count(NotificationReminderDispatch.id))) == 2

    Base.metadata.drop_all(bind=engine)
    engine.dispose()
