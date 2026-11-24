import hashlib
import hmac
import json
import os
import secrets
import shutil
import smtplib
import time
from datetime import date, datetime, timedelta
from decimal import Decimal
from email.message import EmailMessage
from pathlib import Path
from typing import Literal

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, select, func
from sqlalchemy.orm import Mapped, mapped_column, Session

from .database import Base, get_db
from . import models
from .security import current_user, require_roles, hash_password

router = APIRouter(prefix="/api/platform/ops", tags=["platform-operations"])
platform_owner = Depends(require_roles("super_admin"))

# These records are separate from institution maintenance requests: they describe
# the EduNexus platform itself and are always controlled by the platform owner.
class ClientRequestReview(Base):
    __tablename__ = "platform_client_request_reviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    requested_information: Mapped[str] = mapped_column(Text, default="")
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UserInvitation(Base):
    __tablename__ = "platform_user_invitations"
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    role: Mapped[str] = mapped_column(String(60))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    invited_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PlatformIncident(Base):
    __tablename__ = "platform_incidents"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(20), default="medium")
    status: Mapped[str] = mapped_column(String(30), default="open")
    affected_scope: Mapped[str] = mapped_column(String(30), default="platform")
    school_id: Mapped[int | None] = mapped_column(ForeignKey("schools.id"), nullable=True, index=True)
    assigned_to: Mapped[str] = mapped_column(String(180), default="")
    resolution_notes: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PlatformMaintenanceWindow(Base):
    __tablename__ = "platform_maintenance_windows"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text, default="")
    starts_at: Mapped[datetime] = mapped_column(DateTime)
    ends_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default="scheduled")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GatewayPaymentAttempt(Base):
    __tablename__ = "platform_gateway_payment_attempts"
    __table_args__ = (UniqueConstraint("provider_order_id", name="uq_platform_gateway_order"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), index=True)
    subscription_id: Mapped[int | None] = mapped_column(ForeignKey("client_subscriptions.id"), nullable=True)
    provider_order_id: Mapped[str] = mapped_column(String(120), index=True)
    provider_payment_id: Mapped[str] = mapped_column(String(120), default="")
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    status: Mapped[str] = mapped_column(String(20), default="created")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ClientRequestDecision(BaseModel):
    decision: Literal["approve", "reject", "request_info"]
    reason: str = Field(default="", max_length=2000)


class InviteInput(BaseModel):
    school_id: int = Field(gt=0)
    email: EmailStr
    role: str = Field(min_length=2, max_length=60)


class InviteAcceptInput(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    name: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=12, max_length=200)


class RoleAssignmentInput(BaseModel):
    role: str = Field(min_length=2, max_length=60)


class SubscriptionRenewalInput(BaseModel):
    start_date: date
    end_date: date
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    notes: str = Field(default="", max_length=4000)


