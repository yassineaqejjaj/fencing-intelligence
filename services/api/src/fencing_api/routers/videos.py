import uuid
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fencing_api.audit import write_audit
from fencing_api.config import Settings, get_settings
from fencing_api.database import get_db
from fencing_api.deps import Principal, enforce_rate_limit, get_redis, require_role
from fencing_api.errors import AppError
from fencing_api.minors import guardian_consent_granted, is_minor
from fencing_api.models import Video, VideoAsset, VideoJob
from fencing_api.security import utcnow
from fencing_api.services.access import require_athlete, require_bout, require_video
from fencing_api.services.video_jobs import enqueue_video, latest_job
from fencing_api.storage import delete_key, head, presign_get, presign_put, upload_file

router = APIRouter(prefix="/videos", tags=["videos"])
WEAPONS = {"epee", "foil", "sabre"}


def sniff_video(header: bytes) -> bool:
    if len(header) >= 12 and header[4:8] == b"ftyp":
        return True
    if header.startswith(b"\x1a\x45\xdf\xa3"):
        return True
    if header.startswith(b"RIFF") and b"AVI " in header[:16]:
        return True
    return False


class VideoCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    weapon: str
    filename: str
    content_type: str
    size_bytes: int = Field(gt=0)
    bout_id: uuid.UUID | None = None
    athlete_id: uuid.UUID | None = None
    visibility: str = "private"
    camera_perspective: str = "unspecified"
    training_consent: bool = False


class CalibrationIn(BaseModel):
    piste_length_m: float = Field(gt=0, le=30)
    point_a: dict
    point_b: dict


class RoiIn(BaseModel):
    x: float
    y: float
    w: float
    h: float


