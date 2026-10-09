import tempfile
import uuid
from pathlib import Path

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from fencing_api.config import get_settings
from fencing_api.database import SessionLocal
from fencing_api.models import Video, VideoAsset, VideoJob
from fencing_api.security import utcnow
from fencing_api.storage import download_file, upload_file

log = structlog.get_logger()


def latest_job(db: Session, video_id: uuid.UUID) -> VideoJob | None:
    return db.scalar(select(VideoJob).where(VideoJob.video_id == video_id).order_by(VideoJob.created_at.desc()))


def enqueue_video(video_id: uuid.UUID) -> None:
    settings = get_settings()
    if settings.inline_jobs:
        run_video_job(str(video_id))
        return
    from fencing_api.tasks import process_video_task

    process_video_task.send(str(video_id))


def run_video_job(video_id: str) -> None:
    db = SessionLocal()
    try:
        video = db.get(Video, uuid.UUID(video_id))
        if video is None or video.deleted_at is not None:
            return
        job = latest_job(db, video.id)
        if job is None:
            return
        job.status = "running"
        job.attempts += 1
        job.started_at = utcnow()
        video.status = "processing"
        video.error = ""
        db.commit()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "source"
            playback = root / "playback.mp4"
            thumbnail = root / "thumb.jpg"
            download_file(video.storage_key, source)
            from video_worker.pipeline import transcode

            metadata = transcode(source, playback, thumbnail)
            org = video.organization_id
            playback_key = f"org/{org}/videos/{video.id}/playback.mp4"
            thumb_key = f"org/{org}/videos/{video.id}/thumb.jpg"
            upload_file(playback, playback_key, "video/mp4")
            upload_file(thumbnail, thumb_key, "image/jpeg")
        video = db.get(Video, uuid.UUID(video_id))
        job = latest_job(db, video.id)
        video.playback_key = playback_key
        video.thumbnail_key = thumb_key
        video.duration_seconds = metadata["duration_seconds"]
        video.fps = metadata["fps"]
        video.width = metadata["width"]
        video.height = metadata["height"]
        video.orientation = metadata["orientation"]
        video.status = "ready"
        video.error = ""
        job.status = "succeeded"
        job.finished_at = utcnow()
        job.error = ""
        db.add(
            VideoAsset(
                video_id=video.id,
                kind="playback",
                storage_key=playback_key,
                content_type="video/mp4",
                size_bytes=metadata["playback_bytes"],
                metadata_json=metadata["probe"],
            )
        )
        db.add(
            VideoAsset(
                video_id=video.id,
                kind="thumbnail",
                storage_key=thumb_key,
                content_type="image/jpeg",
                size_bytes=metadata["thumbnail_bytes"],
            )
        )
        db.commit()
    except Exception as exc:
        log.warning("video_job_failed", video_id=video_id, error=type(exc).__name__)
        db.rollback()
        video = db.get(Video, uuid.UUID(video_id))
        if video is not None:
            job = latest_job(db, video.id)
            message = str(exc)[:800]
            video.status = "failed"
            video.error = message
            if job is not None:
                job.status = "failed"
                job.error = message
                job.finished_at = utcnow()
            db.commit()
    finally:
        db.close()