class IncidentInput(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(default="", max_length=12000)
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    affected_scope: Literal["platform", "institution"] = "platform"
    school_id: int | None = Field(default=None, gt=0)
    assigned_to: str = Field(default="", max_length=180)


class IncidentUpdate(BaseModel):
    status: Literal["open", "investigating", "identified", "monitoring", "resolved", "closed"]
    severity: Literal["low", "medium", "high", "critical"] | None = None
    assigned_to: str = Field(default="", max_length=180)
    resolution_notes: str = Field(default="", max_length=12000)


class MaintenanceWindowInput(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(default="", max_length=6000)
    starts_at: datetime
    ends_at: datetime


class CheckoutInput(BaseModel):
    school_id: int = Field(gt=0)
    subscription_id: int | None = Field(default=None, gt=0)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class VerifyPaymentInput(BaseModel):
    school_id: int = Field(gt=0)
    order_id: str = Field(min_length=4, max_length=120)
    payment_id: str = Field(min_length=4, max_length=120)
    signature: str = Field(min_length=20, max_length=256)


def _audit(db: Session, actor, event: str, target: str, target_id: str, details: dict):
    db.add(models.AuditLog(actor_user_id=actor.id, event_type=event, target_type=target,
                           target_id=target_id, details=json.dumps(details, separators=(",", ":"), sort_keys=True)))


def _school(db: Session, school_id: int):
    school = db.get(models.School, school_id)
    if not school:
        raise HTTPException(status_code=404, detail="Institution not found")
    return school


def _role_allowed(role: str, institution_type: str) -> bool:
    role = role.strip().lower()
    common = {"admin", "principal", "vice_principal", "teacher", "account", "accountant", "clerk",
              "office_assistant", "librarian", "lab_assistant", "it_administrator", "transport_manager",
              "hostel_warden", "security_guard", "others", "parent", "user"}
    specific = {
        "school": {"school_hod", "class_teacher", "school_accountant", "admission_officer",
                   "examination_controller", "school_counsellor", "school_receptionist", "school_student"},
        "college": {"college_admin", "college_principal", "college_vice_principal", "dean", "college_hod",
                    "lecturer", "college_professor", "academic_coordinator", "registrar", "college_exam_controller",
                    "college_admission_officer", "accounts_officer", "college_librarian", "lab_in_charge",
                    "placement_officer", "college_student"},
        "university": {"university_admin", "chancellor", "vice_chancellor", "university_registrar",
                       "university_dean", "university_director", "department_head", "university_professor",
                       "research_supervisor", "university_exam_controller", "university_finance_officer",
                       "university_admission_officer", "research_scholar", "university_student"},
        "coaching_centre": {"institute_admin", "centre_director", "other_academic_coordinator", "batch_coordinator",
                            "trainer", "admission_counsellor", "admission_executive", "other_accounts_officer",
                            "training_librarian", "training_student"},
        "training_institute": {"institute_admin", "centre_director", "other_academic_coordinator", "batch_coordinator",
                               "trainer", "admission_counsellor", "admission_executive", "other_accounts_officer",
                               "training_librarian", "training_student"},
        "other": {"institute_admin", "centre_director", "other_academic_coordinator", "batch_coordinator",
                  "trainer", "admission_counsellor", "admission_executive", "other_accounts_officer",
                  "training_librarian", "training_student"},
    }
    return role in common or role in specific.get(institution_type, set())


def _send_invitation(email: str, link: str, school_name: str, role: str) -> bool:
    host = os.getenv("SMTP_HOST")
    sender = os.getenv("SMTP_FROM_EMAIL") or os.getenv("SMTP_USERNAME")
    if not host or not sender:
        return False
    message = EmailMessage()
    message["Subject"] = f"Invitation to join {school_name} on EduNexus"
    message["From"] = sender
    message["To"] = email
    message.set_content(
        f"You have been invited to join {school_name} on EduNexus as {role.replace('_', ' ')}.\\n\\n"
        f"Accept your invitation using this one-time link (expires in 7 days):\\n{link}\\n"
    )
    port = int(os.getenv("SMTP_PORT", "587"))
    username, password = os.getenv("SMTP_USERNAME"), os.getenv("SMTP_PASSWORD")
    if os.getenv("SMTP_USE_SSL", "false").lower() == "true":
        with smtplib.SMTP_SSL(host, port, timeout=20) as server:
            if username and password:
                server.login(username, password)
            server.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.ehlo()
            if os.getenv("SMTP_USE_TLS", "true").lower() == "true":
                server.starttls()
                server.ehlo()
            if username and password:
                server.login(username, password)
            server.send_message(message)
    return True


@router.get("/client-requests")
def list_client_requests(db: Session = Depends(get_db), user=platform_owner):
    schools = db.scalars(select(models.School).where(
        models.School.approval_status.in_(["pending", "rejected"])
    ).order_by(models.School.created_at.desc())).all()
    result = []
    for school in schools:
        founder = db.scalar(select(models.User).where(
            models.User.school_id == school.id, models.User.role.in_(["principal", "admin", "college_admin", "university_admin", "institute_admin"])
        ).order_by(models.User.created_at.asc()))
        review = db.scalar(select(ClientRequestReview).where(ClientRequestReview.school_id == school.id))
        profile = db.scalar(select(models.PlatformClientProfile).where(models.PlatformClientProfile.school_id == school.id))
        result.append({
            "school_id": school.id, "school_name": school.name, "school_code": school.code,
            "institution_type": school.institution_type, "approval_status": school.approval_status,
            "created_at": school.created_at, "review_status": review.status if review else "pending",
            "requested_information": review.requested_information if review else "",
            "founder": {"user_id": founder.id, "name": founder.name, "email": founder.email,
                        "email_verified": founder.email_verified} if founder else None,
            "contact": {"contact_person": profile.contact_person, "contact_email": profile.contact_email,
                        "contact_phone": profile.contact_phone, "registration_no": profile.registration_no,
                        "city": profile.city, "state": profile.state} if profile else {},
        })
    return result


@router.post("/client-requests/{school_id}/decision")
def decide_client_request(school_id: int, payload: ClientRequestDecision,
                          db: Session = Depends(get_db), user=platform_owner):
    school = _school(db, school_id)
    if school.approval_status not in {"pending", "rejected"}:
        raise HTTPException(status_code=409, detail="This institution request has already been approved")
    review = db.scalar(select(ClientRequestReview).where(ClientRequestReview.school_id == school_id))
    if not review:
        review = ClientRequestReview(school_id=school_id)
        db.add(review)
    review.reviewer_id = user.id
    review.updated_at = datetime.utcnow()
    review.requested_information = payload.reason
    founder = db.scalar(select(models.User).where(models.User.school_id == school_id).order_by(models.User.created_at.asc()))
    if payload.decision == "request_info":
        review.status = "info_requested"
        event = "platform.client_request.info_requested"
    elif payload.decision == "reject":
        review.status = "rejected"
        school.approval_status = "rejected"
        school.is_active = False
        if founder:
            founder.approval_status = "rejected"
            founder.is_active = False
        event = "platform.client_request.rejected"
    else:
        review.status = "approved"
        school.approval_status = "approved"
        school.is_active = True
        if founder:
            admin_role = {"school": "admin", "college": "college_admin", "university": "university_admin"}.get(
                school.institution_type, "institute_admin")
            founder.role = admin_role
            founder.approval_status = "approved"
            founder.is_active = bool(founder.email_verified)
        event = "platform.client_request.approved"
    _audit(db, user, event, "school", str(school_id),
           {"institution": school.name, "decision": payload.decision, "reason": payload.reason})
    db.commit()
    return {"school_id": school_id, "approval_status": school.approval_status,
            "review_status": review.status, "founder_active": bool(founder and founder.is_active)}


@router.get("/users")
def list_client_users(school_id: int = Query(gt=0), db: Session = Depends(get_db), user=platform_owner):
    _school(db, school_id)
    return [{
        "id": account.id, "name": account.name, "email": account.email, "role": account.role,
        "is_active": account.is_active, "approval_status": account.approval_status,
        "created_at": account.created_at,
    } for account in db.scalars(select(models.User).where(models.User.school_id == school_id)
                                .order_by(models.User.name)).all()]


@router.post("/invitations")
def create_invitation(payload: InviteInput, db: Session = Depends(get_db), user=platform_owner):
    school = _school(db, payload.school_id)
    email = str(payload.email).strip().lower()
    role = payload.role.strip().lower()
    if not school.is_active or school.approval_status != "approved":
        raise HTTPException(status_code=409, detail="Activate and approve the institution before inviting users")
    if not _role_allowed(role, school.institution_type):
        raise HTTPException(status_code=422, detail="This role is not available for the selected institution type")
    existing = db.scalar(select(models.User.id).where(models.User.email == email))
    if existing:
        raise HTTPException(status_code=409, detail="This email already has an account; use role assignment instead")
    pending = db.scalar(select(UserInvitation).where(
        UserInvitation.email == email, UserInvitation.school_id == school.id,
        UserInvitation.accepted_at.is_(None), UserInvitation.expires_at > datetime.utcnow()))
    if pending:
        raise HTTPException(status_code=409, detail="An unexpired invitation already exists for this email")
    token = secrets.token_urlsafe(36)
    invitation = UserInvitation(school_id=school.id, email=email, role=role,
        token_hash=hashlib.sha256(token.encode()).hexdigest(), invited_by=user.id,
        expires_at=datetime.utcnow() + timedelta(days=7))
    db.add(invitation)
    db.flush()
    frontend = os.getenv("FRONTEND_URL", os.getenv("APP_BASE_URL", "http://localhost:8081")).rstrip("/")
    link = f"{frontend}/accept-invitation?token={token}"
    email_sent = False
    try:
        email_sent = _send_invitation(email, link, school.name, role)
    except Exception as exc:
        # Keep the invitation usable for a platform owner to copy/send manually.
        print(f"INVITATION EMAIL DELIVERY FAILED: {type(exc).__name__}: {exc}", flush=True)
    _audit(db, user, "platform.user_invitation.created", "school", str(school.id),
           {"email": email, "role": role, "email_sent": email_sent})
    db.commit()
    return {"invitation_id": invitation.id, "email": email, "role": role,
            "expires_at": invitation.expires_at, "email_sent": email_sent,
            "invitation_url": link if not email_sent else None}


@router.post("/invitations/accept")
def accept_invitation(payload: InviteAcceptInput, db: Session = Depends(get_db)):
    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    invitation = db.scalar(select(UserInvitation).where(UserInvitation.token_hash == token_hash))
    if not invitation or invitation.accepted_at or invitation.expires_at <= datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invitation is invalid, expired or already used")
    school = _school(db, invitation.school_id)
    if not school.is_active or school.approval_status != "approved":
        raise HTTPException(status_code=409, detail="Institution is not currently accepting accounts")
    if db.scalar(select(models.User.id).where(models.User.email == invitation.email)):
        raise HTTPException(status_code=409, detail="An account already exists for this email")
    account = models.User(name=payload.name.strip(), email=invitation.email,
        password_hash=hash_password(payload.password), role=invitation.role,
        school_id=school.id, is_active=True, email_verified=True, approval_status="approved")
    db.add(account)
    db.flush()
    invitation.accepted_at = datetime.utcnow()
    _audit(db, account, "platform.user_invitation.accepted", "school", str(school.id),
           {"email": invitation.email, "role": invitation.role})
    db.commit()
    return {"message": "Invitation accepted. You can now sign in.", "email": account.email,
            "school_id": school.id, "role": account.role}


@router.put("/clients/{school_id}/users/{user_id}/role")
def assign_client_user_role(school_id: int, user_id: int, payload: RoleAssignmentInput,
                            db: Session = Depends(get_db), user=platform_owner):
    school = _school(db, school_id)
    account = db.get(models.User, user_id)
    role = payload.role.strip().lower()
    if not account or account.school_id != school_id or account.role == "super_admin":
        raise HTTPException(status_code=404, detail="Institution user not found")
    if not _role_allowed(role, school.institution_type):
        raise HTTPException(status_code=422, detail="This role is not available for the selected institution type")
    previous = account.role
    account.role = role
    _audit(db, user, "platform.user_role.assigned", "user", str(user_id),
           {"school_id": school_id, "previous_role": previous, "new_role": role})
    db.commit()
    return {"user_id": user_id, "role": role}


@router.post("/subscriptions/{subscription_id}/renew")
def renew_subscription(subscription_id: int, payload: SubscriptionRenewalInput,
                       db: Session = Depends(get_db), user=platform_owner):
    previous = db.get(models.ClientSubscription, subscription_id)
    if not previous:
        raise HTTPException(status_code=404, detail="Subscription not found")
    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=422, detail="Expiry date must be on or after start date")
    school = _school(db, previous.school_id)
    renewal = models.ClientSubscription(
        school_id=school.id, plan_name=previous.plan_name, amount=payload.amount,
        billing_cycle=previous.billing_cycle, start_date=payload.start_date,
        end_date=payload.end_date, status="active", notes=payload.notes or f"Renewal of subscription #{previous.id}",
        created_by=user.id)
    db.add(renewal)
    school.is_active = True
    school.approval_status = "approved"
    db.flush()
    _audit(db, user, "platform.subscription.renewed", "subscription", str(renewal.id),
           {"school_id": school.id, "previous_subscription_id": previous.id,
            "start_date": str(payload.start_date), "end_date": str(payload.end_date)})
    db.commit()
    db.refresh(renewal)
    return renewal


@router.post("/subscriptions/expiry-sweep")
def subscription_expiry_sweep(db: Session = Depends(get_db), user=platform_owner):
    grace_days = max(0, min(90, int(os.getenv("SUBSCRIPTION_GRACE_DAYS", "7"))))
    today = date.today()
    changed = []
    schools = db.scalars(select(models.School).where(models.School.is_active.is_(True))).all()
    for school in schools:
        latest = db.scalar(select(models.ClientSubscription).where(
            models.ClientSubscription.school_id == school.id,
            models.ClientSubscription.status == "active"
        ).order_by(models.ClientSubscription.end_date.desc()).limit(1))
        if latest and latest.end_date + timedelta(days=grace_days) < today:
            school.is_active = False
            school.approval_status = "subscription_expired"
            changed.append(school.id)
            _audit(db, user, "platform.subscription.expired", "school", str(school.id),
                   {"subscription_id": latest.id, "end_date": str(latest.end_date), "grace_days": grace_days})
    db.commit()
    return {"grace_days": grace_days, "suspended_school_ids": changed, "count": len(changed)}


@router.post("/payments/checkout")
def create_gateway_checkout(payload: CheckoutInput, db: Session = Depends(get_db), user=platform_owner):
    school = _school(db, payload.school_id)
    key_id, key_secret = os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET")
    if not key_id or not key_secret:
        raise HTTPException(status_code=503, detail="Razorpay is not configured. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET.")
    if payload.subscription_id:
        subscription = db.get(models.ClientSubscription, payload.subscription_id)
        if not subscription or subscription.school_id != school.id:
            raise HTTPException(status_code=404, detail="Subscription not found for this institution")
    amount_paise = int((payload.amount * 100).quantize(Decimal("1")))
    try:
        response = httpx.post("https://api.razorpay.com/v1/orders",
            auth=(key_id, key_secret),
            json={"amount": amount_paise, "currency": "INR",
                  "receipt": f"EN-{school.id}-{secrets.token_hex(5)}",
                  "notes": {"school_id": str(school.id), "subscription_id": str(payload.subscription_id or "")}},
            timeout=20)
        response.raise_for_status()
        order = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"Payment provider order creation failed: {type(exc).__name__}")
    attempt = GatewayPaymentAttempt(school_id=school.id, subscription_id=payload.subscription_id,
        provider_order_id=order["id"], amount=payload.amount, currency="INR",
        status="created", created_by=user.id)
    db.add(attempt)
    _audit(db, user, "platform.payment.checkout_created", "payment_order", order["id"],
           {"school_id": school.id, "amount": str(payload.amount), "currency": "INR"})
    db.commit()
    return {"provider": "razorpay", "key_id": key_id, "order_id": order["id"],
            "amount": amount_paise, "currency": "INR", "school_name": school.name}


