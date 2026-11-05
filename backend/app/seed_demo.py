"""Opt-in seed data for exercising each SchoolOS workspace.

Run with ENABLE_DEMO_SEED=true python -m app.seed_demo.
A fresh shared demo password is generated and printed once per run.
"""
import os
import secrets
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select

from .database import SessionLocal
from . import models
from .security import hash_password


SCHOOL_CODE = "DEMO-SCHOOL"
SCHOOL_NAME = "SchoolOS Demo Academy"
DEMO_USERS = [
    ("Developer Demo", "demo.developer@example.test", "super_admin", None),
    ("Principal Demo", "demo.principal@example.test", "principal", "principal"),
    ("Vice Principal Demo", "demo.viceprincipal@example.test", "vice_principal", "vice_principal"),
    ("Teacher Demo", "demo.teacher@example.test", "teacher", "teacher"),
    ("Accounts Demo", "demo.accounts@example.test", "account", "account"),
    ("Clerk Demo", "demo.clerk@example.test", "clerk", "clerk"),
    ("Office Assistant Demo", "demo.officeassistant@example.test", "office_assistant", "office_assistant"),
    ("Librarian Demo", "demo.librarian@example.test", "librarian", "librarian"),
    ("Lab Assistant Demo", "demo.labassistant@example.test", "lab_assistant", "lab_assistant"),
    ("IT Administrator Demo", "demo.itadmin@example.test", "it_administrator", "it_administrator"),
    ("Transport Manager Demo", "demo.transport@example.test", "transport_manager", "transport_manager"),
    ("Hostel Warden Demo", "demo.warden@example.test", "hostel_warden", "hostel_warden"),
    ("Security Guard Demo", "demo.security@example.test", "security_guard", "security_guard"),
    ("Others Demo", "demo.others@example.test", "others", "others"),
    ("Parent Demo", "demo.parent@example.test", "parent", "parent"),
]


