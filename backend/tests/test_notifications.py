import asyncio
from types import SimpleNamespace

import httpx
from fastapi import FastAPI
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app import models
from backend.app.database import Base, get_db
from backend.app.notifications import NotificationRead, SchoolNotification, router
from backend.app.security import current_user


def test_parent_notification_inbox_requires_active_same_school_link_and_tracks_read():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    app = FastAPI()
    app.include_router(router)
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
        school = models.School(name="Notification School", code="NOTICE-1")
        other_school = models.School(name="Other Notification School", code="NOTICE-2")
        db.add_all([school, other_school])
        db.flush()
        parent = models.User(name="Parent", email="notice-parent@example.test", password_hash="x",
                             role="parent", school_id=school.id, is_active=True)
        linked = models.Student(school_id=school.id, admission_no="N-1", full_name="Linked Student",
                                class_name="5", section="A")
        unlinked = models.Student(school_id=school.id, admission_no="N-2", full_name="Unlinked Student",
                                  class_name="5", section="B")
        foreign = models.Student(school_id=other_school.id, admission_no="N-3", full_name="Foreign Student",
                                 class_name="5", section="A")
        db.add_all([parent, linked, unlinked, foreign])
        db.flush()
        link = models.ParentStudentLink(school_id=school.id, parent_user_id=parent.id,
                                        student_id=linked.id, is_active=True)
        db.add(link)
        school_notice = SchoolNotification(school_id=school.id, created_by=parent.id,
                                           title="School circular", body="School will close early.",
                                           category="announcement", audience="school", is_published=True)
        class_notice = SchoolNotification(school_id=school.id, created_by=parent.id,
                                          title="Class update", body="Bring your science notebook.",
                                          category="homework", audience="class", class_name="5",
                                          section="B", is_published=True)
        foreign_notice = SchoolNotification(school_id=other_school.id, created_by=parent.id,
                                            title="Other school", body="Not for this family.",
                                            category="general", audience="school", is_published=True)
        db.add_all([school_notice, class_notice, foreign_notice])
        db.commit()
        actor["user"] = SimpleNamespace(id=parent.id, role="parent", school_id=school.id)
        school_notice_id = school_notice.id
        link_id = link.id

    async def exercise():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/parent/notifications")
            assert response.status_code == 200
            rows = response.json()
            assert [row["title"] for row in rows] == ["School circular"]
            assert rows[0]["is_read"] is False

            read = await client.post(f"/api/parent/notifications/{school_notice_id}/read")
            assert read.status_code == 200
            assert read.json()["is_read"] is True
            again = await client.get("/api/parent/notifications")
            assert again.json()[0]["is_read"] is True

            with SessionLocal() as db:
                db.get(models.ParentStudentLink, link_id).is_active = False
                db.commit()

            revoked = await client.get("/api/parent/notifications")
            assert revoked.status_code == 200
            assert revoked.json() == []
            denied_read = await client.post(f"/api/parent/notifications/{school_notice_id}/read")
            assert denied_read.status_code == 404

    try:
        asyncio.run(exercise())
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