@router.post("/payments/verify")
def verify_gateway_payment(payload: VerifyPaymentInput, db: Session = Depends(get_db), user=platform_owner):
    key_id, key_secret = os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET")
    if not key_id or not key_secret:
        raise HTTPException(status_code=503, detail="Razorpay is not configured")
    attempt = db.scalar(select(GatewayPaymentAttempt).where(
        GatewayPaymentAttempt.provider_order_id == payload.order_id,
        GatewayPaymentAttempt.school_id == payload.school_id))
    if not attempt:
        raise HTTPException(status_code=404, detail="Payment order not found")
    expected = hmac.new(key_secret.encode(), f"{payload.order_id}|{payload.payment_id}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, payload.signature):
        raise HTTPException(status_code=400, detail="Payment signature verification failed")
    if attempt.status == "paid":
        return {"verified": True, "already_recorded": True}
    try:
        response = httpx.get(f"https://api.razorpay.com/v1/payments/{payload.payment_id}",
                             auth=(key_id, key_secret), timeout=20)
        response.raise_for_status()
        provider_payment = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"Could not verify payment with provider: {type(exc).__name__}")
    if provider_payment.get("order_id") != payload.order_id or provider_payment.get("status") != "captured":
        raise HTTPException(status_code=409, detail="Provider has not confirmed a captured payment for this order")
    if int(provider_payment.get("amount", 0)) != int((attempt.amount * 100).quantize(Decimal("1"))):
        raise HTTPException(status_code=409, detail="Captured payment amount does not match the order")
    attempt.provider_payment_id = payload.payment_id
    attempt.status = "paid"
    attempt.verified_at = datetime.utcnow()
    payment = models.ClientPayment(school_id=attempt.school_id, subscription_id=attempt.subscription_id,
        amount=attempt.amount, payment_date=date.today(), payment_method="upi",
        transaction_reference=payload.payment_id, status="received",
        notes="Verified Razorpay payment", recorded_by=user.id)
    db.add(payment)
    _audit(db, user, "platform.payment.gateway_verified", "payment", payload.payment_id,
           {"school_id": attempt.school_id, "order_id": payload.order_id, "amount": str(attempt.amount)})
    db.commit()
    return {"verified": True, "payment_id": payment.id, "amount": str(payment.amount)}


