import uuid

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from fencing_domain.recommendations import attach_video_references, recommend
from fencing_domain.taxonomy import TARGET_AREAS

from fencing_api.database import get_db
from fencing_api.deps import Principal, require_role
from fencing_api.errors import AppError
from fencing_api.models import Annotation, Exercise, Recommendation, Report, TrainingAssignment, TrainingSession
from fencing_api.services.access import require_athlete, require_bout
from fencing_api.services.reports import annotations_csv, build_performance_pdf, safe_filename
from fencing_api.services.stats_service import athlete_names, collect_athlete, collect_bout, collect_bout_momentum, collect_bout_reading, collect_intelligence
from fencing_api.storage import presign_get, upload_bytes

router = APIRouter(tags=["insights"])


class ReportIn(BaseModel):
    kind: str
    athlete_id: uuid.UUID | None = None
    bout_id: uuid.UUID | None = None
    title: str = ""


class SessionIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    athlete_id: uuid.UUID | None = None
    scheduled_for: str | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=600)
    rpe: int | None = Field(default=None, ge=1, le=10)
    coach_notes: str = ""
    athlete_feedback: str = ""


class AssignmentIn(BaseModel):
    exercise_id: uuid.UUID
    athlete_id: uuid.UUID
    session_id: uuid.UUID | None = None
    note: str = ""


