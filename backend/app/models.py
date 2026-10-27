from datetime import datetime, date
from sqlalchemy import String, Integer, Date, DateTime, Boolean, ForeignKey, Text, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base
from sqlalchemy import UniqueConstraint, CheckConstraint, Index




class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(40), default="admin")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Student(Base):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(primary_key=True)
    admission_no: Mapped[str] = mapped_column(String(80), unique=True, index=True)
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
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_no: Mapped[str] = mapped_column(String(80), unique=True, index=True)
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
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), index=True)
    section: Mapped[str] = mapped_column(String(40), default="A")
    academic_year: Mapped[str] = mapped_column(String(20), default="")
    class_teacher: Mapped[str] = mapped_column(String(180), default="")
    capacity: Mapped[int] = mapped_column(Integer, default=40)

class Vehicle(Base):
    __tablename__ = "vehicles"
    id: Mapped[int] = mapped_column(primary_key=True)
    registration_no: Mapped[str] = mapped_column(String(80), unique=True, index=True)
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
    __table_args__ = (
        UniqueConstraint(
            "name", "academic_year", "term",
            name="uq_fee_structure_name_year_term"
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
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_fee_payment_amount"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_fee_id: Mapped[int] = mapped_column(
        ForeignKey("student_fees.id"), index=True
    )
    receipt_no: Mapped[str] = mapped_column(
        String(50), unique=True, index=True
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