@router.get("/incidents")
def list_platform_incidents(db: Session = Depends(get_db), user=platform_owner):
    return db.scalars(select(PlatformIncident).order_by(PlatformIncident.created_at.desc()).limit(300)).all()


@router.post("/incidents")
def create_platform_incident(payload: IncidentInput, db: Session = Depends(get_db), user=platform_owner):
    if payload.affected_scope == "institution" and not payload.school_id:
        raise HTTPException(status_code=422, detail="Select an institution for an institution-scoped incident")
    if payload.school_id:
        _school(db, payload.school_id)
    item = PlatformIncident(**payload.model_dump(), created_by=user.id)
    db.add(item)
    db.flush()
    _audit(db, user, "platform.incident.created", "platform_incident", str(item.id),
           {"title": item.title, "severity": item.severity, "scope": item.affected_scope})
    db.commit()
    db.refresh(item)
    return item


@router.patch("/incidents/{incident_id}")
def update_platform_incident(incident_id: int, payload: IncidentUpdate,
                             db: Session = Depends(get_db), user=platform_owner):
    item = db.get(PlatformIncident, incident_id)
    if not item:
        raise HTTPException(status_code=404, detail="Platform incident not found")
    item.status = payload.status
    item.severity = payload.severity or item.severity
    item.assigned_to = payload.assigned_to
    item.resolution_notes = payload.resolution_notes
    item.updated_at = datetime.utcnow()
    _audit(db, user, "platform.incident.updated", "platform_incident", str(item.id),
           {"status": item.status, "severity": item.severity})
    db.commit()
    db.refresh(item)
    return item


