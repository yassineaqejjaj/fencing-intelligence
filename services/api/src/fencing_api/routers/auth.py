import re
from datetime import timedelta

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

import structlog

from fencing_api.audit import write_audit
from fencing_api.config import Settings, get_settings
from fencing_api.database import get_db
from fencing_api.deps import (
    CSRF_HEADER,
    ORG_HEADER,
    SESSION_COOKIE,
    Principal,
    client_ip,
    enforce_rate_limit,
    get_principal,
    get_redis,
)
from fencing_api.errors import AppError
from fencing_api.mailer import send_email
from fencing_api.models import Organization, OrganizationMembership, PasswordResetToken, User
from fencing_api.models import Session as DbSession
from fencing_api.security import expiry_from_now, hash_password, hash_token, new_token, utcnow, validate_password_strength, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=200)
    display_name: str = Field(min_length=1, max_length=200)
    organization_name: str = Field(min_length=1, max_length=200)
    locale: str = "en"


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str
    password: str = Field(min_length=10, max_length=200)


class PasswordChangeIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=10, max_length=200)


class ProfileIn(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    locale: str | None = None


def _slug(db: Session, name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60] or "club"
    slug = base
    suffix = 2
    while db.scalar(select(Organization.id).where(Organization.slug == slug)):
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug


def _cookies(response: Response, token: str, csrf: str, settings: Settings) -> None:
    max_age = settings.session_days * 24 * 60 * 60
    response.set_cookie(SESSION_COOKIE, token, httponly=True, secure=settings.cookie_secure, samesite="lax", max_age=max_age, path="/")
    response.set_cookie("fi_csrf", csrf, httponly=False, secure=settings.cookie_secure, samesite="lax", max_age=max_age, path="/")


def _open_session(db: Session, user: User, request: Request, settings: Settings) -> tuple[str, str]:
    token = new_token()
    csrf = new_token()
    db.add(
        DbSession(
            user_id=user.id,
            token_hash=hash_token(token),
            csrf_token=csrf,
            expires_at=expiry_from_now(days=settings.session_days),
            user_agent=(request.headers.get("user-agent") or "")[:300],
            ip_address=client_ip(request, settings)[:64],
        )
    )
    return token, csrf


def _public_user(user: User, memberships: list[OrganizationMembership], organizations: dict) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "locale": user.locale,
        "memberships": [
            {
                "organization_id": str(item.organization_id),
                "organization_name": organizations[item.organization_id].name,
                "role": item.role,
            }
            for item in memberships
        ],
    }


@router.post("/register", status_code=201)
def register(
    payload: RegisterIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    cache=Depends(get_redis),
):
    if payload.locale not in {"en", "fr"}:
        raise AppError("invalid_locale", 422, "Locale must be en or fr")
    validate_password_strength(payload.password)
    enforce_rate_limit(cache, f"register:{client_ip(request, settings)}", settings.login_rate_limit, settings.login_rate_window_seconds)
    email = payload.email.lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise AppError("email_taken", 409, "An account with this email already exists")
    user = User(email=email, password_hash=hash_password(payload.password), display_name=payload.display_name.strip(), locale=payload.locale)
    db.add(user)
    db.flush()
    organization = Organization(name=payload.organization_name.strip(), slug=_slug(db, payload.organization_name))
    db.add(organization)
    db.flush()
    db.add(OrganizationMembership(organization_id=organization.id, user_id=user.id, role="administrator"))
    token, csrf = _open_session(db, user, request, settings)
    write_audit(db, organization_id=organization.id, actor_user_id=user.id, action="register", resource_type="user", resource_id=str(user.id), metadata={})
    db.commit()
    _cookies(response, token, csrf, settings)
    return {"user": _public_user(user, [OrganizationMembership(organization_id=organization.id, user_id=user.id, role="administrator")], {organization.id: organization}), "csrf_token": csrf, "organization_id": str(organization.id)}


@router.post("/login")
def login(payload: LoginIn, request: Request, response: Response, db: Session = Depends(get_db), settings: Settings = Depends(get_settings), cache=Depends(get_redis)):
    enforce_rate_limit(cache, f"login:{client_ip(request, settings)}:{payload.email.lower()}", settings.login_rate_limit, settings.login_rate_window_seconds)
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise AppError("invalid_credentials", 401, "Email or password is incorrect")
    token, csrf = _open_session(db, user, request, settings)
    db.commit()
    _cookies(response, token, csrf, settings)
    memberships = list(db.scalars(select(OrganizationMembership).where(OrganizationMembership.user_id == user.id)))
    orgs = {org.id: org for org in db.scalars(select(Organization).where(Organization.id.in_([item.organization_id for item in memberships])))}
    return {"user": _public_user(user, memberships, orgs), "csrf_token": csrf}


@router.post("/logout")
def logout(response: Response, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    db.delete(principal.session)
    db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie("fi_csrf", path="/")
    return {"ok": True}


@router.get("/me")
def me(principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    memberships = list(db.scalars(select(OrganizationMembership).where(OrganizationMembership.user_id == principal.user.id)))
    orgs = {org.id: org for org in db.scalars(select(Organization).where(Organization.id.in_([item.organization_id for item in memberships])))}
    return {"user": _public_user(principal.user, memberships, orgs), "organization_id": str(principal.organization.id), "role": principal.membership.role}


@router.patch("/me")
def update_me(payload: ProfileIn, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    if payload.locale is not None:
        if payload.locale not in {"en", "fr"}:
            raise AppError("invalid_locale", 422, "Locale must be en or fr")
        principal.user.locale = payload.locale
    if payload.display_name is not None:
        principal.user.display_name = payload.display_name.strip()
    db.commit()
    return {"ok": True, "display_name": principal.user.display_name, "locale": principal.user.locale}


@router.post("/change-password")
def change_password(payload: PasswordChangeIn, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    if not verify_password(payload.current_password, principal.user.password_hash):
        raise AppError("invalid_credentials", 401, "Current password is incorrect")
    validate_password_strength(payload.new_password)
    principal.user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"ok": True}


@router.post("/forgot-password")
def forgot_password(payload: ForgotIn, request: Request, db: Session = Depends(get_db), settings: Settings = Depends(get_settings), cache=Depends(get_redis)):
    enforce_rate_limit(cache, f"forgot:{client_ip(request, settings)}", 5, 300)
    user = db.scalar(select(User).where(User.email == payload.email.lower(), User.is_active.is_(True)))
    if user is not None:
        token = new_token()
        db.add(PasswordResetToken(user_id=user.id, token_hash=hash_token(token), expires_at=utcnow() + timedelta(hours=2)))
        db.commit()
        link = f"{settings.web_base_url}/reset-password?token={token}"
        sent = send_email(user.email, "Reset your Fencing Intelligence password", f"Open this link within two hours:\n{link}\n")
        if not sent:
            # Generic response on purpose (no account-oracle). The operator
            # must notice this log line and configure SMTP.
            structlog.get_logger().error("password_reset_email_unsent", user_id=str(user.id))
    return {"ok": True, "message": "If an account exists for that email, a reset link has been sent."}


@router.post("/reset-password")
def reset_password(payload: ResetIn, db: Session = Depends(get_db)):
    validate_password_strength(payload.password)
    row = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_token(payload.token)))
    if row is None or row.used_at is not None or row.expires_at <= utcnow():
        raise AppError("invalid_token", 400, "Reset link is invalid or expired")
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise AppError("invalid_token", 400, "Reset link is invalid or expired")
    user.password_hash = hash_password(payload.password)
    row.used_at = utcnow()
    db.commit()
    return {"ok": True}
