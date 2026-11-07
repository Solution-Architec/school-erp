from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, model_validator, Field
from decimal import Decimal
import re
from typing import Any, Literal, Optional





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
    approval_status: str = "approved"
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
    employee_no: str = Field(min_length=8, max_length=8, pattern=r"^[A-Za-z]{4}[0-9]{4}$")
    full_name: str = Field(min_length=2, max_length=100)
    designation: Literal["Principal", "Vice Principal", "Teacher", "Accountant", "Clerk", "Office Assistant", "Librarian", "Lab Assistant", "IT Administrator", "Transport Manager", "Hostel Warden", "Security Guard", "Other"] = "Teacher"
    department: str = Field(default="", max_length=32)
    phone: str = Field(min_length=13, max_length=13, pattern=r"^\+91[6-9]\d{9}$")
    email: str = Field(min_length=11, max_length=40, pattern=r"^[A-Za-z0-9._%+-]+@gmail\.com$")
    salary: Decimal = Field(default=Decimal("0.00"), ge=0, le=Decimal("150000.00"), max_digits=10, decimal_places=2)
    status: Literal["active", "absent", "suspended", "terminated", "sick", "leave"] = "active"
    # Developer-only optional login provisioning. The email is also the login username.
    create_account: bool = False
    account_role: Literal["principal", "vice_principal", "teacher", "account", "clerk", "office_assistant", "librarian", "lab_assistant", "it_administrator", "transport_manager", "hostel_warden", "security_guard", "others", "admin", "accountant"] = "principal"
    account_password: str | None = None
    # Only Super Admin may choose a school; tenant admins are always scoped server-side.
    school_id: int | None = Field(default=None, gt=0)

    @field_validator("employee_no")
    @classmethod
    def normalize_employee_no(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_staff_phone(cls, value: str) -> str:
        return re.sub(r"\s+", "", str(value or ""))

    @field_validator("salary", mode="before")
    @classmethod
    def validate_staff_salary_format(cls, value: Any) -> Any:
        if isinstance(value, (int, float, Decimal)):
            value = str(value)
        if not re.fullmatch(r"\d{1,7}\.\d{2}", str(value or "").strip()):
            raise ValueError("Enter monthly salary as digits with exactly two decimal places, e.g. 25000.00")
        return value

    @field_validator("email", mode="before")
    @classmethod
    def normalize_staff_email(cls, value: str) -> str:
        return str(value or "").strip().lower()

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        cleaned = " ".join((value or "").strip().split())
        if not re.fullmatch(r"[A-Za-z][A-Za-z .'-]*", cleaned):
            raise ValueError("Use letters, spaces, apostrophes, periods or hyphens only for the full name")
        return cleaned

    @field_validator("department")
    @classmethod
    def validate_staff_department(cls, value: str) -> str:
        cleaned = " ".join((value or "").strip().split())
        if cleaned and not re.fullmatch(r"[A-Za-z ]{1,32}", cleaned):
            raise ValueError("Use letters and spaces only (maximum 32 characters)")
        return cleaned.title()

    @field_validator("account_password")
    @classmethod
    def validate_account_password(cls, value: str | None) -> str | None:
        if value is not None and value and len(value) < 12:
            raise ValueError("Login password must contain at least 12 characters")
        return value

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
\n\nclass AttendanceIn(BaseModel):\n    student_id: int = Field(gt=0)\n    attendance_date: date\n    status: Literal["present", "absent", "late", "leave"] = "present"\n    remarks: str = Field(default="", max_length=300)\n\nclass AttendanceOut(AttendanceIn):\n    id: int\n    marked_by: int\n    created_at: datetime\n    model_config = ConfigDict(from_attributes=True)\n\nclass TimetableIn(BaseModel):\n    class_name: str = Field(min_length=1, max_length=80)\n    section: str = Field(default="A", max_length=40)\n    day_of_week: Literal["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]\n    period: int = Field(ge=1, le=16)\n    subject: str = Field(min_length=1, max_length=100)\n    teacher_name: str = Field(default="", max_length=180)\n    room: str = Field(default="", max_length=40)\n    start_time: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")\n    end_time: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")\n\n    @model_validator(mode="after")\n    def validate_period_times(self):\n        if self.end_time <= self.start_time:\n            raise ValueError("Period end time must be after its start time")\n        return self\n\nclass TimetableOut(TimetableIn):\n    id: int\n    created_at: datetime\n    model_config = ConfigDict(from_attributes=True)\n\nclass ExamIn(BaseModel):\n    name: str = Field(min_length=1, max_length=120)\n    class_name: str = Field(min_length=1, max_length=80)\n    section: str = Field(default="", max_length=40)\n    subject: str = Field(min_length=1, max_length=100)\n    exam_date: date\n    max_marks: Decimal = Field(gt=0, max_digits=8, decimal_places=2)\n    pass_marks: Decimal = Field(ge=0, max_digits=8, decimal_places=2)\n    academic_year: str = Field(default="", max_length=20)\n\n    @model_validator(mode="after")\n    def validate_pass_marks(self):\n        if self.pass_marks > self.max_marks:\n            raise ValueError("Pass marks cannot exceed maximum marks")\n        return self\n\nclass ExamOut(ExamIn):\n    id: int\n    created_at: datetime\n    model_config = ConfigDict(from_attributes=True)\n\nclass ReportCardIn(BaseModel):\n    student_id: int = Field(gt=0)\n    exam_id: int = Field(gt=0)\n    marks_obtained: Decimal = Field(ge=0, max_digits=8, decimal_places=2)\n    remarks: str = Field(default="", max_length=500)\n\nclass ReportCardOut(ReportCardIn):\n    id: int\n    created_at: datetime\n    model_config = ConfigDict(from_attributes=True)\n