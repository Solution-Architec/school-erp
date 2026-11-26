"""Idempotent in-app parent reminder worker.

Runs independently from the API process. Only creates reminders; parent delivery
eligibility is still resolved by the inbox against active parent-student links.
"""
from __future__ import annotations

import logging
import os
import time
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from .database import Base, SessionLocal, engine
from . import models
from .notifications import (
    NotificationReminderDispatch,
    SchoolNotification,
    SchoolReminderSettings,
)

logger = logging.getLogger("parent_reminder_worker")


def _school_today(timezone_name: str, now: datetime | None = None) -> date:
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        zone = ZoneInfo("Asia/Kolkata")
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(zone).date()


def _already_dispatched(db, dedupe_key: str) -> bool:
    return db.scalar(select(NotificationReminderDispatch.id).where(
        NotificationReminderDispatch.dedupe_key == dedupe_key
    )) is not None


def _save_reminder(db, *, setting, student, category: str, title: str,
                   body: str, dedupe_key: str, reference_type: str,
                   reference_id: int) -> bool:
    if _already_dispatched(db, dedupe_key):
        return False
    notification = SchoolNotification(
        school_id=setting.school_id,
        created_by=None,
        title=title,
        body=body,
        category=category,
        audience="student",
        student_id=student.id,
        is_published=True,
    )
    db.add(notification)
    db.flush()
    db.add(NotificationReminderDispatch(
        school_id=setting.school_id,
        reference_type=reference_type,
        reference_id=reference_id,
        dedupe_key=dedupe_key,
        notification_id=notification.id,
    ))
    db.add(models.AuditLog(
        actor_user_id=None,
        event_type="notification.reminder_generated",
        target_type=reference_type,
        target_id=str(reference_id),
        details=f"school_id={setting.school_id}; category={category}; dedupe_key={dedupe_key}",
    ))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return False
    return True


def process_due_reminders(db, *, now: datetime | None = None) -> dict[str, int]:
    """Generate due-fee and same-day absence notices once per source event."""
    generated = {"fees": 0, "attendance": 0}
    settings_rows = db.scalars(select(SchoolReminderSettings)).all()
    for setting in settings_rows:
        today = _school_today(setting.timezone, now)

        if setting.fee_reminders_enabled:
            last_due_date = today + timedelta(days=setting.fee_reminder_days_before)
            fees = db.execute(
                select(models.StudentFee, models.Student)
                .join(models.Student, models.Student.id == models.StudentFee.student_id)
                .where(
                    models.StudentFee.school_id == setting.school_id,
                    models.Student.school_id == setting.school_id,
                    models.StudentFee.due_date.is_not(None),
                    models.StudentFee.due_date >= today,
                    models.StudentFee.due_date <= last_due_date,
                )
            ).all()
            for fee, student in fees:
                paid = db.scalar(select(func.coalesce(func.sum(models.FeePayment.amount), 0)).where(
                    models.FeePayment.student_fee_id == fee.id,
                    models.FeePayment.school_id == setting.school_id,
                )) or Decimal("0")
                balance = Decimal(str(fee.total_amount or 0)) - Decimal(str(fee.discount or 0)) - Decimal(str(paid))
                if balance <= 0:
                    continue
                due = fee.due_date.isoformat()
                dedupe = f"fee:{fee.id}:due:{due}"
                if _save_reminder(
                    db, setting=setting, student=student, category="fees",
                    title="Upcoming school fee due date",
                    body=f"{fee.category} fee has an outstanding balance of ₹{balance:.2f}. Due date: {due}.",
                    dedupe_key=dedupe, reference_type="student_fee",
                    reference_id=fee.id,
                ):
                    generated["fees"] += 1

        if setting.absence_alerts_enabled:
            absences = db.execute(
                select(models.AttendanceRecord, models.Student)
                .join(models.Student, models.Student.id == models.AttendanceRecord.student_id)
                .where(
                    models.AttendanceRecord.school_id == setting.school_id,
                    models.Student.school_id == setting.school_id,
                    models.AttendanceRecord.attendance_date == today,
                    func.lower(models.AttendanceRecord.status) == "absent",
                )
            ).all()
            for attendance, student in absences:
                dedupe = f"attendance:{attendance.id}:absent"
                if _save_reminder(
                    db, setting=setting, student=student, category="attendance",
                    title="Student marked absent",
                    body=f"{student.full_name} was marked absent on {today.isoformat()}. Contact the school if this is unexpected.",
                    dedupe_key=dedupe, reference_type="attendance_record",
                    reference_id=attendance.id,
                ):
                    generated["attendance"] += 1

    return generated


def main() -> None:
    Base.metadata.create_all(bind=engine)
    if engine.dialect.name == "postgresql":
        with engine.begin() as connection:
            connection.execute(__import__("sqlalchemy").text(
                "ALTER TABLE school_notifications ALTER COLUMN created_by DROP NOT NULL"
            ))
    interval = max(60, int(os.getenv("REMINDER_POLL_SECONDS", "900")))
    logger.info("Parent reminder worker started; poll interval=%s seconds", interval)
    while True:
        try:
            with SessionLocal() as db:
                counts = process_due_reminders(db)
                if sum(counts.values()):
                    logger.info("Generated parent reminders: %s", counts)
        except Exception:
            logger.exception("Parent reminder cycle failed")
        time.sleep(interval)


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    main()