def _out(row: Video) -> dict:
    return {
        "id": str(row.id),
        "title": row.title,
        "weapon": row.weapon,
        "status": row.status,
        "visibility": row.visibility,
        "bout_id": str(row.bout_id) if row.bout_id else None,
        "athlete_id": str(row.athlete_id) if row.athlete_id else None,
        "duration_seconds": row.duration_seconds,
        "fps": row.fps,
        "width": row.width,
        "height": row.height,
        "orientation": row.orientation,
        "camera_perspective": row.camera_perspective,
        "size_bytes": row.size_bytes,
        "training_consent": row.training_consent,
        "error": row.error,
        "has_playback": bool(row.playback_key),
        "has_thumbnail": bool(row.thumbnail_key),
        "calibration": row.calibration or {},
        "scoreboard_roi": row.scoreboard_roi,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _job_out(row: VideoJob | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": str(row.id),
        "kind": row.kind,
        "status": row.status,
        "attempts": row.attempts,
        "max_attempts": row.max_attempts,
        "error": row.error,
    }


def _check_links(db, principal, bout_id, athlete_id, weapon, visibility, training_consent=False) -> bool:
    """Validate linked records. Returns True when visibility was forced to
    private because the video shows a minor without guardian consent."""
    if weapon not in WEAPONS:
        raise AppError("invalid_weapon", 422, "Weapon must be epee, foil, or sabre")
    if visibility not in {"private", "club"}:
        raise AppError("invalid_visibility", 422, "Visibility must be private or club")
    if bout_id:
        require_bout(db, principal, bout_id)
    forced_private = False
    if athlete_id:
        athlete = require_athlete(db, principal, athlete_id)
        if is_minor(athlete.birth_year) and not guardian_consent_granted(db, athlete.id):
            if training_consent:
                raise AppError("guardian_consent_required", 422, "Training use of a minor athlete video requires guardian consent")
            if visibility != "private":
                forced_private = True
    return forced_private


@router.get("")
def list_videos(page: int = 1, page_size: int = 20, principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    rows = db.scalars(
        select(Video).where(Video.organization_id == principal.organization.id, Video.deleted_at.is_(None)).order_by(Video.created_at.desc())
    ).all()
    visible = [row for row in rows if require_video_safe(db, principal, row)]
    total = len(visible)
    start = (page - 1) * page_size
    return {"items": [_out(row) for row in visible[start : start + page_size]], "page": page, "page_size": page_size, "total": total}


def require_video_safe(db, principal, row: Video) -> bool:
    from fencing_api.services.access import can_read_video

    return can_read_video(db, principal, row)


@router.post("", status_code=201)
def create_upload(
    payload: VideoCreate,
    principal: Principal = Depends(require_role("athlete")),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    cache=Depends(get_redis),
):
    if payload.size_bytes > settings.max_upload_bytes:
        raise AppError("payload_too_large", 413, "File exceeds the upload limit")
    enforce_rate_limit(cache, f"upload:{principal.user.id}", settings.upload_rate_limit, settings.upload_rate_window_seconds)
    forced_private = _check_links(db, principal, payload.bout_id, payload.athlete_id, payload.weapon, payload.visibility, payload.training_consent)
    video = Video(
        organization_id=principal.organization.id,
        bout_id=payload.bout_id,
        athlete_id=payload.athlete_id,
        title=payload.title.strip(),
        weapon=payload.weapon,
        status="awaiting_upload",
        visibility="private" if forced_private else payload.visibility,
        original_filename=Path(payload.filename).name[:300],
        content_type=payload.content_type,
        size_bytes=payload.size_bytes,
        camera_perspective=payload.camera_perspective,
        training_consent=payload.training_consent,
        calibration={},
        created_by=principal.user.id,
    )
    db.add(video)
    db.flush()
    key = f"org/{principal.organization.id}/videos/{video.id}/original"
    video.storage_key = key
    db.commit()
    return {**_out(video), "upload_url": presign_put(key, payload.content_type, settings), "visibility_forced_private": forced_private}


@router.post("/{video_id}/complete")
def complete_upload(video_id: uuid.UUID, principal: Principal = Depends(require_role("athlete")), db: Session = Depends(get_db)):
    video = require_video(db, principal, video_id)
    if video.created_by != principal.user.id and principal.membership.role not in {"administrator", "club_administrator", "coach", "analyst"}:
        raise AppError("forbidden", 403, "Only the uploader can complete this upload")
    info = head(video.storage_key)
    size = int(info.get("ContentLength") or 0)
    if size <= 0 or size > get_settings().max_upload_bytes:
        raise AppError("invalid_upload", 400, "Uploaded object failed validation")
    video.size_bytes = size
    video.status = "uploaded"
    db.add(VideoAsset(video_id=video.id, kind="original", storage_key=video.storage_key, content_type=video.content_type, size_bytes=size))
    job = VideoJob(video_id=video.id, organization_id=video.organization_id, kind="transcode", status="queued", payload={})
    db.add(job)
    db.commit()
    enqueue_video(video.id)
    db.refresh(video)
    return {"video": _out(video), "job": _job_out(latest_job(db, video.id))}


@router.post("/upload", status_code=201)
async def upload_video(
    file: UploadFile = File(...),
    title: str = Form(...),
    weapon: str = Form(...),
    bout_id: uuid.UUID | None = Form(None),
    athlete_id: uuid.UUID | None = Form(None),
    visibility: str = Form("private"),
    camera_perspective: str = Form("unspecified"),
    training_consent: bool = Form(False),
    principal: Principal = Depends(require_role("athlete")),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    cache=Depends(get_redis),
):
    enforce_rate_limit(cache, f"upload:{principal.user.id}", settings.upload_rate_limit, settings.upload_rate_window_seconds)
    forced_private = _check_links(db, principal, bout_id, athlete_id, weapon, visibility, training_consent)
    with NamedTemporaryFile(delete=False) as temporary:
        path = Path(temporary.name)
        size = 0
        header = b""
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > settings.max_upload_bytes:
                path.unlink(missing_ok=True)
                raise AppError("payload_too_large", 413, "File exceeds the upload limit")
            if len(header) < 32:
                header += chunk[:32]
            temporary.write(chunk)
    if not sniff_video(header):
        path.unlink(missing_ok=True)
        raise AppError("invalid_media", 400, "File is not a recognized video container")
    video = Video(
        organization_id=principal.organization.id,
        bout_id=bout_id,
        athlete_id=athlete_id,
        title=title.strip(),
        weapon=weapon,
        status="uploaded",
        visibility="private" if forced_private else visibility,
        original_filename=(file.filename or "video")[:300],
        content_type=file.content_type or "application/octet-stream",
        size_bytes=size,
        camera_perspective=camera_perspective,
        training_consent=training_consent,
        calibration={},
        created_by=principal.user.id,
    )
    db.add(video)
    db.flush()
    key = f"org/{principal.organization.id}/videos/{video.id}/original"
    video.storage_key = key
    upload_file(path, key, video.content_type, settings)
    path.unlink(missing_ok=True)
    db.add(VideoAsset(video_id=video.id, kind="original", storage_key=key, content_type=video.content_type, size_bytes=size))
    db.add(VideoJob(video_id=video.id, organization_id=video.organization_id, kind="transcode", status="queued"))
    if training_consent:
        from fencing_api.models import ConsentRecord

        db.add(
            ConsentRecord(
                organization_id=principal.organization.id,
                user_id=principal.user.id,
                video_id=video.id,
                purpose="research_training",
                granted=True,
                policy_version="1",
            )
        )
    write_audit(db, organization_id=principal.organization.id, actor_user_id=principal.user.id, action="upload", resource_type="video", resource_id=str(video.id), metadata={"bytes": size})
    db.commit()
    enqueue_video(video.id)
    db.refresh(video)
    return {"video": _out(video), "job": _job_out(latest_job(db, video.id)), "visibility_forced_private": forced_private}


@router.get("/{video_id}")
def get_video(video_id: uuid.UUID, principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    video = require_video(db, principal, video_id)
    return {"video": _out(video), "job": _job_out(latest_job(db, video.id))}


@router.get("/{video_id}/playback")
def playback(video_id: uuid.UUID, principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    video = require_video(db, principal, video_id)
    key = video.playback_key or ""
    if video.status != "ready" or not key:
        raise AppError("not_ready", 409, "Video is not ready for playback")
    thumb = presign_get(video.thumbnail_key) if video.thumbnail_key else None
    return {"url": presign_get(key), "thumbnail_url": thumb, "expires_in": 900}


@router.post("/{video_id}/retry")
def retry(video_id: uuid.UUID, principal: Principal = Depends(require_role("analyst")), db: Session = Depends(get_db)):
    video = require_video(db, principal, video_id)
    previous = latest_job(db, video.id)
    if previous and previous.attempts >= previous.max_attempts and previous.status == "failed":
        raise AppError("retries_exhausted", 409, "This video has used its processing retries")
    if video.status not in {"failed", "uploaded"}:
        raise AppError("not_retryable", 409, "Only a failed video can be retried")
    video.status = "uploaded"
    video.error = ""
    db.add(VideoJob(video_id=video.id, organization_id=video.organization_id, kind="transcode", status="queued"))
    db.commit()
    enqueue_video(video.id)
    db.refresh(video)
    return {"video": _out(video), "job": _job_out(latest_job(db, video.id))}


@router.delete("/{video_id}")
def delete_video(video_id: uuid.UUID, principal: Principal = Depends(require_role("athlete")), db: Session = Depends(get_db)):
    video = require_video(db, principal, video_id)
    if video.created_by != principal.user.id and principal.membership.role not in {"administrator", "club_administrator"}:
        raise AppError("forbidden", 403, "You cannot delete this video")
    for key in {video.storage_key, video.playback_key, video.thumbnail_key}:
        delete_key(key)
    assets = db.scalars(select(VideoAsset).where(VideoAsset.video_id == video.id)).all()
    for asset in assets:
        delete_key(asset.storage_key)
    video.deleted_at = utcnow()
    video.status = "deleted"
    write_audit(db, organization_id=principal.organization.id, actor_user_id=principal.user.id, action="delete", resource_type="video", resource_id=str(video.id))
    db.commit()
    return {"ok": True}


@router.put("/{video_id}/calibration")
def set_calibration(video_id: uuid.UUID, payload: CalibrationIn, principal: Principal = Depends(require_role("analyst")), db: Session = Depends(get_db)):
    video = require_video(db, principal, video_id)
    for point in (payload.point_a, payload.point_b):
        if not {"x", "y"} <= set(point):
            raise AppError("invalid_calibration", 422, "Calibration points need x and y")
    video.calibration = {"piste_length_m": payload.piste_length_m, "point_a": payload.point_a, "point_b": payload.point_b}
    db.commit()
    return {"calibration": video.calibration}


@router.put("/{video_id}/scoreboard-roi")
def set_roi(video_id: uuid.UUID, payload: RoiIn, principal: Principal = Depends(require_role("analyst")), db: Session = Depends(get_db)):
    video = require_video(db, principal, video_id)
    if min(payload.w, payload.h) <= 0 or max(payload.x, payload.y, payload.x + payload.w, payload.y + payload.h) > 1:
        raise AppError("invalid_roi", 422, "Scoreboard region must sit inside the frame")
    video.scoreboard_roi = payload.model_dump()
    db.commit()
    return {"scoreboard_roi": video.scoreboard_roi}


@router.get("/jobs/{job_id}")
def get_job(job_id: uuid.UUID, principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    job = db.get(VideoJob, job_id)
    if job is None or job.organization_id != principal.organization.id:
        raise AppError("not_found", 404, "Job not found")
    require_video(db, principal, job.video_id)
    return _job_out(job)
