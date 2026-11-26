"""School announcements and parent notification inbox.

Notifications are stored in-app first. Parent visibility is resolved at read time
from active parent-student links, so revoked links lose access immediately.
"""
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .database import Base, get_db
from . import models
from .security import current_user, require_module_permission

router = APIRouter(tags=["notifications"])


class SchoolNotification(Base):
    __tablename__ = "school_notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(30), default="announcement", index=True)
    audience: Mapped[str] = mapped_column(String(20), default="school", index=True)
    class_name: Mapped[str] = mapped_column(String(80), default="")
    section: Mapped[str] = mapped_column(String(40), default="")
    student_id: Mapped[int | None] = mapped_column(ForeignKey("students.id"), nullable=True, index=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class NotificationRead(Base):
    __tablename__ = "notification_reads"
    __table_args__ = (UniqueConstraint("notification_id", "parent_user_id", name="uq_notification_parent_read"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    notification_id: Mapped[int] = mapped_column(ForeignKey("school_notifications.id"), nullable=False, index=True)
    parent_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    read_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (UniqueConstraint("parent_user_id", name="uq_notification_preference_parent"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    parent_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    announcement: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    attendance: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    homework: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    examination: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    fees: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    general: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SchoolReminderSettings(Base):
    __tablename__ = "school_reminder_settings"
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, unique=True, index=True)
    fee_reminders_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    fee_reminder_days_before: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    absence_alerts_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NotificationReminderDispatch(Base):
    __tablename__ = "notification_reminder_dispatches"
    __table_args__ = (UniqueConstraint("dedupe_key", name="uq_notification_reminder_dedupe"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    reference_type: Mapped[str] = mapped_column(String(40), nullable=False)
    reference_id: Mapped[int] = mapped_column(Integer, nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    notification_id: Mapped[int] = mapped_column(ForeignKey("school_notifications.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class NotificationCreate(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    body: str = Field(min_length=3, max_length=5000)
    category: Literal["announcement", "attendance", "homework", "examination", "fees", "general"] = "announcement"
    audience: Literal["school", "class", "student"] = "school"
    class_name: str = Field(default="", max_length=80)
    section: str = Field(default="", max_length=40)
    student_id: int | None = None
    is_published: bool = True


class SchoolReminderSettingsUpdate(BaseModel):
    fee_reminders_enabled: bool | None = None
    fee_reminder_days_before: int | None = Field(default=None, ge=0, le=30)
    absence_alerts_enabled: bool | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=64)


def _reminder_settings_payload(row: SchoolReminderSettings | None) -> dict:
    return {
        "fee_reminders_enabled": row.fee_reminders_enabled if row else True,
        "fee_reminder_days_before": row.fee_reminder_days_before if row else 3,
        "absence_alerts_enabled": row.absence_alerts_enabled if row else True,
        "timezone": row.timezone if row else "Asia/Kolkata",
    }


class NotificationPreferenceUpdate(BaseModel):
    in_app_enabled: bool | None = None
    announcement: bool | None = None
    attendance: bool | None = None
    homework: bool | None = None
    examination: bool | None = None
    fees: bool | None = None
    general: bool | None = None


PREFERENCE_FIELDS = (
    "in_app_enabled", "announcement", "attendance", "homework",
    "examination", "fees", "general",
)


def _preference_payload(row: NotificationPreference | None) -> dict:
    return {field: getattr(row, field, True) if row else True for field in PREFERENCE_FIELDS}


STAFF_ROLES = {"admin", "principal", "vice_principal", "user"}


def _school_staff(user):
    if user.role not in STAFF_ROLES or not user.school_id:
        raise HTTPException(status_code=403, detail="School staff access required")
    return int(user.school_id)


def _linked_students(db: Session, user):
    return db.execute(
        select(models.Student)
        .join(models.ParentStudentLink, models.ParentStudentLink.student_id == models.Student.id)
        .where(
            models.ParentStudentLink.parent_user_id == user.id,
            models.ParentStudentLink.school_id == user.school_id,
            models.ParentStudentLink.is_active.is_(True),
            models.Student.school_id == user.school_id,
        )
        .order_by(models.Student.full_name.asc())
    ).scalars().all()


def _eligible(notification: SchoolNotification, students: list[models.Student]) -> list[models.Student]:
    if notification.audience == "school":
        return students
    if notification.audience == "student":
        return [student for student in students if student.id == notification.student_id]
    return [
        student for student in students
        if student.class_name == notification.class_name
        and (not notification.section or student.section == notification.section)
    ]


@router.get("/api/school/notifications")
def list_school_notifications(db: Session = Depends(get_db), user=Depends(require_module_permission("notifications", "View", *STAFF_ROLES))):
    school_id = _school_staff(user)
    rows = db.scalars(
        select(SchoolNotification)
        .where(SchoolNotification.school_id == school_id)
        .order_by(SchoolNotification.created_at.desc())
        .limit(200)
    ).all()
    return [{
        "id": row.id, "title": row.title, "body": row.body, "category": row.category,
        "audience": row.audience, "class_name": row.class_name, "section": row.section,
        "student_id": row.student_id, "is_published": row.is_published,
        "published_at": row.published_at, "created_at": row.created_at,
    } for row in rows]


@router.post("/api/school/notifications", status_code=201)
def create_school_notification(payload: NotificationCreate, db: Session = Depends(get_db), user=Depends(require_module_permission("notifications", "Create", *STAFF_ROLES))):
    school_id = _school_staff(user)
    class_name = payload.class_name.strip()
    section = payload.section.strip()
    student_id = payload.student_id
    if payload.audience == "class" and not class_name:
        raise HTTPException(status_code=422, detail="Class is required for class-targeted notifications")
    if payload.audience == "student":
        student = db.get(models.Student, student_id) if student_id else None
        if not student or student.school_id != school_id:
            raise HTTPException(status_code=404, detail="Student not found in this school")
    else:
        student_id = None
    row = SchoolNotification(
        school_id=school_id, created_by=user.id, title=payload.title.strip(),
        body=payload.body.strip(), category=payload.category, audience=payload.audience,
        class_name=class_name, section=section, student_id=student_id,
        is_published=payload.is_published,
    )
    db.add(row)
    db.flush()
    db.add(models.AuditLog(
        actor_user_id=user.id, event_type="notification.published" if row.is_published else "notification.drafted",
        target_type="school_notification", target_id=str(row.id),
        details=f"school_id={school_id}; audience={row.audience}; category={row.category}",
    ))
    db.commit()
    db.refresh(row)
    return {"id": row.id, "title": row.title, "body": row.body, "category": row.category,
            "audience": row.audience, "class_name": row.class_name, "section": row.section,
            "student_id": row.student_id, "is_published": row.is_published,
            "published_at": row.published_at, "created_at": row.created_at}


@router.get("/api/school/parent-reminder-settings")
def get_school_parent_reminder_settings(db: Session = Depends(get_db), user=Depends(require_module_permission("notifications", "View", *STAFF_ROLES))):
    if user.role not in {"admin", "principal", "vice_principal"} or not user.school_id:
        raise HTTPException(status_code=403, detail="School leadership access required")
    row = db.scalar(select(SchoolReminderSettings).where(
        SchoolReminderSettings.school_id == user.school_id
    ))
    return _reminder_settings_payload(row)


@router.patch("/api/school/parent-reminder-settings")
def update_school_parent_reminder_settings(
    payload: SchoolReminderSettingsUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_module_permission("notifications", "Edit", *STAFF_ROLES)),
):
    if user.role not in {"admin", "principal", "vice_principal"} or not user.school_id:
        raise HTTPException(status_code=403, detail="School leadership access required")
    changes = payload.model_dump(exclude_unset=True)
    if not changes or any(value is None for value in changes.values()):
        raise HTTPException(status_code=422, detail="Provide valid reminder settings")
    if "timezone" in changes:
        try:
            ZoneInfo(changes["timezone"])
        except (ZoneInfoNotFoundError, TypeError):
            raise HTTPException(status_code=422, detail="Use a valid IANA timezone, such as Asia/Kolkata")
    row = db.scalar(select(SchoolReminderSettings).where(
        SchoolReminderSettings.school_id == user.school_id
    ))
    if row is None:
        row = SchoolReminderSettings(school_id=user.school_id)
        db.add(row)
    for field, value in changes.items():
        setattr(row, field, value)
    db.flush()
    db.add(models.AuditLog(
        actor_user_id=user.id,
        event_type="notification.reminder_settings.updated",
        target_type="school_reminder_settings",
        target_id=str(row.id),
        details=f"school_id={user.school_id}; fields={','.join(sorted(changes))}",
    ))
    db.commit()
    db.refresh(row)
    return _reminder_settings_payload(row)


@router.get("/api/parent/notifications")
def list_parent_notifications(db: Session = Depends(get_db), user=Depends(require_module_permission("parent-portal", "View", "parent"))):
    if user.role != "parent" or not user.school_id:
        raise HTTPException(status_code=403, detail="Parent access required")
    students = _linked_students(db, user)
    if not students:
        return []
    rows = db.scalars(
        select(SchoolNotification)
        .where(
            SchoolNotification.school_id == user.school_id,
            SchoolNotification.is_published.is_(True),
        )
        .order_by(SchoolNotification.published_at.desc(), SchoolNotification.id.desc())
        .limit(300)
    ).all()
    read_ids = set(db.scalars(
        select(NotificationRead.notification_id).where(NotificationRead.parent_user_id == user.id)
    ).all())
    preferences = db.scalar(select(NotificationPreference).where(
        NotificationPreference.parent_user_id == user.id,
        NotificationPreference.school_id == user.school_id,
    ))
    if preferences and not preferences.in_app_enabled:
        return []
    result = []
    for row in rows:
        if preferences and not getattr(preferences, row.category, True):
            continue
        matched = _eligible(row, students)
        if not matched:
            continue
        result.append({
            "id": row.id, "title": row.title, "body": row.body, "category": row.category,
            "audience": row.audience, "published_at": row.published_at,
            "is_read": row.id in read_ids,
            "students": [{"id": student.id, "full_name": student.full_name,
                          "class_name": student.class_name, "section": student.section}
                         for student in matched],
        })
    return result


@router.post("/api/parent/notifications/{notification_id}/read")
def mark_parent_notification_read(notification_id: int, db: Session = Depends(get_db), user=Depends(require_module_permission("parent-portal", "Edit", "parent"))):
    if user.role != "parent" or not user.school_id:
        raise HTTPException(status_code=403, detail="Parent access required")
    row = db.scalar(select(SchoolNotification).where(
        SchoolNotification.id == notification_id,
        SchoolNotification.school_id == user.school_id,
        SchoolNotification.is_published.is_(True),
    ))
    if not row:
        raise HTTPException(status_code=404, detail="Notification not found")
    students = _linked_students(db, user)
    if not _eligible(row, students):
        raise HTTPException(status_code=404, detail="Notification not found")
    receipt = db.scalar(select(NotificationRead).where(
        NotificationRead.notification_id == row.id,
        NotificationRead.parent_user_id == user.id,
    ))
    if not receipt:
        db.add(NotificationRead(notification_id=row.id, parent_user_id=user.id))
        db.add(models.AuditLog(
            actor_user_id=user.id, event_type="notification.read",
            target_type="school_notification", target_id=str(row.id),
            details=f"school_id={user.school_id}",
        ))
        db.commit()
    return {"notification_id": row.id, "is_read": True}


@router.get("/api/parent/notification-preferences")
def get_parent_notification_preferences(db: Session = Depends(get_db), user=Depends(require_module_permission("parent-portal", "View", "parent"))):
    if user.role != "parent" or not user.school_id:
        raise HTTPException(status_code=403, detail="Parent access required")
    row = db.scalar(select(NotificationPreference).where(
        NotificationPreference.parent_user_id == user.id,
        NotificationPreference.school_id == user.school_id,
    ))
    return _preference_payload(row)


@router.patch("/api/parent/notification-preferences")
def update_parent_notification_preferences(
    payload: NotificationPreferenceUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_module_permission("parent-portal", "Edit", "parent")),
):
    if user.role != "parent" or not user.school_id:
        raise HTTPException(status_code=403, detail="Parent access required")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="Provide at least one notification preference")
    if any(value is None for value in changes.values()):
        raise HTTPException(status_code=422, detail="Notification preferences must be true or false")
    row = db.scalar(select(NotificationPreference).where(
        NotificationPreference.parent_user_id == user.id,
        NotificationPreference.school_id == user.school_id,
    ))
    if row is None:
        row = NotificationPreference(parent_user_id=user.id, school_id=user.school_id)
        db.add(row)
    for field, value in changes.items():
        setattr(row, field, value)
    db.flush()
    db.add(models.AuditLog(
        actor_user_id=user.id,
        event_type="notification.preferences.updated",
        target_type="notification_preference",
        target_id=str(row.id),
        details=f"school_id={user.school_id}; fields={','.join(sorted(changes))}",
    ))
    db.commit()
    db.refresh(row)
    return _preference_payload(row)


def create_event_notification(
    db: Session,
    *,
    school_id: int,
    actor_user_id: int,
    title: str,
    body: str,
    category: Literal["attendance", "homework", "examination", "fees", "general"],
    student_id: int | None = None,
    class_name: str = "",
    section: str = "",
) -> SchoolNotification:
    """Queue an in-app alert in the caller's transaction.

    Parent recipients are deliberately not snapshotted: inbox visibility is
    evaluated against active same-school parent-student links at read time.
    """
    audience = "student" if student_id is not None else "class"
    row = SchoolNotification(
        school_id=school_id,
        created_by=actor_user_id,
        title=title[:180],
        body=body[:5000],
        category=category,
        audience=audience,
        class_name=class_name[:80],
        section=section[:40],
        student_id=student_id,
        is_published=True,
    )
    db.add(row)
    db.flush()
    db.add(models.AuditLog(
        actor_user_id=actor_user_id,
        event_type="notification.event_generated",
        target_type="school_notification",
        target_id=str(row.id),
        details=f"school_id={school_id}; audience={audience}; category={category}",
    ))
    return row
