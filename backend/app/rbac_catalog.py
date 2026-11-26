"""Canonical EduNexus RBAC catalogue and idempotent seed helpers.

This is catalogue data only: it does not grant permissions or change the
existing RolePermission/default-matrix authorization behavior.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models


INSTITUTION_TYPES = (
    ("school", "School"),
    ("college", "College"),
    ("university", "University"),
    ("coaching_centre", "Coaching Centre"),
    ("training_institute", "Training Institute"),
    ("other", "Other Institution"),
)

# Keep keys aligned with the existing RBAC_MODULES registry. The two
# platform workspaces are explicitly marked so tenant role builders can
# never expose them as ordinary institution modules.
MODULES = (
    ("dashboard", "Dashboard", "Institution overview and operational alerts", "workspace", False),
    ("parent-portal", "Parent Workspace", "Family services for verified linked students", "parent", False),
    ("parent-relationships", "Parent Relationships", "Governance of verified parent-student links", "parent", False),
    ("notifications", "Notification Centre", "School announcements and parent notifications", "communication", False),
    ("facility-requests", "Transport & Hostel Requests", "Review parent facility requests", "operations", False),
    ("developer-control", "Developer Control Centre", "Platform-wide institution and service administration", "platform", True),
    ("chatbot", "Help Assistant", "Guided help and institution FAQ", "workspace", False),
    ("approvals", "Staff Approvals", "Review institution staff account requests", "administration", False),
    ("schools", "Institutions", "Manage institution onboarding and platform records", "platform", True),
    ("students", "Students", "Student profiles, admissions and student services", "academic", False),
    ("staff", "Staff & HR", "Employee profiles and staff administration", "people", False),
    ("classes", "Classes", "Grades, departments, sections and class groups", "academic", False),
    ("vehicles", "Transport", "Vehicles, routes and transport operations", "operations", False),
    ("hostels", "Hostel", "Hostel facilities, rooms and occupancy", "operations", False),
    ("documents", "Documents", "Institution document register and verification", "administration", False),
    ("maintenance", "Maintenance", "Maintenance requests and work orders", "operations", False),
    ("fee-structures", "Fee Structures", "Configure tuition and other fee structures", "finance", False),
    ("student-fees", "Student Fees", "Assign fees and track outstanding balances", "finance", False),
    ("payments", "Fee Payments", "Record payments and manage receipts", "finance", False),
    ("fee-reports", "Fee Reports", "Collections, balances and overdue reports", "finance", False),
    ("attendance", "Attendance", "Student attendance records", "academic", False),
    ("timetable", "Timetable", "Periods, schedules and teaching assignments", "academic", False),
    ("exams", "Examinations", "Exam schedules and assessment setup", "academic", False),
    ("report-cards", "Report Cards", "Marks, results and academic reports", "academic", False),
    ("homework", "Homework", "Assignments and learning activities", "academic", False),
    ("student-leave", "Student Leave", "Student leave applications and approvals", "student-services", False),
    ("parent-messages", "Parent–Teacher Messages", "Private parent and school communication", "communication", False),
    ("library-books", "Library Books", "Library catalogue and inventory", "library", False),
    ("library-loans", "Library Issue & Return", "Book issue, return and loan records", "library", False),
    ("certificate-management", "Certificate Management", "Review, issue and download certificates", "administration", False),
)

# Preserve every action currently used by the legacy matrix. Additional
# action vocabulary is registered now for later template/API work; it is
# not automatically enabled for any role.
ACTIONS = (
    ("View", "View", "Read permitted module information"),
    ("Create", "Create", "Create a new record"),
    ("Edit", "Edit", "Modify an existing record"),
    ("Delete", "Delete", "Delete a record where policy permits"),
    ("Approve", "Approve", "Approve a pending workflow"),
    ("Export", "Export", "Export permitted information"),
    ("Reject", "Reject", "Reject a pending workflow"),
    ("Publish", "Publish", "Publish information to an audience"),
    ("Assign", "Assign", "Assign records, resources or users"),
    ("Import", "Import", "Import records from an approved source"),
    ("Print", "Print", "Print permitted records or reports"),
    ("Download", "Download", "Download permitted files or reports"),
    ("Manage", "Manage", "Manage module configuration"),
)

LEGACY_ACTION_KEYS = ("View", "Create", "Edit", "Delete", "Approve", "Export")


def seed_rbac_catalog(db: Session) -> dict[str, int]:
    """Insert missing catalogue rows without overwriting existing metadata."""
    counts = {"institution_types": 0, "modules": 0, "actions": 0, "module_actions": 0}

    for key, label in INSTITUTION_TYPES:
        if db.get(models.RbacInstitutionType, key) is None:
            db.add(models.RbacInstitutionType(key=key, label=label, is_active=True))
            counts["institution_types"] += 1

    for index, (key, label, description, category, platform_only) in enumerate(MODULES):
        if db.get(models.RbacModule, key) is None:
            db.add(models.RbacModule(
                key=key,
                label=label,
                description=description,
                category=category,
                is_platform_only=platform_only,
                is_active=True,
                institution_types=[item[0] for item in INSTITUTION_TYPES],
                sort_order=index,
            ))
            counts["modules"] += 1

    for key, label, description in ACTIONS:
        if db.get(models.RbacAction, key) is None:
            db.add(models.RbacAction(key=key, label=label, description=description, is_active=True))
            counts["actions"] += 1

    # The six legacy actions remain valid for every existing RBAC module,
    # preserving the current matrix's module/action shape during migration.
    for module_key, *_ in MODULES:
        for action_key in LEGACY_ACTION_KEYS:
            identity = (module_key, action_key)
            if db.get(models.RbacModuleAction, identity) is None:
                db.add(models.RbacModuleAction(
                    module_key=module_key,
                    action_key=action_key,
                    is_active=True,
                ))
                counts["module_actions"] += 1

    db.flush()
    return counts


def catalog_snapshot(db: Session, *, include_platform: bool = False) -> dict:
    """Return a stable, sorted read-only catalogue snapshot."""
    module_query = select(models.RbacModule).where(models.RbacModule.is_active.is_(True))
    if not include_platform:
        module_query = module_query.where(models.RbacModule.is_platform_only.is_(False))

    modules = db.scalars(module_query.order_by(models.RbacModule.sort_order, models.RbacModule.key)).all()
    actions = db.scalars(
        select(models.RbacAction).where(models.RbacAction.is_active.is_(True)).order_by(models.RbacAction.key)
    ).all()
    combinations = db.scalars(
        select(models.RbacModuleAction).where(models.RbacModuleAction.is_active.is_(True))
    ).all()
    types = db.scalars(
        select(models.RbacInstitutionType).where(models.RbacInstitutionType.is_active.is_(True)).order_by(models.RbacInstitutionType.key)
    ).all()

    action_map: dict[str, list[str]] = {}
    for item in combinations:
        action_map.setdefault(item.module_key, []).append(item.action_key)

    return {
        "institution_types": [{"key": item.key, "label": item.label} for item in types],
        "modules": [{
            "key": item.key,
            "label": item.label,
            "description": item.description,
            "category": item.category,
            "platform_only": item.is_platform_only,
            "institution_types": item.institution_types or [],
            "actions": sorted(action_map.get(item.key, [])),
        } for item in modules],
        "actions": [{"key": item.key, "label": item.label, "description": item.description} for item in actions],
    }