@router.get("/maintenance-windows")
def list_maintenance_windows(db: Session = Depends(get_db), user=platform_owner):
    return db.scalars(select(PlatformMaintenanceWindow).order_by(PlatformMaintenanceWindow.starts_at.desc()).limit(200)).all()


@router.post("/maintenance-windows")
def create_maintenance_window(payload: MaintenanceWindowInput, db: Session = Depends(get_db), user=platform_owner):
    if payload.ends_at <= payload.starts_at:
        raise HTTPException(status_code=422, detail="Maintenance end must be after start")
    item = PlatformMaintenanceWindow(**payload.model_dump(), created_by=user.id)
    db.add(item)
    db.flush()
    _audit(db, user, "platform.maintenance_window.created", "maintenance_window", str(item.id),
           {"title": item.title, "starts_at": item.starts_at.isoformat(), "ends_at": item.ends_at.isoformat()})
    db.commit()
    db.refresh(item)
    return item


@router.get("/infrastructure-health")
def infrastructure_health(db: Session = Depends(get_db), user=platform_owner):
    started = time.perf_counter()
    database = "healthy"
    try:
        db.execute(select(1))
        db_latency_ms = round((time.perf_counter() - started) * 1000, 2)
    except Exception:
        db.rollback()
        database = "unavailable"
        db_latency_ms = None
    disk_path = os.getenv("APP_DATA_DIR", "/")
    try:
        usage = shutil.disk_usage(disk_path)
        disk = {"path": disk_path, "total_bytes": usage.total, "used_bytes": usage.used,
                "free_bytes": usage.free, "used_percent": round(usage.used / usage.total * 100, 1)}
    except OSError:
        disk = {"path": disk_path, "status": "unavailable"}
    backup_dir = os.getenv("BACKUP_DIR")
    backup = {"configured": bool(backup_dir), "latest_file": None, "age_hours": None}
    if backup_dir and Path(backup_dir).is_dir():
        files = [p for p in Path(backup_dir).iterdir() if p.is_file() and p.suffix.lower() in {".sql", ".dump", ".backup", ".gz"}]
        if files:
            latest = max(files, key=lambda p: p.stat().st_mtime)
            backup = {"configured": True, "latest_file": latest.name,
                      "age_hours": round((time.time() - latest.stat().st_mtime) / 3600, 1)}
    load = os.getloadavg() if hasattr(os, "getloadavg") else None
    return {"api": "healthy", "database": database, "database_latency_ms": db_latency_ms,
            "disk": disk, "cpu_load_average": list(load) if load else None,
            "backup": backup, "ssl_domain_monitoring": "not_configured",
            "checked_at": datetime.utcnow().isoformat() + "Z"}


