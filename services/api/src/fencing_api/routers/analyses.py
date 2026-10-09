import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ml_inference.movement import classify_track
from ml_inference.scoreboard import calibrated_distance_m, detect_light_candidates

from fencing_api.database import get_db
from fencing_api.deps import Principal, require_role
from fencing_api.errors import AppError
from fencing_api.models import AnalysisRun, Annotation, InferenceResult, ModelVersion, PoseSequence, ScoreEvent
from fencing_api.security import utcnow
from fencing_api.services.access import require_video
from fencing_api.storage import download_file
from fencing_domain.taxonomy import action_by_code

router = APIRouter(tags=["analyses"])
KNOWN = {"advance", "retreat", "lunge", "fleche", "en_garde", "attack"}


class AnalysisIn(BaseModel):
    kind: str
    samples: list[dict] = Field(default_factory=list)
    forward: str | None = None


class DistanceIn(BaseModel):
    point_a: dict
    point_b: dict


@router.post("/videos/{video_id}/analyses", status_code=201)
def create_analysis(video_id: uuid.UUID, payload: AnalysisIn, principal: Principal = Depends(require_role("analyst")), db: Session = Depends(get_db)):
    video = require_video(db, principal, video_id)
    if payload.kind == "movement":
        return _movement(db, principal, video, payload)
    if payload.kind == "scoreboard":
        return _scoreboard(db, principal, video)
    if payload.kind == "pose":
        return _pose(db, principal, video)
    raise AppError("unsupported_analysis", 400, "Supported analyses are movement, scoreboard, and pose")


def _model(db: Session, name: str) -> ModelVersion | None:
    from sqlalchemy import select

    return db.scalar(select(ModelVersion).where(ModelVersion.name == name, ModelVersion.version == "0.1.0"))


def _movement(db, principal, video, payload: AnalysisIn) -> dict:
    model = _model(db, "heuristic-movement")
    run = AnalysisRun(
        organization_id=principal.organization.id,
        video_id=video.id,
        kind="heuristic_movement",
        status="running",
        model_version_id=model.id if model else None,
        parameters={"forward": payload.forward},
        created_by=principal.user.id,
    )
    db.add(run)
    db.flush()
    if payload.forward not in {None, "image_left", "image_right"}:
        raise AppError("invalid_direction", 422, "forward must be image_left or image_right")
    labels = classify_track(payload.samples, forward=payload.forward)
    created = 0
    for label in labels:
        code = label["label"]
        if code not in KNOWN or action_by_code(code) is None:
            continue
        db.add(
            Annotation(
                organization_id=principal.organization.id,
                video_id=video.id,
                analysis_run_id=run.id,
                mode="technical",
                status="draft",
                source="heuristic",
                action_type_code=code,
                start_ms=int(label["start_ms"]),
                end_ms=int(label["end_ms"]),
                body={"experimental": True, "peak_speed": label.get("peak_speed")},
                confidence=None,
                notes="Heuristic suggestion. It is not a validated fencing action.",
                created_by=principal.user.id,
            )
        )
        created += 1
    db.add(
        InferenceResult(
            analysis_run_id=run.id,
            video_id=video.id,
            model_version_id=model.id if model else None,
            kind="movement",
            payload={"labels": labels, "draft_annotations": created, "claim_accuracy": False},
        )
    )
    run.status = "succeeded"
    run.finished_at = utcnow()
    run.summary = {
        "experimental": True,
        "claim_accuracy": False,
        "draft_annotations": created,
        "raw_segments": len(labels),
        "direction_provided": payload.forward is not None,
    }
    db.commit()
    return {"id": str(run.id), "status": run.status, "summary": run.summary}


