from sqlalchemy.orm import Session

from fencing_api.models import AuditLog


REDACT = {"password", "password_hash", "token", "csrf_token", "authorization"}


def write_audit(
    db: Session,
    *,
    organization_id,
    actor_user_id,
    action: str,
    resource_type: str,
    resource_id: str,
    metadata: dict | None = None,
) -> None:
    clean = {}
    for key, value in (metadata or {}).items():
        if key.lower() in REDACT:
            continue
        clean[key] = value
    db.add(
        AuditLog(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            metadata_json=clean,
        )
    )
