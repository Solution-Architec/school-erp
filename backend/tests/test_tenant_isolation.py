from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app import main, models
from backend.app.database import Base


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


def _school(db, name, code):
    school = models.School(name=name, code=code)
    db.add(school)
    db.flush()
    return school


def _user(db, school_id, role, email):
    user = models.User(
        name=email.split("@")[0],
        email=email,
        password_hash="not-used-in-this-test",
        role=role,
        school_id=school_id,
    )
    db.add(user)
    db.flush()
    return user


def _student(db, school_id, admission_no, name):
    student = models.Student(
        school_id=school_id,
        admission_no=admission_no,
        full_name=name,
    )
    db.add(student)
    db.flush()
    return student


def test_school_admin_cannot_link_parent_to_another_school_student(db):
    school_a = _school(db, "School A", "SCA")
    school_b = _school(db, "School B", "SCB")
    admin = _user(db, school_a.id, "admin", "admin@a.example")
    parent = _user(db, school_a.id, "parent", "parent@a.example")
    student = _student(db, school_b.id, "B-001", "Student B")

    with pytest.raises(HTTPException) as exc:
        main.create_parent_link(
            {"parent_user_id": parent.id, "student_id": student.id},
            db=db,
            user=admin,
        )

    assert exc.value.status_code == 422
    assert db.query(models.ParentStudentLink).count() == 0


def test_parent_children_and_fees_never_return_cross_school_records(db):
    school_a = _school(db, "School A", "SCA")
    school_b = _school(db, "School B", "SCB")
    parent = _user(db, school_a.id, "parent", "parent@a.example")
    own_student = _student(db, school_a.id, "A-001", "Student A")
    foreign_student = _student(db, school_b.id, "B-001", "Student B")

    db.add(models.ParentStudentLink(
        school_id=school_a.id,
        parent_user_id=parent.id,
        student_id=own_student.id,
        relationship="parent",
    ))
    # Simulate a legacy/corrupt cross-tenant link to prove read paths also
    # enforce the student and fee tenant, not only link creation validation.
    db.add(models.ParentStudentLink(
        school_id=school_a.id,
        parent_user_id=parent.id,
        student_id=foreign_student.id,
        relationship="parent",
    ))
    db.add(models.StudentFee(
        school_id=school_b.id,
        student_id=foreign_student.id,
        category="tuition",
        description="Foreign school fee",
        academic_year="2026-2027",
        term="annual",
        total_amount=Decimal("1000.00"),
        discount=Decimal("0.00"),
        status="pending",
    ))
    db.commit()

    children = main.parent_children(db=db, user=parent)
    assert [child["id"] for child in children] == [own_student.id]

    foreign_fees = main.parent_child_fees(
        student_id=foreign_student.id,
        db=db,
        user=parent,
    )
    assert foreign_fees == []



def _route_endpoint(path, method):
    return next(
        route.endpoint
        for route in main.app.routes
        if getattr(route, "path", None) == path and method in getattr(route, "methods", set())
    )


@pytest.mark.parametrize(
    ("resource", "make_record"),
    [
        ("students", lambda school_id: models.Student(
            school_id=school_id, admission_no=f"{school_id}-001", full_name=f"Student {school_id}"
        )),
        ("staff", lambda school_id: models.Staff(
            school_id=school_id, employee_no=f"{school_id}-001", full_name=f"Staff {school_id}"
        )),
    ],
)
def test_generic_crud_routes_scope_list_get_update_and_delete_to_school(db, resource, make_record):
    school_a = _school(db, "School A", "SCA")
    school_b = _school(db, "School B", "SCB")
    admin = _user(db, school_a.id, "admin", "admin@a.example")
    own_record = make_record(school_a.id)
    foreign_record = make_record(school_b.id)
    db.add_all([own_record, foreign_record])
    db.commit()

    list_endpoint = _route_endpoint(f"/api/{resource}", "GET")
    get_endpoint = _route_endpoint(f"/api/{resource}/{{item_id}}", "GET")
    update_endpoint = _route_endpoint(f"/api/{resource}/{{item_id}}", "PUT")
    delete_endpoint = _route_endpoint(f"/api/{resource}/{{item_id}}", "DELETE")

    records = list_endpoint(q="", limit=100, offset=0, db=db, user=admin)
    assert [record.id for record in records] == [own_record.id]

    with pytest.raises(HTTPException) as get_error:
        get_endpoint(item_id=foreign_record.id, db=db, user=admin)
    assert get_error.value.status_code == 404

    with pytest.raises(HTTPException) as update_error:
        update_endpoint(item_id=foreign_record.id, payload=None, db=db, user=admin)
    assert update_error.value.status_code == 404

    with pytest.raises(HTTPException) as delete_error:
        delete_endpoint(item_id=foreign_record.id, db=db, user=admin)
    assert delete_error.value.status_code == 404

    assert db.get(type(foreign_record), foreign_record.id) is not None


def test_fee_dues_only_returns_the_requesting_school(db):
    school_a = _school(db, "School A", "SCA")
    school_b = _school(db, "School B", "SCB")
    admin = _user(db, school_a.id, "admin", "admin@a.example")
    student_a = _student(db, school_a.id, "A-001", "Student A")
    student_b = _student(db, school_b.id, "B-001", "Student B")

    fee_a = models.StudentFee(
        school_id=school_a.id, student_id=student_a.id, category="tuition",
        description="School A tuition", academic_year="2026-2027", term="annual",
        total_amount=Decimal("1000.00"), discount=Decimal("0.00"), status="pending",
    )
    fee_b = models.StudentFee(
        school_id=school_b.id, student_id=student_b.id, category="tuition",
        description="School B tuition", academic_year="2026-2027", term="annual",
        total_amount=Decimal("2000.00"), discount=Decimal("0.00"), status="pending",
    )
    db.add_all([fee_a, fee_b])
    db.commit()

    dues = main.fee_dues(db=db, user=admin)
    assert [row["fee_id"] for row in dues] == [fee_a.id]
    assert all(row["student_name"] != student_b.full_name for row in dues)
