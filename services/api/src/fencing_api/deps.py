from dataclasses import dataclass

import redis
from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from fencing_api.config import Settings, get_settings
from fencing_api.database import get_db
from fencing_api.errors import AppError
from fencing_api.models import Organization, OrganizationMembership, Session as DbSession, User
from fencing_api.security import hash_token, utcnow

SESSION_COOKIE = "fi_session"
CSRF_HEADER = "X-CSRF-Token"
ORG_HEADER = "X-Organization-Id"

ROLE_RANK = {
    "viewer": 10,
    "athlete": 20,
    "analyst": 30,
    "coach": 40,
    "club_administrator": 50,
    "administrator": 60,
}
WRITE_ROLES = {"athlete", "analyst", "coach", "club_administrator", "administrator"}
UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}


@dataclass
class Principal:
    user: User
    organization: Organization
    membership: OrganizationMembership
    session: DbSession


def get_redis(settings: Settings = Depends(get_settings)) -> redis.Redis:
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


def enforce_rate_limit(cache: redis.Redis, key: str, limit: int, window: int) -> None:
    try:
        count = cache.incr(key)
        if count == 1:
            cache.expire(key, window)
    except redis.RedisError as exc:
        raise AppError("service_unavailable", 503, "Rate limiter is unavailable") from exc
    if count > limit:
        raise AppError("rate_limited", 429, "Too many attempts. Try again later.")


def get_principal(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Principal:
    raw = request.cookies.get(SESSION_COOKIE)
    if not raw:
        raise AppError("unauthenticated", 401, "Sign in required")
    record = db.scalar(select(DbSession).where(DbSession.token_hash == hash_token(raw)))
    if record is None or record.expires_at <= utcnow():
        raise AppError("unauthenticated", 401, "Sign in required")
    if request.method in UNSAFE:
        sent = request.headers.get(CSRF_HEADER, "")
        if not sent or sent != record.csrf_token:
            raise AppError("csrf", 403, "CSRF token missing or invalid")
    user = db.get(User, record.user_id)
    if user is None or not user.is_active:
        raise AppError("unauthenticated", 401, "Sign in required")
    org_id = request.headers.get(ORG_HEADER)
    memberships = list(db.scalars(select(OrganizationMembership).where(OrganizationMembership.user_id == user.id)))
    if org_id:
        membership = next((item for item in memberships if str(item.organization_id) == org_id), None)
        if membership is None:
            raise AppError("forbidden", 403, "Not a member of this organization")
    elif len(memberships) == 1:
        membership = memberships[0]
    elif len(memberships) == 0:
        raise AppError("forbidden", 403, "No organization membership")
    else:
        raise AppError("organization_required", 400, "Send X-Organization-Id")
    organization = db.get(Organization, membership.organization_id)
    if organization is None:
        raise AppError("not_found", 404, "Organization not found")
    return Principal(user=user, organization=organization, membership=membership, session=record)


def require_role(minimum: str):
    def dependency(principal: Principal = Depends(get_principal)) -> Principal:
        if ROLE_RANK[principal.membership.role] < ROLE_RANK[minimum]:
            raise AppError("forbidden", 403, "Insufficient role")
        return principal

    return dependency


def client_ip(request: Request, settings: Settings) -> str:
    if settings.trust_proxy:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    if request.client is None:
        return ""
    return request.client.host
