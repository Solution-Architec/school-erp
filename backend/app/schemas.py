from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, model_validator, Field
from decimal import Decimal
import re
from typing import Literal, Optional





class LoginInput(BaseModel):
    # School code is optional only for global Super Admin sign-in.
    # School-scoped accounts are still resolved only when a valid code is supplied.
    school_code: str = Field(default="", max_length=40)
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    school_id: int | None = None
    name: str
    email: EmailStr
    role: str
    model_config = ConfigDict(from_attributes=True)

class SchoolIn(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    code: str = Field(min_length=2, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")


class SchoolOut(BaseModel):
    id: int
    name: str
    code: str
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class StudentIn(BaseModel):
    admission_no: str = Field(min_length=1, max_length=80)
    full_name: str = Field(min_length=1, max_length=180)
    class_name: str = ""
    section: str = ""
    guardian_name: str = ""
    guardian_phone: str = ""
    email: str = ""
    address: str = ""
    date_of_birth: date | None = None
    transport_required: bool = False
    hostel_required: bool = False
    status: str = "active"

class StudentOut(StudentIn):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class StaffIn(BaseModel):
    employee_no: str = Field(min_length=1, max_length=80)
    full_name: str = Field(min_length=1, max_length=180)
    designation: str = ""
    department: str = ""
    phone: str = ""
    email: str = ""
    salary: float = Field(default=0, ge=0)

    @field_validator("phone")
    @classmethod
    def validate_indian_phone(cls, value: str) -> str:
        phone = re.sub(r"[\\s()-]", "", value or "")
        if not phone:
            return ""
        if phone.startswith("+91"):
            phone = phone[3:]
        elif phone.startswith("0091"):
            phone = phone[4:]
        elif phone.startswith("0") and len(phone) == 11:
            phone = phone[1:]
        if not re.fullmatch(r"[6-9]\\d{9}", phone):
            raise ValueError("Enter a valid 10-digit Indian mobile number (optionally with +91)")
        return phone

    @field_validator("designation", "department")
    @classmethod
    def normalize_staff_labels(cls, value: str) -> str:
        cleaned = " ".join((value or "").strip().split())
        known_corrections = {
            "acountent": "Accountant",
            "accountent": "Accountant",
            "finace": "Finance",
            "finanace": "Finance",
        }
        return known_corrections.get(cleaned.casefold(), cleaned.title())
    status: str = "active"
    # Only Super Admin may choose a school; tenant admins are always scoped server-side.
    school_id: int | None = Field(default=None, gt=0)

class StaffOut(BaseModel):
    # Output schema deliberately does not inherit StaffIn: legacy rows may contain
    # historical phone values that should remain readable and editable.
    id: int
    school_id: int
    employee_no: str
    full_name: str
    designation: str = ""
    department: str = ""
    phone: str = ""
    email: str = ""
    salary: Decimal = Decimal("0")
    status: str = "active"
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ClassIn(BaseModel):
    name: str
    section: str = "A"
    academic_year: str = ""
    class_teacher: str = ""
    capacity: int = Field(default=40, ge=1)

class ClassOut(ClassIn):
    id: int
    model_config = ConfigDict(from_attributes=True)

class VehicleIn(BaseModel):
    registration_no: str
    vehicle_type: str = "Bus"
    route_name: str = ""
    capacity: int = Field(default=40, ge=1)
    driver_name: str = ""
    driver_phone: str = ""
    insurance_expiry: date | None = None
    next_service_date: date | None = None
    status: str = "active"

class VehicleOut(VehicleIn):
    id: int
    model_config = ConfigDict(from_attributes=True)

class HostelIn(BaseModel):
    name: str
    building: str = ""
    room_no: str = ""
    capacity: int = Field(default=4, ge=1)
    occupied: int = Field(default=0, ge=0)
    warden_name: str = ""
    status: str = "active"

class HostelOut(HostelIn):
    id: int
    model_config = ConfigDict(from_attributes=True)

class DocumentIn(BaseModel):
    owner_type: str
    owner_id: int = Field(gt=0)
    category: str
    file_name: str
    storage_key: str
    status: str = "pending"
    expiry_date: date | None = None

class DocumentOut(DocumentIn):
    id: int
    uploaded_by: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class MaintenanceIn(BaseModel):
    title: str
    category: str = "General"
    location: str = ""
    description: str = ""
    priority: str = "medium"
    status: str = "open"
    assigned_to: str = ""
    estimated_cost: float = Field(default=0, ge=0)

class MaintenanceOut(MaintenanceIn):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

FeeCategory = Literal[
    "tuition", "admission", "examination",
    "transport", "hostel", "books", "miscellaneous"
]

PaymentMethod = Literal[
    "cash", "upi", "bank_transfer", "card", "cheque"
]


class FeeStructureIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: FeeCategory
    amount: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    academic_year: str = Field(min_length=4, max_length=20)
    term: str = "annual"
    description: str = ""
    is_active: bool = True


class FeeStructureOut(FeeStructureIn):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class StudentFeeIn(BaseModel):
    student_id: int = Field(gt=0)
    fee_structure_id: int | None = Field(default=None, gt=0)
    category: FeeCategory
    description: str = Field(default="", max_length=200)
    academic_year: str = Field(min_length=4, max_length=20)
    term: str = "annual"
    total_amount: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    discount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    due_date: date | None = None

    @model_validator(mode="after")
    def validate_discount(self):
        if self.discount > self.total_amount:
            raise ValueError("Discount cannot exceed total fee")
        return self


class PaymentIn(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    payment_method: PaymentMethod
    transaction_reference: str = Field(default="", max_length=120)
    notes: str = ""
    payment_date: datetime | None = None


class FeeStructureSummary(BaseModel):
    id: int
    name: str
    category: str
    amount: Decimal
    academic_year: str
    term: str
    description: str
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PaymentOut(BaseModel):
    id: int
    school_id: int | None = None
    student_fee_id: int
    receipt_no: str
    amount: Decimal
    payment_method: str
    transaction_reference: str
    notes: str
    payment_date: datetime
    received_by: int
    model_config = ConfigDict(from_attributes=True)

class StudentFeeOut(StudentFeeIn):
    id: int
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
