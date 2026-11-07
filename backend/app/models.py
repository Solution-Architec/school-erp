from datetime import datetime, date
from sqlalchemy import String, Integer, Date, DateTime, Boolean, ForeignKey, Text, Numeric, text
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base
from sqlalchemy import UniqueConstraint, CheckConstraint, Index




class School(Base):
    __tablename__ = "schools"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    # Existing schools remain approved; public self-registration starts pending.
    approval_status: Mapped[str] = mapped_column(String(20), default="approved", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(40), default="admin")
    position: Mapped[str] = mapped_column(String(80), default="Principal")
    school_id: Mapped[int | None] = mapped_column(ForeignKey("schools.id"), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=True)
    approval_status: Mapped[str] = mapped_column(String(20), default="approved")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class AuthCode(Base):
    __tablename__ = "auth_codes"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    purpose: Mapped[str] = mapped_column(String(20), index=True)
    code_hash: Mapped[str] = mapped_column(String(255))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Student(Base):
    __tablename__ = "students"
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    __table_args__ = (UniqueConstraint("school_id", "admission_no", name="uq_student_school_admission"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    admission_no: Mapped[str] = mapped_column(String(80), index=True)
    full_name: Mapped[str] = mapped_column(String(180), index=True)
    class_name: Mapped[str] = mapped_column(String(80), default="")
    section: Mapped[str] = mapped_column(String(40), default="")
    guardian_name: Mapped[str] = mapped_column(String(180), default="")
    guardian_phone: Mapped[str] = mapped_column(String(40), default="")
    email: Mapped[str] = mapped_column(String(255), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    transport_required: Mapped[bool] = mapped_column(Boolean, default=False)
    hostel_required: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(30), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Staff(Base):
    __tablename__ = "staff"
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    __table_args__ = (UniqueConstraint("school_id", "employee_no", name="uq_staff_school_employee"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_no: Mapped[str] = mapped_column(String(80), index=True)
    full_name: Mapped[str] = mapped_column(String(180), index=True)
    designation: Mapped[str] = mapped_column(String(100), default="")
    department: Mapped[str] = mapped_column(String(100), default="")
    phone: Mapped[str] = mapped_column(String(40), default="")
    email: Mapped[str] = mapped_column(String(255), default="")
    salary: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    status: Mapped[str] = mapped_column(String(30), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class SchoolClass(Base):
    __tablename__ = "classes"
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), index=True)
    section: Mapped[str] = mapped_column(String(40), default="A")
    academic_year: Mapped[str] = mapped_column(String(20), default="")
    class_teacher: Mapped[str] = mapped_column(String(180), default="")
    capacity: Mapped[int] = mapped_column(Integer, default=40)

class Vehicle(Base):
    __tablename__ = "vehicles"
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    __table_args__ = (UniqueConstraint("school_id", "registration_no", name="uq_vehicle_school_registration"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    registration_no: Mapped[str] = mapped_column(String(80), index=True)
    vehicle_type: Mapped[str] = mapped_column(String(80), default="Bus")
    route_name: Mapped[str] = mapped_column(String(120), default="")
    capacity: Mapped[int] = mapped_column(Integer, default=40)
    driver_name: Mapped[str] = mapped_column(String(180), default="")
    driver_phone: Mapped[str] = mapped_column(String(40), default="")
    insurance_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_service_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active")

class Hostel(Base):
    __tablename__ = "hostels"
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    building: Mapped[str] = mapped_column(String(120), default="")
    room_no: Mapped[str] = mapped_column(String(40), default="")
    capacity: Mapped[int] = mapped_column(Integer, default=4)
    occupied: Mapped[int] = mapped_column(Integer, default=0)
    warden_name: Mapped[str] = mapped_column(String(180), default="")
    status: Mapped[str] = mapped_column(String(30), default="active")

class Document(Base):
    __tablename__ = "documents"
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_type: Mapped[str] = mapped_column(String(40), index=True)
    owner_id: Mapped[int] = mapped_column(Integer, index=True)
    category: Mapped[str] = mapped_column(String(120))
    file_name: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(30), default="pending")
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class MaintenanceRequest(Base):
    __tablename__ = "maintenance_requests"
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(100), default="General")
    location: Mapped[str] = mapped_column(String(180), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    status: Mapped[str] = mapped_column(String(30), default="open")
    assigned_to: Mapped[str] = mapped_column(String(180), default="")
    estimated_cost: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

# Append to models.py

class FeeStructure(Base):
    __tablename__ = "fee_structures"
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    __table_args__ = (
        UniqueConstraint(
            "school_id", "name", "academic_year", "term",
            name="uq_fee_structure_school_year_term"
        ),
        CheckConstraint("amount >= 0", name="ck_fee_structure_amount"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    category: Mapped[str] = mapped_column(String(40), index=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    academic_year: Mapped[str] = mapped_column(String(20), index=True)
    term: Mapped[str] = mapped_column(String(40), default="annual")
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )


class StudentFee(Base):
    __tablename__ = "student_fees"
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    __table_args__ = (
        CheckConstraint("total_amount >= 0", name="ck_student_fee_amount"),
        CheckConstraint("discount >= 0", name="ck_student_fee_discount"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id"), index=True
    )
    fee_structure_id: Mapped[int | None] = mapped_column(
        ForeignKey("fee_structures.id"), nullable=True
    )
    category: Mapped[str] = mapped_column(String(40), index=True)
    description: Mapped[str] = mapped_column(String(200), default="")
    academic_year: Mapped[str] = mapped_column(String(20), index=True)
    term: Mapped[str] = mapped_column(String(40), default="annual")
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2))
    discount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )


class FeePayment(Base):
    __tablename__ = "fee_payments"
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_fee_payment_amount"),
        UniqueConstraint("school_id", "receipt_no", name="uq_fee_payment_school_receipt"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_fee_id: Mapped[int] = mapped_column(
        ForeignKey("student_fees.id"), index=True
    )
    receipt_no: Mapped[str] = mapped_column(
        String(50), index=True
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    payment_method: Mapped[str] = mapped_column(String(30))
    transaction_reference: Mapped[str] = mapped_column(
        String(120), default=""
    )
    notes: Mapped[str] = mapped_column(Text, default="")
    payment_date: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    received_by: Mapped[int] = mapped_column(ForeignKey("users.id"))

class ParentStudentLink(Base):
    """Explicit parent-to-student relationship; never infer access from names/phones."""
    __tablename__ = "parent_student_links"
    __table_args__ = (
        UniqueConstraint("school_id", "parent_user_id", "student_id", name="uq_parent_student_school"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    parent_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    relationship: Mapped[str] = mapped_column(String(40), default="parent")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RolePermission(Base):
    __tablename__ = "role_permissions"
    school_id: Mapped[int | None] = mapped_column(ForeignKey("schools.id"), nullable=True, index=True)
    __table_args__ = (
        Index("uq_role_permission_global", "role", "module_key", "action", unique=True, postgresql_where=text("school_id IS NULL")),
        Index("uq_role_permission_school", "school_id", "role", "module_key", "action", unique=True, postgresql_where=text("school_id IS NOT NULL")),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[str] = mapped_column(String(40), index=True)
    module_key: Mapped[str] = mapped_column(String(60), index=True)
    action: Mapped[str] = mapped_column(String(20))
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    target_type: Mapped[str] = mapped_column(String(80), default="")
    target_id: Mapped[str] = mapped_column(String(120), default="")
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (UniqueConstraint("school_id", "student_id", "attendance_date", name="uq_attendance_school_student_date"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    attendance_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(20), default="present")
    remarks: Mapped[str] = mapped_column(String(300), default="")
    marked_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TimetableEntry(Base):
    __tablename__ = "timetable_entries"
    __table_args__ = (UniqueConstraint("school_id", "class_name", "section", "day_of_week", "period", name="uq_timetable_school_class_period"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    class_name: Mapped[str] = mapped_column(String(80), index=True)
    section: Mapped[str] = mapped_column(String(40), default="A")
    day_of_week: Mapped[str] = mapped_column(String(12), index=True)
    period: Mapped[int] = mapped_column(Integer)
    subject: Mapped[str] = mapped_column(String(100))
    teacher_name: Mapped[str] = mapped_column(String(180), default="")
    room: Mapped[str] = mapped_column(String(40), default="")
    start_time: Mapped[str] = mapped_column(String(5))
    end_time: Mapped[str] = mapped_column(String(5))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Exam(Base):
    __tablename__ = "exams"
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    class_name: Mapped[str] = mapped_column(String(80), index=True)
    section: Mapped[str] = mapped_column(String(40), default="")
    subject: Mapped[str] = mapped_column(String(100))
    exam_date: Mapped[date] = mapped_column(Date, index=True)
    max_marks: Mapped[float] = mapped_column(Numeric(8, 2))
    pass_marks: Mapped[float] = mapped_column(Numeric(8, 2))
    academic_year: Mapped[str] = mapped_column(String(20), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ReportCard(Base):
    __tablename__ = "report_cards"
    __table_args__ = (UniqueConstraint("school_id", "student_id", "exam_id", name="uq_report_card_school_student_exam"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), nullable=False, index=True)
    marks_obtained: Mapped[float] = mapped_column(Numeric(8, 2))
    remarks: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