def main() -> None:
    if os.getenv("ENABLE_DEMO_SEED", "").lower() != "true":
        raise SystemExit("Refusing to seed demo accounts. Set ENABLE_DEMO_SEED=true to continue.")
    if os.getenv("APP_ENV", "").lower() in {"prod", "production"} and os.getenv("ALLOW_DEMO_SEED_IN_PRODUCTION", "").lower() != "true":
        raise SystemExit("Refusing to create demo accounts in production. Use a non-production database.")

    demo_password = secrets.token_urlsafe(18)
    with SessionLocal() as db:
        school = db.scalar(select(models.School).where(models.School.code == SCHOOL_CODE))
        if not school:
            school = models.School(name=SCHOOL_NAME, code=SCHOOL_CODE, is_active=True)
            db.add(school)
            db.flush()
        else:
            school.name = SCHOOL_NAME
            school.is_active = True

        users = {}
        for name, email, role, _ in DEMO_USERS:
            account = db.scalar(select(models.User).where(models.User.email == email))
            if not account:
                account = models.User(name=name, email=email, role=role)
                db.add(account)
            account.name = name
            account.role = role
            account.school_id = None if role == "super_admin" else school.id
            account.password_hash = hash_password(demo_password)
            account.is_active = True
            account.email_verified = True
            account.approval_status = "approved"
            users[role] = account
        db.flush()

        student = db.scalar(select(models.Student).where(
            models.Student.school_id == school.id,
            models.Student.admission_no == "DEMO-0001"))
        if not student:
            student = models.Student(
                school_id=school.id, admission_no="DEMO-0001",
                full_name="Aarav Demo Student", class_name="Class 5", section="A",
                guardian_name="Parent Demo", guardian_phone="9999999999",
                email="demo.parent@example.test", address="Demo campus",
                date_of_birth=date(2015, 6, 15), transport_required=True,
                hostel_required=True, status="active")
            db.add(student)
            db.flush()

        parent_link = db.scalar(select(models.ParentStudentLink).where(
            models.ParentStudentLink.school_id == school.id,
            models.ParentStudentLink.parent_user_id == users["parent"].id,
            models.ParentStudentLink.student_id == student.id))
        if not parent_link:
            db.add(models.ParentStudentLink(
                school_id=school.id, parent_user_id=users["parent"].id,
                student_id=student.id, relationship="parent", is_active=True))

        staff = db.scalar(select(models.Staff).where(
            models.Staff.school_id == school.id, models.Staff.employee_no == "DEMO0001"))
        if not staff:
            db.add(models.Staff(
                school_id=school.id, employee_no="DEMO0001",
                full_name="Teacher Demo", designation="Teacher",
                department="Academics", phone="+919999999999",
                email="demo.teacher@example.test", salary=Decimal("25000.00"),
                status="active"))

        school_class = db.scalar(select(models.SchoolClass).where(
            models.SchoolClass.school_id == school.id,
            models.SchoolClass.name == "Class 5",
            models.SchoolClass.section == "A"))
        if not school_class:
            db.add(models.SchoolClass(
                school_id=school.id, name="Class 5", section="A",
                academic_year="2026-27", class_teacher="Teacher Demo", capacity=40))

        vehicle = db.scalar(select(models.Vehicle).where(
            models.Vehicle.school_id == school.id,
            models.Vehicle.registration_no == "DEMO-BUS-01"))
        if not vehicle:
            db.add(models.Vehicle(
                school_id=school.id, registration_no="DEMO-BUS-01",
                vehicle_type="School Bus", route_name="Demo Route",
                capacity=40, driver_name="Demo Driver", driver_phone="9999999999",
                insurance_expiry=date(2027, 12, 31), next_service_date=date(2027, 1, 15),
                status="active"))

        hostel = db.scalar(select(models.Hostel).where(
            models.Hostel.school_id == school.id,
            models.Hostel.name == "Demo Boys Hostel",
            models.Hostel.room_no == "D-101"))
        if not hostel:
            db.add(models.Hostel(
                school_id=school.id, name="Demo Boys Hostel", building="Block D",
                room_no="D-101", capacity=4, occupied=1,
                warden_name="Hostel Warden Demo", status="active"))

        maintenance = db.scalar(select(models.MaintenanceRequest).where(
            models.MaintenanceRequest.school_id == school.id,
            models.MaintenanceRequest.title == "Demo classroom projector check"))
        if not maintenance:
            db.add(models.MaintenanceRequest(
                school_id=school.id, title="Demo classroom projector check",
                category="Electrical", location="Class 5",
                description="Sample maintenance request for role-wise testing.",
                priority="medium", status="open", assigned_to="IT Administrator Demo",
                estimated_cost=Decimal("1500.00")))

        fee_structure = db.scalar(select(models.FeeStructure).where(
            models.FeeStructure.school_id == school.id,
            models.FeeStructure.name == "Demo Annual Tuition",
            models.FeeStructure.academic_year == "2026-27",
            models.FeeStructure.term == "annual"))
        if not fee_structure:
            fee_structure = models.FeeStructure(
                school_id=school.id, name="Demo Annual Tuition", category="tuition",
                amount=Decimal("30000.00"), academic_year="2026-27",
                term="annual", description="Sample fee structure", is_active=True)
            db.add(fee_structure)
            db.flush()

        student_fee = db.scalar(select(models.StudentFee).where(
            models.StudentFee.school_id == school.id,
            models.StudentFee.student_id == student.id,
            models.StudentFee.description == "Demo annual tuition"))
        if not student_fee:
            student_fee = models.StudentFee(
                school_id=school.id, student_id=student.id,
                fee_structure_id=fee_structure.id, category="tuition",
                description="Demo annual tuition", academic_year="2026-27",
                term="annual", total_amount=Decimal("30000.00"),
                discount=Decimal("0.00"), due_date=date(2027, 3, 31),
                status="partial")
            db.add(student_fee)
            db.flush()

        payment = db.scalar(select(models.FeePayment).where(
            models.FeePayment.school_id == school.id,
            models.FeePayment.receipt_no == "DEMO-RCPT-0001"))
        if not payment:
            db.add(models.FeePayment(
                school_id=school.id, student_fee_id=student_fee.id,
                receipt_no="DEMO-RCPT-0001", amount=Decimal("5000.00"),
                payment_method="upi", transaction_reference="DEMO-UPI-0001",
                notes="Sample payment for testing", received_by=users["account"].id,
                payment_date=datetime.utcnow()))

        db.commit()

    print("\nSchoolOS demo accounts are ready.")
    print(f"School code for all school roles: {SCHOOL_CODE}")
    print("Developer: leave the school-code field blank.")
    print(f"Shared temporary password (shown once): {demo_password}\n")
    for name, email, role, _ in DEMO_USERS:
        print(f"{role:18} {email}")
    print("\nSample records: student, parent link, staff member, class, bus, hostel room,")
    print("maintenance request, fee structure, student fee and payment.")
    print("Change or remove these demo accounts and records before real school use.")


if __name__ == "__main__":
    main()
