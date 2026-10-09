from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from fencing_api.audit import write_audit
from fencing_api.database import get_db
from fencing_api.deps import Principal, get_principal
from fencing_api.errors import AppError
from fencing_api.models import Annotation, ConsentRecord, OrganizationMembership, Session as DbSession, Video
from fencing_api.security import hash_password, utcnow, verify_password
from fencing_api.storage import delete_key

router = APIRouter(prefix="/privacy", tags=["privacy"])


class DeleteIn(BaseModel):
    password: str
    delete_uploaded_videos: bool = False


class ConsentIn(BaseModel):
    granted: bool
    purpose: str = "research_training"


@router.get("/export")
def export_account(principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    memberships = db.scalars(select(OrganizationMembership).where(OrganizationMembership.user_id == principal.user.id)).all()
    consents = db.scalars(select(ConsentRecord).where(ConsentRecord.user_id == principal.user.id)).all()
    annotations = db.scalars(select(Annotation).where(Annotation.created_by == principal.user.id)).all()
    return {
        "user": {
            "id": str(principal.user.id),
            "email": principal.user.email,
            "display_name": principal.user.display_name,
            "locale": principal.user.locale,
        },
        "memberships": [{"organization_id": str(item.organization_id), "role": item.role} for item in memberships],
        "consents": [{"purpose": item.purpose, "granted": item.granted, "policy_version": item.policy_version} for item in consents],
        "annotations_created": [
            {"id": str(item.id), "video_id": str(item.video_id), "action_type_code": item.action_type_code} for item in annotations
        ],
    }


@router.post("/consent")
def set_consent(payload: ConsentIn, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    if payload.purpose != "research_training":
        raise AppError("invalid_purpose", 422, "Only research_training consent is available")
    db.add(
        ConsentRecord(
            organization_id=principal.organization.id,
            user_id=principal.user.id,
            purpose=payload.purpose,
            granted=payload.granted,
            policy_version="1",
        )
    )
    db.commit()
    return {"ok": True, "granted": payload.granted}


@router.post("/delete-account")
def delete_account(payload: DeleteIn, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    if not verify_password(payload.password, principal.user.password_hash):
        raise AppError("invalid_credentials", 401, "Password is incorrect")
    if payload.delete_uploaded_videos:
        videos = db.scalars(select(Video).where(Video.created_by == principal.user.id, Video.deleted_at.is_(None))).all()
        for video in videos:
            if video.organization_id != principal.organization.id:
                continue
            for key in {video.storage_key, video.playback_key, video.thumbnail_key}:
                delete_key(key)
            video.deleted_at = utcnow()
    user = principal.user
    write_audit(
        db,
        organization_id=principal.organization.id,
        actor_user_id=user.id,
        action="delete_account",
        resource_type="user",
        resource_id=str(user.id),
    )
    user.email = f"deleted-{user.id}@invalid.local"
    user.display_name = "Deleted user"
    user.password_hash = hash_password(f"disabled-{user.id}")
    user.is_active = False
    for session in db.scalars(select(DbSession).where(DbSession.user_id == user.id)).all():
        db.delete(session)
    db.commit()
    return {"ok": True}