@router.get("/athletes/{athlete_id}/statistics")
def athlete_stats(athlete_id: uuid.UUID, weapon: str | None = None, principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    require_athlete(db, principal, athlete_id)
    stats = collect_athlete(db, principal.organization.id, athlete_id, weapon=weapon)
    stats["athlete_names"] = athlete_names(db, principal.organization.id)
    return stats


@router.get("/athletes/{athlete_id}/intelligence")
def athlete_intelligence_view(athlete_id: uuid.UUID, weapon: str | None = None, principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    """Tactical readings and plain-language insight cards from validated records only."""
    require_athlete(db, principal, athlete_id)
    payload = collect_intelligence(db, principal.organization.id, athlete_id, weapon=weapon)
    payload["athlete_names"] = athlete_names(db, principal.organization.id)
    return payload


@router.get("/bouts/{bout_id}/statistics")
def bout_stats(bout_id: uuid.UUID, principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    bout = require_bout(db, principal, bout_id)
    stats = collect_bout(db, bout)
    stats["athlete_names"] = athlete_names(db, principal.organization.id)
    return stats


@router.get("/bouts/{bout_id}/reading")
def bout_reading_view(bout_id: uuid.UUID, principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    """Strengths and weaknesses of one bout. Validated touches and validated video marks only."""
    bout = require_bout(db, principal, bout_id)
    payload = collect_bout_reading(db, bout)
    payload["athlete_names"] = athlete_names(db, principal.organization.id)
    return payload


@router.get("/bouts/{bout_id}/momentum")
def bout_momentum_view(bout_id: uuid.UUID, principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    """Running score, scoring runs, and lead changes rebuilt from validated valid touches."""
    bout = require_bout(db, principal, bout_id)
    payload = collect_bout_momentum(db, bout)
    payload["athlete_names"] = athlete_names(db, principal.organization.id)
    return payload


@router.get("/videos/{video_id}/statistics")
def video_stats(video_id: uuid.UUID, principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    from fencing_api.services.access import require_video

    video = require_video(db, principal, video_id)
    if video.athlete_id is None:
        return {"data_status": "no_validated_data", "reason": "Video has no linked athlete"}
    stats = collect_athlete(db, principal.organization.id, video.athlete_id, weapon=video.weapon)
    return stats


@router.get("/clubs/{club_id}/statistics")
def club_stats(club_id: uuid.UUID, principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    from fencing_api.models import Athlete, Club
    from fencing_api.services.access import same_org

    same_org(db.get(Club, club_id), principal.organization.id, "Club")
    athletes = db.scalars(select(Athlete).where(Athlete.organization_id == principal.organization.id, Athlete.club_id == club_id)).all()
    items = []
    for athlete in athletes:
        stats = collect_athlete(db, principal.organization.id, athlete.id)
        block = stats.get("combined") or {}
        items.append(
            {
                "athlete_id": str(athlete.id),
                "display_name": athlete.display_name,
                "data_status": stats["data_status"],
                "touches_scored": block.get("touches_scored"),
                "touches_conceded": block.get("touches_conceded"),
                "offensive_success_rate": block.get("offensive_success_rate"),
            }
        )
    return {"club_id": str(club_id), "athletes": items, "data_status": "ok" if any(item["data_status"] == "ok" for item in items) else "no_validated_data"}


@router.get("/athletes/{athlete_id}/recommendations")
def live_recommendations(athlete_id: uuid.UUID, principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    require_athlete(db, principal, athlete_id)
    stats = collect_athlete(db, principal.organization.id, athlete_id)
    suggestions = recommend(stats)
    rows = db.scalars(select(Annotation).where(Annotation.organization_id == principal.organization.id, Annotation.actor_athlete_id == athlete_id)).all()
    payload = [
        {
            "id": str(row.id),
            "validated": row.status == "validated",
            "action_code": row.action_type_code,
            "outcome": row.outcome,
            "weapon": None,
            "video_id": str(row.video_id),
            "start_ms": row.start_ms,
        }
        for row in rows
    ]
    attach_video_references(suggestions, payload)
    for item in suggestions:
        exercise = db.scalar(select(Exercise).where(Exercise.code == item["exercise_code"], Exercise.organization_id.is_(None)))
        item["exercise_id"] = str(exercise.id) if exercise else None
    return {"data_status": stats["data_status"], "items": suggestions}


@router.post("/athletes/{athlete_id}/recommendations", status_code=201)
def save_recommendations(athlete_id: uuid.UUID, principal: Principal = Depends(require_role("coach")), db: Session = Depends(get_db)):
    require_athlete(db, principal, athlete_id)
    live = live_recommendations(athlete_id, principal, db)
    saved = []
    for item in live["items"]:
        exercise_id = uuid.UUID(item["exercise_id"]) if item.get("exercise_id") else None
        row = Recommendation(
            organization_id=principal.organization.id,
            athlete_id=athlete_id,
            exercise_id=exercise_id,
            observation=item["observation"],
            evidence=item["evidence"],
            video_references=item["video_references"],
            evidence_level=item["evidence_level"],
            narrative=item["observation"],
        )
        db.add(row)
        db.flush()
        saved.append(str(row.id))
    db.commit()
    return {"ids": saved, "count": len(saved)}


@router.get("/training/exercises")
def list_exercises(principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Exercise).where((Exercise.organization_id.is_(None)) | (Exercise.organization_id == principal.organization.id)).order_by(Exercise.name_en)
    ).all()
    return {
        "items": [
            {
                "id": str(row.id),
                "code": row.code,
                "name_en": row.name_en,
                "name_fr": row.name_fr,
                "description_en": row.description_en,
                "description_fr": row.description_fr,
                "weapons": row.weapons,
                "duration_minutes": row.duration_minutes,
            }
            for row in rows
        ]
    }


@router.get("/training/sessions")
def list_sessions(principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    rows = db.scalars(select(TrainingSession).where(TrainingSession.organization_id == principal.organization.id).order_by(TrainingSession.scheduled_for.desc().nulls_last())).all()
    return {"items": [_session_out(row) for row in rows]}


@router.post("/training/sessions", status_code=201)
def create_session(payload: SessionIn, principal: Principal = Depends(require_role("coach")), db: Session = Depends(get_db)):
    if payload.athlete_id:
        require_athlete(db, principal, payload.athlete_id)
    from datetime import datetime

    scheduled = datetime.fromisoformat(payload.scheduled_for) if payload.scheduled_for else None
    row = TrainingSession(
        organization_id=principal.organization.id,
        athlete_id=payload.athlete_id,
        coach_user_id=principal.user.id,
        title=payload.title.strip(),
        scheduled_for=scheduled,
        duration_minutes=payload.duration_minutes,
        rpe=payload.rpe,
        coach_notes=payload.coach_notes,
        athlete_feedback=payload.athlete_feedback,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _session_out(row)


def _session_out(row: TrainingSession) -> dict:
    load = None
    if row.duration_minutes is not None and row.rpe is not None:
        load = row.duration_minutes * row.rpe
    return {
        "id": str(row.id),
        "title": row.title,
        "athlete_id": str(row.athlete_id) if row.athlete_id else None,
        "scheduled_for": row.scheduled_for.isoformat() if row.scheduled_for else None,
        "duration_minutes": row.duration_minutes,
        "rpe": row.rpe,
        "training_load": load,
        "training_load_reason": None if load is not None else "duration_or_rpe_missing",
        "coach_notes": row.coach_notes,
        "athlete_feedback": row.athlete_feedback,
    }


@router.post("/training/assignments", status_code=201)
def assign_exercise(payload: AssignmentIn, principal: Principal = Depends(require_role("coach")), db: Session = Depends(get_db)):
    require_athlete(db, principal, payload.athlete_id)
    exercise = db.get(Exercise, payload.exercise_id)
    if exercise is None or (exercise.organization_id not in {None, principal.organization.id}):
        raise AppError("not_found", 404, "Exercise not found")
    row = TrainingAssignment(
        organization_id=principal.organization.id,
        session_id=payload.session_id,
        exercise_id=exercise.id,
        athlete_id=payload.athlete_id,
        note=payload.note,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": str(row.id), "status": row.status, "exercise_id": str(row.exercise_id), "athlete_id": str(row.athlete_id)}


@router.get("/training/load")
def training_load(athlete_id: uuid.UUID, principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    require_athlete(db, principal, athlete_id)
    rows = db.scalars(select(TrainingSession).where(TrainingSession.organization_id == principal.organization.id, TrainingSession.athlete_id == athlete_id)).all()
    points = []
    for row in rows:
        item = _session_out(row)
        points.append({"session_id": item["id"], "scheduled_for": item["scheduled_for"], "training_load": item["training_load"], "reason": item["training_load_reason"]})
    return {"athlete_id": str(athlete_id), "points": points}


@router.post("/reports", status_code=201)
def create_report(payload: ReportIn, principal: Principal = Depends(require_role("analyst")), db: Session = Depends(get_db)):
    if payload.kind not in {"athlete", "bout", "coach"}:
        raise AppError("invalid_report", 422, "Report kind must be athlete, bout, or coach")
    athlete = require_athlete(db, principal, payload.athlete_id) if payload.athlete_id else None
    bout = require_bout(db, principal, payload.bout_id) if payload.bout_id else None
    if athlete is None and bout is not None:
        from fencing_api.services.access import bout_sides

        sides = bout_sides(db, bout.id)
        left = sides.get("left")
        if left is None:
            raise AppError("invalid_report", 422, "Bout has no left athlete")
        athlete = require_athlete(db, principal, left.athlete_id)
    if athlete is None:
        raise AppError("invalid_report", 422, "A report needs an athlete")
    stats = collect_athlete(db, principal.organization.id, athlete.id)
    model_note = "none — this report uses validated human records only"
    pdf = build_performance_pdf(title=payload.title or f"{athlete.display_name} performance", athlete_name=athlete.display_name, stats=stats, model_note=model_note)
    report_id = uuid.uuid4()
    key = f"org/{principal.organization.id}/reports/{report_id}.pdf"
    upload_bytes(pdf, key, "application/pdf")
    row = Report(
        id=report_id,
        organization_id=principal.organization.id,
        athlete_id=athlete.id,
        bout_id=bout.id if bout else payload.bout_id,
        kind=payload.kind,
        title=payload.title or f"{athlete.display_name} performance",
        storage_key=key,
        content_type="application/pdf",
        source={"formula_version": "1", "model": None, "data_status": stats["data_status"]},
        created_by=principal.user.id,
    )
    db.add(row)
    db.commit()
    return {"id": str(row.id), "title": row.title, "kind": row.kind, "download_path": f"/api/v1/reports/{row.id}/download"}


@router.get("/reports")
def list_reports(principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    rows = db.scalars(select(Report).where(Report.organization_id == principal.organization.id).order_by(Report.created_at.desc())).all()
    return {"items": [{"id": str(row.id), "title": row.title, "kind": row.kind, "athlete_id": str(row.athlete_id) if row.athlete_id else None, "created_at": row.created_at.isoformat()} for row in rows]}


@router.get("/reports/{report_id}/download")
def download_report(report_id: uuid.UUID, principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    row = db.get(Report, report_id)
    if row is None or row.organization_id != principal.organization.id:
        raise AppError("not_found", 404, "Report not found")
    return {"url": presign_get(row.storage_key, download_name=f"{safe_filename(row.title)}.pdf"), "expires_in": 900}


@router.get("/athletes/{athlete_id}/export.json")
def export_json(athlete_id: uuid.UUID, principal: Principal = Depends(require_role("analyst")), db: Session = Depends(get_db)):
    athlete = require_athlete(db, principal, athlete_id)
    stats = collect_athlete(db, principal.organization.id, athlete.id)
    annotations = db.scalars(select(Annotation).where(Annotation.organization_id == principal.organization.id, Annotation.actor_athlete_id == athlete.id)).all()
    return {
        "athlete": {"id": str(athlete.id), "display_name": athlete.display_name, "weapon": athlete.weapon},
        "statistics": stats,
        "annotations": [
            {"id": str(row.id), "video_id": str(row.video_id), "action_type_code": row.action_type_code, "status": row.status, "outcome": row.outcome, "start_ms": row.start_ms, "end_ms": row.end_ms, "target_area": row.target_area}
            for row in annotations
        ],
        "target_areas": list(TARGET_AREAS),
    }


@router.get("/athletes/{athlete_id}/export.csv")
def export_csv(athlete_id: uuid.UUID, principal: Principal = Depends(require_role("analyst")), db: Session = Depends(get_db)):
    athlete = require_athlete(db, principal, athlete_id)
    annotations = db.scalars(select(Annotation).where(Annotation.organization_id == principal.organization.id, Annotation.actor_athlete_id == athlete.id)).all()
    payload = [
        {"id": str(row.id), "video_id": str(row.video_id), "action_type_code": row.action_type_code, "status": row.status, "outcome": row.outcome or "", "start_ms": row.start_ms, "end_ms": row.end_ms, "target_area": row.target_area or "", "actor_athlete_id": str(row.actor_athlete_id or "")}
        for row in annotations
    ]
    return Response(content=annotations_csv(payload), media_type="text/csv")
