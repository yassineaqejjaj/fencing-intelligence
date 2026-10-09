import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fencing_domain.taxonomy import OUTCOMES, action_by_code

from fencing_api.database import get_db
from fencing_api.deps import Principal, require_role
from fencing_api.errors import AppError
from fencing_api.models import Action, Annotation, AnnotationVersion, Athlete, FencingPhrase, TagTemplate, Video
from fencing_api.services.access import can_read_video, require_athlete, require_video

router = APIRouter(tags=["annotations"])
MODES = {"simplified", "tactical", "technical"}


class AnnotationIn(BaseModel):
    mode: str
    action_type_code: str
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    actor_athlete_id: uuid.UUID | None = None
    opponent_athlete_id: uuid.UUID | None = None
    phrase_id: uuid.UUID | None = None
    target_area: str | None = None
    piste_position: float | None = None
    outcome: str | None = None
    body: dict = Field(default_factory=dict)
    notes: str = ""
    status: str = "draft"


class PhraseIn(BaseModel):
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    notes: str = ""
    validated: bool = False


class TemplateIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    mode: str
    action_type_code: str
    body: dict = Field(default_factory=dict)


def _check(payload: AnnotationIn, db: Session, principal: Principal) -> None:
    if payload.mode not in MODES:
        raise AppError("invalid_mode", 422, "Mode must be simplified, tactical, or technical")
    if action_by_code(payload.action_type_code) is None:
        raise AppError("unknown_action", 422, "Unknown fencing action")
    if payload.end_ms < payload.start_ms:
        raise AppError("invalid_time", 422, "Action end is before its start")
    if payload.outcome is not None and payload.outcome not in OUTCOMES:
        raise AppError("invalid_outcome", 422, "Unknown outcome")
    if payload.piste_position is not None and not 0 <= payload.piste_position <= 1:
        raise AppError("invalid_position", 422, "Piste position must be between 0 and 1")
    if payload.status not in {"draft", "validated", "rejected"}:
        raise AppError("invalid_status", 422, "Unknown annotation status")
    if len(str(payload.body)) > 20000:
        raise AppError("payload_too_large", 413, "Annotation details are too large")
    for athlete_id in (payload.actor_athlete_id, payload.opponent_athlete_id):
        if athlete_id is not None:
            require_athlete(db, principal, athlete_id)


