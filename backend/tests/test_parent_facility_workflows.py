import asyncio
from types import SimpleNamespace

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app import models
from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.parent_services import StudentTransportAssignment, StudentHostelAssignment
from backend.app.security import current_user


def test_parent_facility_requests_are_link_scoped_and_staff_approval_updates_assignment():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    actor = {}
    def override_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[current_user] = lambda: actor["user"]

    with SessionLocal() as db:
        school = models.School(name="Facility Test School", code="FACILITY-TEST")
        other_school = models.School(name="Other Facility School", code="FACILITY-OTHER")
        db.add_all([school, other_school]); db.flush()
        parent = models.User(name="Parent", email="parent.facility@test.local", password_hash="x", role="parent", school_id=school.id)
        admin = models.User(name="Admin", email="admin.facility@test.local", password_hash="x", role="admin", school_id=school.id)
        student = models.Student(school_id=school.id, admission_no="F-001", full_name="Facility Child")
        other_student = models.Student(school_id=other_school.id, admission_no="F-002", full_name="Other Child")
        vehicle = models.Vehicle(school_id=school.id, registration_no="TS09AB1234", route_name="North Route", status="active")
        hostel = models.Hostel(school_id=school.id, name="Boys Hostel", building="Block A", room_no="101", status="active")
        db.add_all([parent, admin, student, other_student, vehicle, hostel]); db.flush()
        db.add(models.ParentStudentLink(school_id=school.id, parent_user_id=parent.id, student_id=student.id, is_active=True))
        db.commit()
        ids = {"school": school.id, "parent": parent.id, "admin": admin.id, "student": student.id,
               "other_student": other_student.id, "vehicle": vehicle.id, "hostel": hostel.id}

    def api(method, path, body=None):
        async def send():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                return await client.request(method, path, json=body)
        return asyncio.run(send())

    try:
        actor["user"] = SimpleNamespace(id=ids["parent"], role="parent", school_id=ids["school"])
        denied = api("GET", f"/api/parent/children/{ids['other_student']}/facilities")
        assert denied.status_code == 404

        created = api("POST", f"/api/parent/children/{ids['student']}/facility-requests", {
            "facility_type": "transport", "request_type": "pickup_change",
            "reason": "Please change the pickup point",
            "details": {"vehicle_id": ids["vehicle"], "pickup_point": "Main Gate", "pickup_time": "07:30"},
        })
        assert created.status_code == 201
        request_id = created.json()["id"]

        actor["user"] = SimpleNamespace(id=ids["admin"], role="admin", school_id=ids["school"])
        queue = api("GET", "/api/facility-requests?facility_type=transport")
        assert queue.status_code == 200 and queue.json()[0]["id"] == request_id
        reviewed = api("POST", f"/api/facility-requests/{request_id}/review", {"status": "approved", "reviewer_note": "Approved"})
        assert reviewed.status_code == 200

        actor["user"] = SimpleNamespace(id=ids["parent"], role="parent", school_id=ids["school"])
        facilities = api("GET", f"/api/parent/children/{ids['student']}/facilities")
        assert facilities.status_code == 200
        assert facilities.json()["transport"]["vehicle_registration"] == "TS09AB1234"
        assert facilities.json()["transport"]["pickup_point"] == "Main Gate"

        # A second review is rejected, preventing duplicate approval side effects.
        actor["user"] = SimpleNamespace(id=ids["admin"], role="admin", school_id=ids["school"])
        duplicate = api("POST", f"/api/facility-requests/{request_id}/review", {"status": "approved"})
        assert duplicate.status_code == 409
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
