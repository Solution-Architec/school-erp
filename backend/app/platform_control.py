from datetime import date, datetime, timedelta
from decimal import Decimal
import secrets
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from . import models
from .database import get_db
from .security import current_user, require_roles, create_access_token

router = APIRouter(prefix="/api/platform", tags=["platform-control"])


class ClientInstitutionInput(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    code: str = Field(min_length=2, max_length=40)
    institution_type: Literal["school", "college", "university", "coaching_centre", "training_institute", "other"] = "school"


class ClientInstitutionUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    code: str = Field(min_length=2, max_length=40)
    institution_type: Literal["school", "college", "university", "coaching_centre", "training_institute", "other"]


class ClientLifecycleAction(BaseModel):
    action: Literal["pause", "reactivate", "archive", "restore"]


class ClientProfileInput(BaseModel):
    contact_person: str = Field(default="", max_length=180)
    contact_email: str = Field(default="", max_length=255)
    contact_phone: str = Field(default="", max_length=40)
    address: str = Field(default="", max_length=4000)
    city: str = Field(default="", max_length=100)
    state: str = Field(default="", max_length=100)
    country: str = Field(default="India", max_length=100)
    affiliation: str = Field(default="", max_length=180)
    registration_no: str = Field(default="", max_length=120)
    website: str = Field(default="", max_length=255)
    notes: str = Field(default="", max_length=10000)


class QuotationInput(BaseModel):
    school_id: int = Field(gt=0)
    title: str = Field(min_length=2, max_length=180)
    amount: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    tax_amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    discount_amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    valid_until: date | None = None
    status: Literal["draft", "sent", "accepted", "rejected", "expired"] = "draft"
    notes: str = Field(default="", max_length=10000)

    @model_validator(mode="after")
    def validate_discount(self):
        if self.discount_amount > self.amount + self.tax_amount:
            raise ValueError("Discount cannot exceed the quotation total")
        return self


class SubscriptionInput(BaseModel):
    school_id: int = Field(gt=0)
    plan_name: str = Field(min_length=2, max_length=120)
    amount: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    billing_cycle: Literal["monthly", "quarterly", "half_yearly", "annual", "custom"] = "annual"
    start_date: date
    end_date: date
    status: Literal["active", "pending", "expired", "suspended", "cancelled"] = "active"
    notes: str = Field(default="", max_length=10000)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("Subscription expiry date must be on or after the start date")
        return self


class PaymentInput(BaseModel):
    school_id: int = Field(gt=0)
    quotation_id: int | None = Field(default=None, gt=0)
    subscription_id: int | None = Field(default=None, gt=0)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    payment_date: date = Field(default_factory=date.today)
    payment_method: Literal["cash", "upi", "bank_transfer", "card", "cheque", "other"] = "bank_transfer"
    transaction_reference: str = Field(default="", max_length=120)
    status: Literal["received", "pending", "failed", "refunded"] = "received"
    notes: str = Field(default="", max_length=4000)


class SupportTicketInput(BaseModel):
    school_id: int = Field(gt=0)
    subject: str = Field(min_length=3, max_length=180)
    description: str = Field(default="", max_length=10000)
    category: Literal["technical", "billing", "data", "training", "feature_request", "general"] = "general"
    priority: Literal["low", "normal", "high", "urgent"] = "normal"
    requester_name: str = Field(default="", max_length=180)
    requester_email: str = Field(default="", max_length=255)


class SupportTicketUpdate(BaseModel):
    status: Literal["open", "in_progress", "waiting_client", "resolved", "closed"]
    priority: Literal["low", "normal", "high", "urgent"] | None = None
    resolution_notes: str = Field(default="", max_length=10000)


def _school_or_404(db: Session, school_id: int) -> models.School:
    school = db.get(models.School, school_id)
    if not school:
        raise HTTPException(status_code=404, detail="Client institution not found")
    return school


def _profile_dict(profile):
    if not profile:
        return {}
    return {key: getattr(profile, key) for key in (
        "contact_person", "contact_email", "contact_phone", "address", "city",
        "state", "country", "affiliation", "registration_no", "website", "notes",
        "updated_at"
    )}


def _subscription_dict(item):
    if not item:
        return None
    return {
        "id": item.id, "school_id": item.school_id, "plan_name": item.plan_name,
        "amount": item.amount, "billing_cycle": item.billing_cycle,
        "start_date": item.start_date, "end_date": item.end_date,
        "status": item.status, "notes": item.notes, "created_at": item.created_at,
    }


@router.post("/activity/heartbeat")
def activity_heartbeat(db: Session = Depends(get_db), user: models.User = Depends(current_user)):
    """Record a minimal last-seen timestamp; does not collect page content or keystrokes."""
    now = datetime.utcnow()
    activity = db.scalar(select(models.PlatformActivity).where(models.PlatformActivity.user_id == user.id))
    if activity:
        activity.school_id = user.school_id
        activity.last_seen_at = now
    else:
        db.add(models.PlatformActivity(user_id=user.id, school_id=user.school_id, last_seen_at=now))
    db.commit()
    return {"recorded": True, "last_seen_at": now}


@router.get("/overview")
def platform_overview(db: Session = Depends(get_db), user: models.User = Depends(require_roles("super_admin"))):
    today = date.today()
    online_cutoff = datetime.utcnow() - timedelta(minutes=5)
    count = lambda model, *where: db.scalar(select(func.count()).select_from(model).where(*where)) or 0
    received = db.scalar(select(func.coalesce(func.sum(models.ClientPayment.amount), 0)).where(
        models.ClientPayment.status == "received"
    )) or Decimal("0")
    pending_quotes = count(models.ClientQuotation, models.ClientQuotation.status.in_(["draft", "sent"]))
    expiring = count(models.ClientSubscription, models.ClientSubscription.status == "active",
                     models.ClientSubscription.end_date >= today,
                     models.ClientSubscription.end_date <= today + timedelta(days=30))
    return {
        "institutions": count(models.School),
        "active_institutions": count(models.School, models.School.is_active.is_(True)),
        "users": count(models.User),
        "students": count(models.Student),
        "staff": count(models.Staff),
        "online_users": count(models.PlatformActivity, models.PlatformActivity.last_seen_at >= online_cutoff),
        "active_subscriptions": count(models.ClientSubscription, models.ClientSubscription.status == "active",
                                      models.ClientSubscription.end_date >= today),
        "subscriptions_expiring_30_days": expiring,
        "pending_quotations": pending_quotes,
        "received_amount": received,
        "open_support_tickets": count(models.ClientSupportTicket, models.ClientSupportTicket.status.in_(["open", "in_progress", "waiting_client"])),
    }


@router.post("/clients")
def create_client_institution(payload: ClientInstitutionInput, db: Session = Depends(get_db),
                              user: models.User = Depends(require_roles("super_admin"))):
    name = payload.name.strip()
    code = payload.code.strip().upper()
    if db.scalar(select(models.School.id).where((models.School.name == name) | (models.School.code == code))):
        raise HTTPException(status_code=409, detail="An institution with this name or code already exists")
    school = models.School(name=name, code=code, institution_type=payload.institution_type,
                           is_active=True, approval_status="approved")
    db.add(school)
    try:
        db.flush()
        db.add(models.PlatformClientProfile(school_id=school.id))
        db.add(models.AuditLog(actor_user_id=user.id, event_type="platform.client.created",
                               target_type="school", target_id=str(school.id),
                               details=f"Created {payload.institution_type} client '{name}' ({code})"))
        db.commit()
        db.refresh(school)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Institution name or code already exists")
    return {"id": school.id, "name": school.name, "code": school.code,
            "institution_type": school.institution_type, "is_active": school.is_active,
            "approval_status": school.approval_status, "created_at": school.created_at}


@router.put("/clients/{school_id}")
def update_client_institution(school_id: int, payload: ClientInstitutionUpdate,
                              db: Session = Depends(get_db),
                              user: models.User = Depends(require_roles("super_admin"))):
    school = _school_or_404(db, school_id)
    if school.approval_status == "archived":
        raise HTTPException(status_code=409, detail="Restore this archived client before editing")
    name = payload.name.strip()
    code = payload.code.strip().upper()
    duplicate = db.scalar(select(models.School.id).where(
        models.School.id != school_id,
        (models.School.name == name) | (models.School.code == code)))
    if duplicate:
        raise HTTPException(status_code=409, detail="Another institution already uses this name or code")
    old = {"name": school.name, "code": school.code, "institution_type": school.institution_type}
    school.name, school.code, school.institution_type = name, code, payload.institution_type
    db.add(models.AuditLog(actor_user_id=user.id, event_type="platform.client.updated",
                           target_type="school", target_id=str(school_id),
                           details=f"Updated institution details from {old} to {payload.model_dump()}"))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Institution name or code already exists")
    db.refresh(school)
    return {"id": school.id, "name": school.name, "code": school.code,
            "institution_type": school.institution_type, "is_active": school.is_active,
            "approval_status": school.approval_status}


@router.patch("/clients/{school_id}/lifecycle")
def change_client_lifecycle(school_id: int, payload: ClientLifecycleAction,
                            db: Session = Depends(get_db),
                            user: models.User = Depends(require_roles("super_admin"))):
    school = _school_or_404(db, school_id)
    action = payload.action
    if action == "pause":
        if school.approval_status == "archived":
            raise HTTPException(status_code=409, detail="Restore the archived client before pausing it")
        if not school.is_active:
            raise HTTPException(status_code=409, detail="This client is already inactive")
        school.is_active = False
        event = "platform.client.paused"
    elif action == "reactivate":
        if school.approval_status == "archived":
            raise HTTPException(status_code=409, detail="Restore the archived client before reactivating it")
        if school.is_active:
            raise HTTPException(status_code=409, detail="This client is already active")
        school.is_active = True
        school.approval_status = "approved"
        event = "platform.client.reactivated"
    elif action == "archive":
        if school.approval_status == "archived":
            raise HTTPException(status_code=409, detail="This client is already archived")
        school.is_active = False
        school.approval_status = "archived"
        event = "platform.client.archived"
    else:
        if school.approval_status != "archived":
            raise HTTPException(status_code=409, detail="Only archived clients can be restored")
        school.approval_status = "approved"
        school.is_active = True
        event = "platform.client.restored"
    db.add(models.AuditLog(actor_user_id=user.id, event_type=event, target_type="school",
                           target_id=str(school_id),
                           details=f"Client '{school.name}' lifecycle action: {action}. No tenant data was deleted."))
    db.commit()
    db.refresh(school)
    return {"id": school.id, "name": school.name, "is_active": school.is_active,
            "approval_status": school.approval_status, "action": action}


@router.get("/clients")
def platform_clients(q: str = Query(default="", max_length=120), db: Session = Depends(get_db),
                     user: models.User = Depends(require_roles("super_admin"))):
    schools = db.scalars(select(models.School).order_by(models.School.name)).all()
    profiles = {p.school_id: p for p in db.scalars(select(models.PlatformClientProfile)).all()}
    subscriptions = db.scalars(select(models.ClientSubscription).order_by(
        models.ClientSubscription.created_at.desc()
    )).all()
    latest_subscription = {}
    for item in subscriptions:
        latest_subscription.setdefault(item.school_id, item)
    result = []
    for school in schools:
        if q and q.casefold() not in (school.name + " " + school.code + " " + school.institution_type).casefold():
            continue
        result.append({
            "id": school.id, "name": school.name, "code": school.code,
            "institution_type": school.institution_type, "is_active": school.is_active,
            "approval_status": school.approval_status, "created_at": school.created_at,
            "users": db.scalar(select(func.count()).select_from(models.User).where(models.User.school_id == school.id)) or 0,
            "students": db.scalar(select(func.count()).select_from(models.Student).where(models.Student.school_id == school.id)) or 0,
            "staff": db.scalar(select(func.count()).select_from(models.Staff).where(models.Staff.school_id == school.id)) or 0,
            "profile": _profile_dict(profiles.get(school.id)),
            "subscription": _subscription_dict(latest_subscription.get(school.id)),
        })
    return result


@router.get("/clients/{school_id}")
def platform_client_detail(school_id: int, db: Session = Depends(get_db),
                           user: models.User = Depends(require_roles("super_admin"))):
    school = _school_or_404(db, school_id)
    profile = db.scalar(select(models.PlatformClientProfile).where(models.PlatformClientProfile.school_id == school_id))
    return {
        "id": school.id, "name": school.name, "code": school.code,
        "institution_type": school.institution_type, "is_active": school.is_active,
        "approval_status": school.approval_status, "created_at": school.created_at,
        "profile": _profile_dict(profile),
        "users": [{
            "id": account.id, "name": account.name, "email": account.email,
            "role": account.role, "is_active": account.is_active,
            "approval_status": account.approval_status, "created_at": account.created_at,
        } for account in db.scalars(select(models.User).where(models.User.school_id == school_id).order_by(models.User.name)).all()],
        "students_count": db.scalar(select(func.count()).select_from(models.Student).where(models.Student.school_id == school_id)) or 0,
        "staff_count": db.scalar(select(func.count()).select_from(models.Staff).where(models.Staff.school_id == school_id)) or 0,
    }


@router.put("/clients/{school_id}/profile")
def update_client_profile(school_id: int, payload: ClientProfileInput, db: Session = Depends(get_db),
                          user: models.User = Depends(require_roles("super_admin"))):
    _school_or_404(db, school_id)
    profile = db.scalar(select(models.PlatformClientProfile).where(models.PlatformClientProfile.school_id == school_id))
    if not profile:
        profile = models.PlatformClientProfile(school_id=school_id)
        db.add(profile)
    for key, value in payload.model_dump().items():
        setattr(profile, key, value)
    db.add(models.AuditLog(actor_user_id=user.id, event_type="platform.client_profile.updated",
                           target_type="school", target_id=str(school_id),
                           details="Client contact and institution profile updated"))
    db.commit()
    db.refresh(profile)
    return _profile_dict(profile)


@router.get("/quotations")
def list_quotations(school_id: int | None = None, db: Session = Depends(get_db),
                    user: models.User = Depends(require_roles("super_admin"))):
    stmt = select(models.ClientQuotation).order_by(models.ClientQuotation.created_at.desc())
    if school_id:
        stmt = stmt.where(models.ClientQuotation.school_id == school_id)
    return db.scalars(stmt).all()


@router.post("/quotations")
def create_quotation(payload: QuotationInput, db: Session = Depends(get_db),
                     user: models.User = Depends(require_roles("super_admin"))):
    _school_or_404(db, payload.school_id)
    quote = models.ClientQuotation(
        school_id=payload.school_id,
        quotation_no="ENQ-" + date.today().strftime("%Y%m%d") + "-" + secrets.token_hex(3).upper(),
        title=payload.title, amount=payload.amount, tax_amount=payload.tax_amount,
        discount_amount=payload.discount_amount, valid_until=payload.valid_until,
        status=payload.status, notes=payload.notes, created_by=user.id,
    )
    db.add(quote)
    db.flush()
    db.add(models.AuditLog(actor_user_id=user.id, event_type="platform.quotation.created",
                           target_type="quotation", target_id=str(quote.id),
                           details=f"Quotation {quote.quotation_no} created for institution {payload.school_id}"))
    db.commit()
    db.refresh(quote)
    return quote


@router.get("/subscriptions")
def list_subscriptions(school_id: int | None = None, db: Session = Depends(get_db),
                       user: models.User = Depends(require_roles("super_admin"))):
    stmt = select(models.ClientSubscription).order_by(models.ClientSubscription.end_date.asc())
    if school_id:
        stmt = stmt.where(models.ClientSubscription.school_id == school_id)
    return db.scalars(stmt).all()


@router.post("/subscriptions")
def create_subscription(payload: SubscriptionInput, db: Session = Depends(get_db),
                         user: models.User = Depends(require_roles("super_admin"))):
    _school_or_404(db, payload.school_id)
    item = models.ClientSubscription(**payload.model_dump(), created_by=user.id)
    db.add(item)
    db.flush()
    db.add(models.AuditLog(actor_user_id=user.id, event_type="platform.subscription.created",
                           target_type="subscription", target_id=str(item.id),
                           details=f"{payload.plan_name} subscription created for institution {payload.school_id}"))
    db.commit()
    db.refresh(item)
    return item


@router.get("/payments")
def list_client_payments(school_id: int | None = None, db: Session = Depends(get_db),
                         user: models.User = Depends(require_roles("super_admin"))):
    stmt = select(models.ClientPayment).order_by(models.ClientPayment.payment_date.desc())
    if school_id:
        stmt = stmt.where(models.ClientPayment.school_id == school_id)
    return db.scalars(stmt).all()


@router.post("/payments")
def record_client_payment(payload: PaymentInput, db: Session = Depends(get_db),
                           user: models.User = Depends(require_roles("super_admin"))):
    _school_or_404(db, payload.school_id)
    if payload.quotation_id:
        quote = db.get(models.ClientQuotation, payload.quotation_id)
        if not quote or quote.school_id != payload.school_id:
            raise HTTPException(status_code=404, detail="Quotation not found for this institution")
    if payload.subscription_id:
        subscription = db.get(models.ClientSubscription, payload.subscription_id)
        if not subscription or subscription.school_id != payload.school_id:
            raise HTTPException(status_code=404, detail="Subscription not found for this institution")
    item = models.ClientPayment(**payload.model_dump(), recorded_by=user.id)
    db.add(item)
    db.flush()
    db.add(models.AuditLog(actor_user_id=user.id, event_type="platform.payment.recorded",
                           target_type="payment", target_id=str(item.id),
                           details=f"Client payment recorded for institution {payload.school_id}; status={payload.status}"))
    db.commit()
    db.refresh(item)
    return item


@router.get("/support-tickets")
def list_support_tickets(school_id: int | None = None, status: str | None = None,
                         db: Session = Depends(get_db),
                         user: models.User = Depends(current_user)):
    stmt = select(models.ClientSupportTicket).order_by(models.ClientSupportTicket.updated_at.desc())
    if user.role != "super_admin":
        if not user.school_id:
            raise HTTPException(status_code=403, detail="Your account is not assigned to an institution")
        stmt = stmt.where(models.ClientSupportTicket.school_id == user.school_id)
    elif school_id:
        stmt = stmt.where(models.ClientSupportTicket.school_id == school_id)
    if status:
        stmt = stmt.where(models.ClientSupportTicket.status == status)
    return db.scalars(stmt).all()


@router.post("/support-tickets")
def create_support_ticket(payload: SupportTicketInput, db: Session = Depends(get_db),
                          user: models.User = Depends(current_user)):
    _school_or_404(db, payload.school_id)
    if user.role != "super_admin" and user.school_id != payload.school_id:
        raise HTTPException(status_code=403, detail="You can only submit support requests for your own institution")
    ticket_data = payload.model_dump()
    if user.role != "super_admin":
        ticket_data["requester_name"] = user.name
        ticket_data["requester_email"] = user.email
    ticket = models.ClientSupportTicket(**ticket_data, created_by=user.id)
    db.add(ticket)
    db.flush()
    db.add(models.AuditLog(actor_user_id=user.id, event_type="platform.support_ticket.created",
                           target_type="support_ticket", target_id=str(ticket.id),
                           details=f"Support ticket created for institution {payload.school_id}"))
    db.commit()
    db.refresh(ticket)
    return ticket


@router.patch("/support-tickets/{ticket_id}")
def update_support_ticket(ticket_id: int, payload: SupportTicketUpdate, db: Session = Depends(get_db),
                          user: models.User = Depends(require_roles("super_admin"))):
    ticket = db.get(models.ClientSupportTicket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Support ticket not found")
    ticket.status = payload.status
    if payload.priority is not None:
        ticket.priority = payload.priority
    ticket.resolution_notes = payload.resolution_notes
    ticket.updated_at = datetime.utcnow()
    db.add(models.AuditLog(actor_user_id=user.id, event_type="platform.support_ticket.updated",
                           target_type="support_ticket", target_id=str(ticket.id),
                           details=f"Support ticket status changed to {payload.status}"))
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/activity")
def platform_activity(db: Session = Depends(get_db), user: models.User = Depends(require_roles("super_admin"))):
    cutoff = datetime.utcnow() - timedelta(minutes=5)
    rows = db.execute(
        select(models.PlatformActivity, models.User, models.School)
        .join(models.User, models.User.id == models.PlatformActivity.user_id)
        .outerjoin(models.School, models.School.id == models.PlatformActivity.school_id)
        .order_by(models.PlatformActivity.last_seen_at.desc())
        .limit(500)
    ).all()
    return [{
        "user_id": activity.user_id, "name": account.name, "email": account.email,
        "role": account.role, "school_id": activity.school_id,
        "institution": school.name if school else "Platform",
        "last_seen_at": activity.last_seen_at.isoformat() + "Z",
        "online": activity.last_seen_at >= cutoff,
    } for activity, account, school in rows]


@router.post("/clients/{school_id}/workspace")
def enter_client_workspace(school_id: int, db: Session = Depends(get_db),
                           user: models.User = Depends(require_roles("super_admin"))):
    school = _school_or_404(db, school_id)
    if not school.is_active:
        raise HTTPException(status_code=409, detail="This client institution is inactive")
    token = create_access_token(user, workspace_school_id=school.id)
    db.add(models.AuditLog(
        actor_user_id=user.id, event_type="platform.client_workspace.entered",
        target_type="school", target_id=str(school.id),
        details=f"Platform owner entered the client workspace for {school.name}",
    ))
    db.commit()
    return {
        "access_token": token, "token_type": "bearer",
        "user": {"id": user.id, "name": user.name, "email": user.email,
                 "role": "admin", "school_id": school.id, "platform_workspace": True},
        "institution": {"id": school.id, "name": school.name, "code": school.code},
    }


@router.post("/workspace/exit")
def exit_client_workspace(db: Session = Depends(get_db),
                          user=Depends(current_user)):
    if not getattr(user, "is_platform_workspace", False):
        raise HTTPException(status_code=409, detail="You are not inside a client workspace")
    platform_owner = db.get(models.User, user.platform_owner_id)
    if not platform_owner or not platform_owner.is_active or platform_owner.role != "super_admin":
        raise HTTPException(status_code=401, detail="Platform owner account is unavailable")
    db.add(models.AuditLog(
        actor_user_id=platform_owner.id, event_type="platform.client_workspace.exited",
        target_type="school", target_id=str(user.school_id),
        details=f"Platform owner exited the client workspace for {user.platform_school_name}",
    ))
    db.commit()
    token = create_access_token(platform_owner)
    return {
        "access_token": token, "token_type": "bearer",
        "user": {"id": platform_owner.id, "name": platform_owner.name,
                 "email": platform_owner.email, "role": platform_owner.role,
                 "school_id": None, "platform_workspace": False},
    }


@router.get("/system-health")
def platform_system_health(db: Session = Depends(get_db),
                           user: models.User = Depends(require_roles("super_admin"))):
    database_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db.rollback()
        database_status = "unavailable"
    checked_at = datetime.utcnow()
    return {
        "api": "healthy",
        "database": database_status,
        "checked_at": checked_at.isoformat() + "Z",
    }