def _out(row: Annotation) -> dict:
    return {
        "id": str(row.id),
        "video_id": str(row.video_id),
        "phrase_id": str(row.phrase_id) if row.phrase_id else None,
        "mode": row.mode,
        "status": row.status,
        "source": row.source,
        "actor_athlete_id": str(row.actor_athlete_id) if row.actor_athlete_id else None,
        "opponent_athlete_id": str(row.opponent_athlete_id) if row.opponent_athlete_id else None,
        "action_type_code": row.action_type_code,
        "start_ms": row.start_ms,
        "end_ms": row.end_ms,
        "target_area": row.target_area,
        "piste_position": row.piste_position,
        "outcome": row.outcome,
        "body": row.body,
        "notes": row.notes,
        "confidence": row.confidence,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _snapshot(row: Annotation) -> dict:
    data = _out(row)
    data.pop("created_at", None)
    data.pop("updated_at", None)
    return data


def _sync_action(db: Session, row: Annotation) -> None:
    action = db.scalar(select(Action).where(Action.annotation_id == row.id))
    if action is None:
        action = Action(annotation_id=row.id, organization_id=row.organization_id, video_id=row.video_id)
        db.add(action)
    action.phrase_id = row.phrase_id
    action.actor_athlete_id = row.actor_athlete_id
    action.action_type_code = row.action_type_code
    action.start_ms = row.start_ms
    action.end_ms = row.end_ms
    action.target_area = row.target_area
    action.outcome = row.outcome


def _version(db: Session, row: Annotation, editor) -> None:
    current = db.scalar(select(func.max(AnnotationVersion.version)).where(AnnotationVersion.annotation_id == row.id))
    db.add(AnnotationVersion(annotation_id=row.id, version=(current or 0) + 1, snapshot=_snapshot(row), editor_id=editor))


@router.get("/videos/{video_id}/annotations")
def list_annotations(video_id: uuid.UUID, principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    video = require_video(db, principal, video_id)
    rows = db.scalars(select(Annotation).where(Annotation.video_id == video.id).order_by(Annotation.start_ms)).all()
    return {"items": [_out(row) for row in rows]}


@router.post("/videos/{video_id}/annotations", status_code=201)
def create_annotation(video_id: uuid.UUID, payload: AnnotationIn, principal: Principal = Depends(require_role("athlete")), db: Session = Depends(get_db)):
    video = require_video(db, principal, video_id)
    if principal.membership.role == "viewer":
        raise AppError("forbidden", 403, "Viewers cannot annotate")
    _check(payload, db, principal)
    row = Annotation(
        organization_id=principal.organization.id,
        video_id=video.id,
        phrase_id=payload.phrase_id,
        mode=payload.mode,
        status=payload.status,
        source="human",
        actor_athlete_id=payload.actor_athlete_id,
        opponent_athlete_id=payload.opponent_athlete_id,
        action_type_code=payload.action_type_code,
        start_ms=payload.start_ms,
        end_ms=payload.end_ms,
        target_area=payload.target_area,
        piste_position=payload.piste_position,
        outcome=payload.outcome,
        body=payload.body,
        notes=payload.notes,
        created_by=principal.user.id,
    )
    db.add(row)
    db.flush()
    _sync_action(db, row)
    _version(db, row, principal.user.id)
    db.commit()
    db.refresh(row)
    return _out(row)


@router.patch("/annotations/{annotation_id}")
def update_annotation(annotation_id: uuid.UUID, payload: AnnotationIn, principal: Principal = Depends(require_role("athlete")), db: Session = Depends(get_db)):
    row = db.get(Annotation, annotation_id)
    if row is None or row.organization_id != principal.organization.id:
        raise AppError("not_found", 404, "Annotation not found")
    require_video(db, principal, row.video_id)
    _check(payload, db, principal)
    _version(db, row, principal.user.id)
    row.mode = payload.mode
    row.status = payload.status
    row.actor_athlete_id = payload.actor_athlete_id
    row.opponent_athlete_id = payload.opponent_athlete_id
    row.phrase_id = payload.phrase_id
    row.action_type_code = payload.action_type_code
    row.start_ms = payload.start_ms
    row.end_ms = payload.end_ms
    row.target_area = payload.target_area
    row.piste_position = payload.piste_position
    row.outcome = payload.outcome
    row.body = payload.body
    row.notes = payload.notes
    _sync_action(db, row)
    db.commit()
    return _out(row)


@router.post("/annotations/{annotation_id}/validate")
def validate_annotation(annotation_id: uuid.UUID, principal: Principal = Depends(require_role("athlete")), db: Session = Depends(get_db)):
    row = db.get(Annotation, annotation_id)
    if row is None or row.organization_id != principal.organization.id:
        raise AppError("not_found", 404, "Annotation not found")
    require_video(db, principal, row.video_id)
    _version(db, row, principal.user.id)
    row.status = "validated"
    db.commit()
    return _out(row)


@router.post("/annotations/{annotation_id}/reject")
def reject_annotation(annotation_id: uuid.UUID, principal: Principal = Depends(require_role("athlete")), db: Session = Depends(get_db)):
    """Mark a suggestion as wrong. Rejected rows stay for model evaluation and never count in statistics."""
    row = db.get(Annotation, annotation_id)
    if row is None or row.organization_id != principal.organization.id:
        raise AppError("not_found", 404, "Annotation not found")
    require_video(db, principal, row.video_id)
    _version(db, row, principal.user.id)
    row.status = "rejected"
    db.commit()
    return _out(row)


@router.get("/review-queue")
def review_queue(limit: int = 50, principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    """Draft annotations waiting for a human decision, newest first, limited to videos the caller may read."""
    limit = max(1, min(limit, 200))
    rows = db.scalars(
        select(Annotation)
        .where(Annotation.organization_id == principal.organization.id, Annotation.status == "draft")
        .order_by(Annotation.created_at.desc())
        .limit(limit * 4)
    ).all()
    total_drafts = db.scalar(select(func.count(Annotation.id)).where(Annotation.organization_id == principal.organization.id, Annotation.status == "draft")) or 0
    videos: dict[uuid.UUID, Video | None] = {}
    athletes: dict[uuid.UUID, str] = {}
    items = []
    for row in rows:
        if row.video_id not in videos:
            video = db.get(Video, row.video_id)
            videos[row.video_id] = video if video is not None and can_read_video(db, principal, video) else None
        video = videos[row.video_id]
        if video is None:
            continue
        for athlete_id in (row.actor_athlete_id, row.opponent_athlete_id):
            if athlete_id and athlete_id not in athletes:
                athlete = db.get(Athlete, athlete_id)
                athletes[athlete_id] = athlete.display_name if athlete else ""
        spec = action_by_code(row.action_type_code)
        items.append(
            {
                **_out(row),
                "video_title": video.title,
                "actor_name": athletes.get(row.actor_athlete_id, "") if row.actor_athlete_id else "",
                "opponent_name": athletes.get(row.opponent_athlete_id, "") if row.opponent_athlete_id else "",
                "action_label_en": spec.label_en if spec else row.action_type_code,
                "action_label_fr": spec.label_fr if spec else row.action_type_code,
                "experimental": bool(spec.experimental) if spec else False,
            }
        )
        if len(items) >= limit:
            break
    by_source: dict[str, int] = {}
    for item in items:
        by_source[item["source"]] = by_source.get(item["source"], 0) + 1
    return {"items": items, "pending_total": int(total_drafts), "by_source": by_source}


@router.get("/annotations/{annotation_id}/versions")
def versions(annotation_id: uuid.UUID, principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    row = db.get(Annotation, annotation_id)
    if row is None or row.organization_id != principal.organization.id:
        raise AppError("not_found", 404, "Annotation not found")
    require_video(db, principal, row.video_id)
    history = db.scalars(select(AnnotationVersion).where(AnnotationVersion.annotation_id == row.id).order_by(AnnotationVersion.version)).all()
    return {"items": [{"version": item.version, "snapshot": item.snapshot, "created_at": item.created_at.isoformat()} for item in history]}


@router.delete("/annotations/{annotation_id}")
def delete_annotation(annotation_id: uuid.UUID, principal: Principal = Depends(require_role("analyst")), db: Session = Depends(get_db)):
    row = db.get(Annotation, annotation_id)
    if row is None or row.organization_id != principal.organization.id:
        raise AppError("not_found", 404, "Annotation not found")
    require_video(db, principal, row.video_id)
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/videos/{video_id}/phrases")
def list_phrases(video_id: uuid.UUID, principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    video = require_video(db, principal, video_id)
    rows = db.scalars(select(FencingPhrase).where(FencingPhrase.video_id == video.id).order_by(FencingPhrase.start_ms)).all()
    return {"items": [_phrase(row) for row in rows]}


@router.post("/videos/{video_id}/phrases", status_code=201)
def create_phrase(video_id: uuid.UUID, payload: PhraseIn, principal: Principal = Depends(require_role("athlete")), db: Session = Depends(get_db)):
    video = require_video(db, principal, video_id)
    if payload.end_ms <= payload.start_ms:
        raise AppError("invalid_time", 422, "Phrase end must be after its start")
    row = FencingPhrase(
        organization_id=principal.organization.id,
        video_id=video.id,
        bout_id=video.bout_id,
        start_ms=payload.start_ms,
        end_ms=payload.end_ms,
        notes=payload.notes,
        validated=payload.validated,
        source="human",
        created_by=principal.user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _phrase(row)


def _phrase(row: FencingPhrase) -> dict:
    return {
        "id": str(row.id),
        "video_id": str(row.video_id),
        "start_ms": row.start_ms,
        "end_ms": row.end_ms,
        "validated": row.validated,
        "source": row.source,
        "notes": row.notes,
    }


@router.get("/tag-templates")
def list_templates(principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    rows = db.scalars(select(TagTemplate).where(TagTemplate.organization_id == principal.organization.id).order_by(TagTemplate.name)).all()
    return {"items": [_template(row) for row in rows]}


@router.post("/tag-templates", status_code=201)
def create_template(payload: TemplateIn, principal: Principal = Depends(require_role("coach")), db: Session = Depends(get_db)):
    if payload.mode not in MODES or action_by_code(payload.action_type_code) is None:
        raise AppError("invalid_template", 422, "Template mode or action is unknown")
    row = TagTemplate(
        organization_id=principal.organization.id,
        name=payload.name.strip(),
        mode=payload.mode,
        action_type_code=payload.action_type_code,
        body=payload.body,
        created_by=principal.user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _template(row)


def _template(row: TagTemplate) -> dict:
    return {"id": str(row.id), "name": row.name, "mode": row.mode, "action_type_code": row.action_type_code, "body": row.body}


@router.get("/action-types")
def action_types(principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    from fencing_api.models import ActionType

    rows = db.scalars(select(ActionType).order_by(ActionType.category, ActionType.code)).all()
    return {
        "items": [
            {
                "code": row.code,
                "category": row.category,
                "label_en": row.label_en,
                "label_fr": row.label_fr,
                "weapons": row.weapons,
                "experimental": row.experimental,
                "rule_source": row.rule_source,
                "rule_version": row.rule_version,
            }
            for row in rows
        ]
    }