def _scoreboard(db, principal, video) -> dict:
    model = _model(db, "scoreboard-lights")
    run = AnalysisRun(
        organization_id=principal.organization.id,
        video_id=video.id,
        kind="scoreboard",
        status="running",
        model_version_id=model.id if model else None,
        parameters={"roi": video.scoreboard_roi},
        created_by=principal.user.id,
    )
    db.add(run)
    db.flush()
    if not video.scoreboard_roi:
        run.status = "failed"
        run.error = "Select a scoreboard region first"
        run.finished_at = utcnow()
        db.commit()
        raise AppError("roi_required", 422, "Select a scoreboard region first")
    from ml_inference.frames import CapabilityUnavailable, sample_roi_colors

    with tempfile.TemporaryDirectory() as folder:
        source = Path(folder) / "video"
        key = video.playback_key or video.storage_key
        try:
            download_file(key, source)
            frames = sample_roi_colors(source, video.scoreboard_roi)
        except CapabilityUnavailable as exc:
            run.status = "failed"
            run.error = str(exc)
            run.finished_at = utcnow()
            db.commit()
            raise AppError("capability_unavailable", 422, str(exc)) from exc
    # Frames were cropped to the ROI, so the detector should see the whole crop.
    candidates = detect_light_candidates(frames, {"x": 0, "y": 0, "w": 1, "h": 1})
    for candidate in candidates:
        db.add(
            ScoreEvent(
                organization_id=principal.organization.id,
                bout_id=video.bout_id,
                video_id=video.id,
                timestamp_ms=int(candidate["start_ms"] or 0),
                left_score=0,
                right_score=0,
                source="scoreboard_candidate",
                validated=False,
                note=candidate["note"],
                created_by=principal.user.id,
            )
        )
    db.add(
        InferenceResult(
            analysis_run_id=run.id,
            video_id=video.id,
            model_version_id=model.id if model else None,
            kind="scoreboard",
            payload={"candidates": candidates, "claim_accuracy": False, "score_values_extracted": False},
        )
    )
    run.status = "succeeded"
    run.finished_at = utcnow()
    run.summary = {"experimental": True, "candidates": len(candidates), "claim_accuracy": False, "official_decision": False}
    db.commit()
    return {"id": str(run.id), "status": run.status, "summary": run.summary}


def _pose(db, principal, video) -> dict:
    import json

    from fencing_api.storage import upload_bytes
    from ml_inference.frames import CapabilityUnavailable
    from ml_inference.pose import estimate_poses

    model = _model(db, "pose-landmarker")
    run = AnalysisRun(
        organization_id=principal.organization.id,
        video_id=video.id,
        kind="pose",
        status="running",
        model_version_id=model.id if model else None,
        parameters={"num_poses": 2},
        created_by=principal.user.id,
    )
    db.add(run)
    db.flush()
    key = video.playback_key or video.storage_key
    if not key:
        raise AppError("not_ready", 409, "Video has no stored file")
    with tempfile.TemporaryDirectory() as folder:
        source = Path(folder) / "video"
        download_file(key, source)
        try:
            track = estimate_poses(source)
        except CapabilityUnavailable as exc:
            run.status = "failed"
            run.error = str(exc)
            run.finished_at = utcnow()
            db.commit()
            raise AppError("capability_unavailable", 422, str(exc)) from exc
    storage_key = f"org/{principal.organization.id}/videos/{video.id}/poses/{run.id}.json"
    upload_bytes(json.dumps(track).encode(), storage_key, "application/json")
    db.add(
        PoseSequence(
            video_id=video.id,
            analysis_run_id=run.id,
            model_name="pose_landmarker_lite",
            frame_count=track["frames_sampled"],
            storage_key=storage_key,
        )
    )
    summary = {key: value for key, value in track.items() if key != "frames"}
    db.add(
        InferenceResult(
            analysis_run_id=run.id,
            video_id=video.id,
            model_version_id=model.id if model else None,
            kind="pose",
            payload=summary,
        )
    )
    run.status = "succeeded"
    run.finished_at = utcnow()
    run.summary = summary
    db.commit()
    return {"id": str(run.id), "status": run.status, "summary": summary}


@router.post("/videos/{video_id}/distance")
def distance(video_id: uuid.UUID, payload: DistanceIn, principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    video = require_video(db, principal, video_id)
    width = video.width or 1
    height = video.height or 1
    return calibrated_distance_m(payload.point_a, payload.point_b, video.calibration, width, height)


@router.get("/analyses/{analysis_id}")
def get_analysis(analysis_id: uuid.UUID, principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    run = db.get(AnalysisRun, analysis_id)
    if run is None or run.organization_id != principal.organization.id:
        raise AppError("not_found", 404, "Analysis not found")
    require_video(db, principal, run.video_id)
    return {"id": str(run.id), "kind": run.kind, "status": run.status, "summary": run.summary, "error": run.error}
