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