@router.get("/reports")
def platform_operations_report(db: Session = Depends(get_db), user=platform_owner):
    today = date.today()
    month_start = today.replace(day=1)
    schools = db.scalars(select(models.School).order_by(models.School.name)).all()
    rows = []
    for school in schools:
        active_subscription = db.scalar(select(models.ClientSubscription).where(
            models.ClientSubscription.school_id == school.id,
            models.ClientSubscription.status == "active"
        ).order_by(models.ClientSubscription.end_date.desc()).limit(1))
        users = db.scalar(select(func.count()).select_from(models.User).where(models.User.school_id == school.id)) or 0
        students = db.scalar(select(func.count()).select_from(models.Student).where(models.Student.school_id == school.id)) or 0
        staff = db.scalar(select(func.count()).select_from(models.Staff).where(models.Staff.school_id == school.id)) or 0
        received = db.scalar(select(func.coalesce(func.sum(models.ClientPayment.amount), 0)).where(
            models.ClientPayment.school_id == school.id, models.ClientPayment.status == "received",
            models.ClientPayment.payment_date >= month_start)) or Decimal("0")
        rows.append({"school_id": school.id, "institution": school.name, "type": school.institution_type,
                     "active": school.is_active, "users": users, "students": students, "staff": staff,
                     "subscription_end": active_subscription.end_date if active_subscription else None,
                     "received_this_month": str(received)})
    open_incidents = db.scalar(select(func.count()).select_from(PlatformIncident).where(
        PlatformIncident.status.notin_(["resolved", "closed"]))) or 0
    return {"generated_at": datetime.utcnow().isoformat() + "Z", "period_start": month_start,
            "institutions": len(rows), "active_institutions": sum(1 for r in rows if r["active"]),
            "open_platform_incidents": open_incidents, "clients": rows}
