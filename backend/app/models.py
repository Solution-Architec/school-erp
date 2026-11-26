from datetime import datetime, date
from sqlalchemy import String, Integer, Date, DateTime, Boolean, ForeignKey, Text, Numeric, text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base
from sqlalchemy import UniqueConstraint, CheckConstraint, Index




class School(Base):
    __tablename__ = "schools"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    institution_type: Mapped[str] = mapped_column(String(40), default="school", index=True)
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

class CertificateApplication(Base):
    __tablename__ = "certificate_applications"
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    parent_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    certificate_type: Mapped[str] = mapped_column(String(40), index=True)
    purpose: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewer_note: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Homework(Base):
    __tablename__ = "homework"
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    class_name: Mapped[str] = mapped_column(String(80), index=True)
    section: Mapped[str] = mapped_column(String(40), default="")
    subject: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text, default="")
    assigned_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, index=True)
    attachment_url: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class StudentLeaveRequest(Base):
    __tablename__ = "student_leave_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    start_date: Mapped[date] = mapped_column(Date, index=True)
    end_date: Mapped[date] = mapped_column(Date)
    reason: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewer_note: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ParentTeacherMessage(Base):
    __tablename__ = "parent_teacher_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    sender_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    recipient_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(180), default="")
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class LibraryBook(Base):
    __tablename__ = "library_books"
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(180), index=True)
    author: Mapped[str] = mapped_column(String(180), default="")
    isbn: Mapped[str] = mapped_column(String(32), default="", index=True)
    publisher: Mapped[str] = mapped_column(String(180), default="")
    category: Mapped[str] = mapped_column(String(100), default="")
    total_copies: Mapped[int] = mapped_column(Integer, default=1)
    available_copies: Mapped[int] = mapped_column(Integer, default=1)
    shelf_location: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LibraryLoan(Base):
    __tablename__ = "library_loans"
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("library_books.id"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    issued_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    due_date: Mapped[date] = mapped_column(Date, index=True)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="issued", index=True)


class PlatformClientProfile(Base):
    """Platform-level commercial and contact details for one institution."""
    __tablename__ = "platform_client_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), unique=True, index=True)
    contact_person: Mapped[str] = mapped_column(String(180), default="")
    contact_email: Mapped[str] = mapped_column(String(255), default="")
    contact_phone: Mapped[str] = mapped_column(String(40), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    city: Mapped[str] = mapped_column(String(100), default="")
    state: Mapped[str] = mapped_column(String(100), default="")
    country: Mapped[str] = mapped_column(String(100), default="India")
    affiliation: Mapped[str] = mapped_column(String(180), default="")
    registration_no: Mapped[str] = mapped_column(String(120), default="")
    website: Mapped[str] = mapped_column(String(255), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ClientQuotation(Base):
    __tablename__ = "client_quotations"
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), index=True)
    quotation_no: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(180))
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    tax_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    discount_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class ClientSubscription(Base):
    __tablename__ = "client_subscriptions"
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), index=True)
    plan_name: Mapped[str] = mapped_column(String(120))
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    billing_cycle: Mapped[str] = mapped_column(String(20), default="annual")
    start_date: Mapped[date] = mapped_column(Date, index=True)
    end_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ClientPayment(Base):
    __tablename__ = "client_payments"
    __table_args__ = (CheckConstraint("amount > 0", name="ck_client_payment_amount"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), index=True)
    quotation_id: Mapped[int | None] = mapped_column(ForeignKey("client_quotations.id"), nullable=True, index=True)
    subscription_id: Mapped[int | None] = mapped_column(ForeignKey("client_subscriptions.id"), nullable=True, index=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    payment_date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    payment_method: Mapped[str] = mapped_column(String(30), default="bank_transfer")
    transaction_reference: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(20), default="received", index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    recorded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ClientSupportTicket(Base):
    __tablename__ = "client_support_tickets"
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), index=True)
    subject: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(40), default="general")
    priority: Mapped[str] = mapped_column(String(20), default="normal", index=True)
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    requester_name: Mapped[str] = mapped_column(String(180), default="")
    requester_email: Mapped[str] = mapped_column(String(255), default="")
    resolution_notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PlatformActivity(Base):
    """Latest authenticated activity heartbeat for each account; no content is captured."""
    __tablename__ = "platform_activity"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    school_id: Mapped[int | None] = mapped_column(ForeignKey("schools.id"), nullable=True, index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class CertificateIssue(Base):
    """Immutable issuance record for an approved parent certificate request."""
    __tablename__ = "certificate_issues"
    __table_args__ = (
        UniqueConstraint("application_id", name="uq_certificate_issue_application"),
        UniqueConstraint("school_id", "certificate_number", name="uq_certificate_issue_school_number"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("certificate_applications.id"), nullable=False, index=True)
    certificate_number: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    issued_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class RbacInstitutionType(Base):
    """Canonical institution categories used to scope Developer role templates."""
    __tablename__ = "rbac_institution_types"
    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class RbacModule(Base):
    """Canonical ERP module catalogue; platform-only modules cannot be tenant-granted."""
    __tablename__ = "rbac_modules"
    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    category: Mapped[str] = mapped_column(String(60), default="general", nullable=False)
    is_platform_only: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    institution_types: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class RbacAction(Base):
    """Canonical permission action vocabulary."""
    __tablename__ = "rbac_actions"
    key: Mapped[str] = mapped_column(String(30), primary_key=True)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class RbacModuleAction(Base):
    """Allow-listed action combinations for each registered module."""
    __tablename__ = "rbac_module_actions"
    module_key: Mapped[str] = mapped_column(
        String(60), ForeignKey("rbac_modules.key"), primary_key=True
    )
    action_key: Mapped[str] = mapped_column(
        String(30), ForeignKey("rbac_actions.key"), primary_key=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class RbacRoleTemplate(Base):
    """Developer-owned role template identity; versions hold immutable published policy."""
    __tablename__ = "rbac_role_templates"
    __table_args__ = (
        UniqueConstraint("template_key", name="uq_rbac_role_template_key"),
        Index("ix_rbac_role_template_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    template_key: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    category: Mapped[str] = mapped_column(String(60), default="general", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class RbacRoleTemplateVersion(Base):
    """Versioned template policy. Published rows are immutable by service contract."""
    __tablename__ = "rbac_role_template_versions"
    __table_args__ = (
        UniqueConstraint("template_id", "version_number", name="uq_rbac_template_version"),
        CheckConstraint("version_number > 0", name="ck_rbac_template_version_positive"),
        CheckConstraint("status IN ('draft', 'published', 'retired')", name="ck_rbac_template_version_status"),
        Index("ix_rbac_template_version_status", "template_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("rbac_role_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    institution_types: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    # Shape: [{"module_key": "...", "actions": ["View"], "scope": "institution"}]
    permissions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    change_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    published_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
