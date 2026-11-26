"""Parent-facing transport and hostel assignment/request workflows.

Parents can read only active linked-student allocations and submit requests.
Only authorized school staff can review requests and change official allocations.
"""
import json
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .database import Base, get_db
from . import models
from .security import current_user, require_roles

router = APIRouter(tags=["parent transport and hostel"])


class StudentTransportAssignment(Base):
    __tablename__ = "student_transport_assignments"
    __table_args__ = (UniqueConstraint("school_id", "student_id", name="uq_transport_assignment_school_student"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    route_name: Mapped[str] = mapped_column(String(120), default="")
    pickup_point: Mapped[str] = mapped_column(String(180), default="")
    drop_point: Mapped[str] = mapped_column(String(180), default="")
    pickup_time: Mapped[str] = mapped_column(String(10), default="")
    drop_time: Mapped[str] = mapped_column(String(10), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StudentHostelAssignment(Base):
    __tablename__ = "student_hostel_assignments"
    __table_args__ = (UniqueConstraint("school_id", "student_id", name="uq_hostel_assignment_school_student"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    hostel_id: Mapped[int | None] = mapped_column(ForeignKey("hostels.id"), nullable=True)
    room_no: Mapped[str] = mapped_column(String(40), default="")
    bed_no: Mapped[str] = mapped_column(String(40), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ParentFacilityRequest(Base):
    __tablename__ = "parent_facility_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    parent_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    facility_type: Mapped[str] = mapped_column(String(20), index=True)
    request_type: Mapped[str] = mapped_column(String(40))
    reason: Mapped[str] = mapped_column(String(500))
    details_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewer_note: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class FacilityRequestIn(BaseModel):
    facility_type: Literal["transport", "hostel"]
    request_type: str = Field(min_length=3, max_length=40)
    reason: str = Field(min_length=5, max_length=500)
    details: dict[str, str | int | None] = Field(default_factory=dict)


class FacilityReviewIn(BaseModel):
    status: Literal["approved", "rejected"]
    reviewer_note: str = Field(default="", max_length=500)


def _parent_link(db: Session, user: models.User, student_id: int):
    link = db.scalar(select(models.ParentStudentLink).where(
        models.ParentStudentLink.parent_user_id == user.id,
        models.ParentStudentLink.student_id == student_id,
        models.ParentStudentLink.school_id == user.school_id,
        models.ParentStudentLink.is_active.is_(True),
    ))
    if not link:
        raise HTTPException(status_code=404, detail="Student not found")
    student = db.scalar(select(models.Student).where(
        models.Student.id == student_id,
        models.Student.school_id == user.school_id,
    ))
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


def _audit(db: Session, user: models.User, event: str, target: str, target_id: int, details: dict):
    db.add(models.AuditLog(
        actor_user_id=user.id,
        event_type=event,
        target_type=target,
        target_id=str(target_id),
        details=json.dumps(details, separators=(",", ":"), sort_keys=True),
    ))


def _facility_payload(db: Session, student: models.Student):
    transport = db.scalar(select(StudentTransportAssignment).where(
        StudentTransportAssignment.school_id == student.school_id,
        StudentTransportAssignment.student_id == student.id,
        StudentTransportAssignment.is_active.is_(True),
    ))
    hostel = db.scalar(select(StudentHostelAssignment).where(
        StudentHostelAssignment.school_id == student.school_id,
        StudentHostelAssignment.student_id == student.id,
        StudentHostelAssignment.is_active.is_(True),
    ))
    vehicle = db.scalar(select(models.Vehicle).where(
        models.Vehicle.id == transport.vehicle_id, models.Vehicle.school_id == student.school_id,
    )) if transport and transport.vehicle_id else None
    hostel_record = db.scalar(select(models.Hostel).where(
        models.Hostel.id == hostel.hostel_id, models.Hostel.school_id == student.school_id,
    )) if hostel and hostel.hostel_id else None
    return {
        "transport": ({
            "route_name": transport.route_name or (vehicle.route_name if vehicle else ""),
            "vehicle_registration": vehicle.registration_no if vehicle else None,
            "vehicle_type": vehicle.vehicle_type if vehicle else None,
            "pickup_point": transport.pickup_point,
            "drop_point": transport.drop_point,
            "pickup_time": transport.pickup_time,
            "drop_time": transport.drop_time,
        } if transport else None),
        "hostel": ({
            "hostel_name": hostel_record.name if hostel_record else None,
            "building": hostel_record.building if hostel_record else "",
            "room_no": hostel.room_no or (hostel_record.room_no if hostel_record else ""),
            "bed_no": hostel.bed_no,
            "warden_name": hostel_record.warden_name if hostel_record else "",
        } if hostel else None),
    }


@router.get("/api/parent/children/{student_id}/facilities")
def parent_facilities(
    student_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("parent")),
):
    student = _parent_link(db, user, student_id)
    return _facility_payload(db, student)


@router.get("/api/parent/children/{student_id}/facility-requests")
def parent_facility_requests(
    student_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("parent")),
):
    _parent_link(db, user, student_id)
    rows = db.scalars(select(ParentFacilityRequest).where(
        ParentFacilityRequest.school_id == user.school_id,
        ParentFacilityRequest.student_id == student_id,
        ParentFacilityRequest.parent_user_id == user.id,
    ).order_by(ParentFacilityRequest.created_at.desc())).all()
    return [{
        "id": row.id, "facility_type": row.facility_type, "request_type": row.request_type,
        "reason": row.reason, "details": json.loads(row.details_json or "{}"),
        "status": row.status, "reviewer_note": row.reviewer_note,
        "created_at": row.created_at, "reviewed_at": row.reviewed_at,
    } for row in rows]


@router.post("/api/parent/children/{student_id}/facility-requests", status_code=201)
def create_parent_facility_request(
    student_id: int,
    payload: FacilityRequestIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("parent")),
):
    _parent_link(db, user, student_id)
    allowed_types = {
        "transport": {"new_allocation", "route_change", "pickup_change", "drop_change", "discontinue"},
        "hostel": {"new_allocation", "room_change", "bed_change", "discontinue"},
    }
    if payload.request_type not in allowed_types[payload.facility_type]:
        raise HTTPException(status_code=422, detail="Unsupported facility request type")
    row = ParentFacilityRequest(
        school_id=user.school_id, student_id=student_id, parent_user_id=user.id,
        facility_type=payload.facility_type, request_type=payload.request_type,
        reason=payload.reason.strip(), details_json=json.dumps(payload.details),
    )
    db.add(row)
    db.flush()
    _audit(db, user, "parent_facility_request_submitted", "parent_facility_request", row.id,
           {"facility_type": row.facility_type, "request_type": row.request_type, "student_id": student_id})
    db.commit()
    db.refresh(row)
    return {"id": row.id, "status": row.status, "facility_type": row.facility_type,
            "request_type": row.request_type, "created_at": row.created_at}


@router.get("/api/facility-requests")
def list_facility_requests(
    facility_type: Literal["transport", "hostel"],
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("admin", "principal", "vice_principal", "transport_manager", "hostel_warden")),
):
    if not user.school_id:
        raise HTTPException(status_code=403, detail="School staff account required")
    permitted = ({"admin", "principal", "vice_principal", "transport_manager"} if facility_type == "transport"
                 else {"admin", "principal", "vice_principal", "hostel_warden"})
    if user.role not in permitted:
        raise HTTPException(status_code=403, detail="Not authorized to review this facility")
    rows = db.scalars(select(ParentFacilityRequest).where(
        ParentFacilityRequest.school_id == user.school_id,
        ParentFacilityRequest.facility_type == facility_type,
    ).order_by(ParentFacilityRequest.created_at.desc())).all()
    return [{
        "id": row.id, "student_id": row.student_id, "parent_user_id": row.parent_user_id,
        "facility_type": row.facility_type, "request_type": row.request_type,
        "reason": row.reason, "details": json.loads(row.details_json or "{}"),
        "status": row.status, "reviewer_note": row.reviewer_note, "created_at": row.created_at,
    } for row in rows]


@router.post("/api/facility-requests/{request_id}/review")
def review_facility_request(
    request_id: int,
    decision: FacilityReviewIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("admin", "principal", "vice_principal", "transport_manager", "hostel_warden")),
):
    if not user.school_id:
        raise HTTPException(status_code=403, detail="School staff account required")
    row = db.scalar(select(ParentFacilityRequest).where(
        ParentFacilityRequest.id == request_id,
        ParentFacilityRequest.school_id == user.school_id,
    ))
    if not row:
        raise HTTPException(status_code=404, detail="Request not found")
    permitted = ({"admin", "principal", "vice_principal", "transport_manager"} if row.facility_type == "transport"
                 else {"admin", "principal", "vice_principal", "hostel_warden"})
    if user.role not in permitted:
        raise HTTPException(status_code=403, detail="Not authorized to review this facility")
    if row.status != "pending":
        raise HTTPException(status_code=409, detail="Request has already been reviewed")
    student = db.scalar(select(models.Student).where(
        models.Student.id == row.student_id, models.Student.school_id == user.school_id,
    ))
    if not student:
        raise HTTPException(status_code=404, detail="Request not found")

    details = json.loads(row.details_json or "{}")
    if decision.status == "approved":
        if row.facility_type == "transport":
            assignment = db.scalar(select(StudentTransportAssignment).where(
                StudentTransportAssignment.school_id == user.school_id,
                StudentTransportAssignment.student_id == row.student_id,
            ))
            if assignment is None:
                assignment = StudentTransportAssignment(school_id=user.school_id, student_id=row.student_id)
                db.add(assignment)
            if row.request_type == "discontinue":
                assignment.is_active = False
            else:
                vehicle_id = details.get("vehicle_id")
                if vehicle_id is not None:
                    try:
                        vehicle_id = int(vehicle_id)
                    except (TypeError, ValueError):
                        raise HTTPException(status_code=422, detail="Vehicle ID must be a valid number")
                    vehicle = db.scalar(select(models.Vehicle).where(
                        models.Vehicle.id == vehicle_id, models.Vehicle.school_id == user.school_id,
                        models.Vehicle.status == "active",
                    ))
                    if not vehicle:
                        raise HTTPException(status_code=422, detail="Selected vehicle is not available in this school")
                    assignment.vehicle_id = vehicle.id
                    assignment.route_name = vehicle.route_name
                field_limits = {"route_name": 120, "pickup_point": 180, "drop_point": 180,
                                "pickup_time": 10, "drop_time": 10}
                for key, max_length in field_limits.items():
                    if key in details and details[key] is not None:
                        setattr(assignment, key, str(details[key]).strip()[:max_length])
                assignment.is_active = True
        else:
            assignment = db.scalar(select(StudentHostelAssignment).where(
                StudentHostelAssignment.school_id == user.school_id,
                StudentHostelAssignment.student_id == row.student_id,
            ))
            if assignment is None:
                assignment = StudentHostelAssignment(school_id=user.school_id, student_id=row.student_id)
                db.add(assignment)
            if row.request_type == "discontinue":
                assignment.is_active = False
            else:
                hostel_id = details.get("hostel_id")
                if hostel_id is not None:
                    try:
                        hostel_id = int(hostel_id)
                    except (TypeError, ValueError):
                        raise HTTPException(status_code=422, detail="Hostel ID must be a valid number")
                    hostel_record = db.scalar(select(models.Hostel).where(
                        models.Hostel.id == hostel_id, models.Hostel.school_id == user.school_id,
                        models.Hostel.status == "active",
                    ))
                    if not hostel_record:
                        raise HTTPException(status_code=422, detail="Selected hostel is not available in this school")
                    assignment.hostel_id = hostel_record.id
                for key in ("room_no", "bed_no"):
                    if key in details and details[key] is not None:
                        setattr(assignment, key, str(details[key])[:40])
                assignment.is_active = True

    row.status = decision.status
    row.reviewed_by = user.id
    row.reviewer_note = decision.reviewer_note.strip()
    row.reviewed_at = datetime.utcnow()
    _audit(db, user, "parent_facility_request_reviewed", "parent_facility_request", row.id,
           {"facility_type": row.facility_type, "status": row.status, "student_id": row.student_id})
    if decision.status == "approved":
        _audit(db, user, "student_facility_assignment_updated", f"{row.facility_type}_assignment", row.student_id,
               {"request_id": row.id, "student_id": row.student_id})
    db.commit()
    return {"id": row.id, "status": row.status, "reviewed_at": row.reviewed_at}
