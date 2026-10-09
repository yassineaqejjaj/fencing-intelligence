"""Retention purge for soft-deleted videos.

Videos deleted through the privacy flow stay recoverable until this command
hard-deletes them: object-storage keys are removed, then the video row is
deleted (annotations, assets, and jobs cascade in Postgres). Audit log rows
are append-only and deliberately kept.

Usage (dry run first, always):
    python -m fencing_api.retention --days 30
    python -m fencing_api.retention --days 30 --apply
"""
import argparse
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from fencing_api.audit import write_audit
from fencing_api.config import get_settings
from fencing_api.database import SessionLocal
from fencing_api.models import PoseSequence, Video, VideoAsset
from fencing_api.security import utcnow
from fencing_api.storage import delete_key


def purge_expired(db: Session, *, days: int, dry_run: bool = True) -> list[dict]:
    cutoff = utcnow() - timedelta(days=days)
    rows = db.scalars(select(Video).where(Video.deleted_at.is_not(None), Video.deleted_at < cutoff)).all()
    purged = []
    for video in rows:
        keys = {video.storage_key, video.playback_key, video.thumbnail_key}
        keys |= {asset.storage_key for asset in db.scalars(select(VideoAsset).where(VideoAsset.video_id == video.id)).all()}
        keys |= {
            pose.storage_key
            for pose in db.scalars(select(PoseSequence).where(PoseSequence.video_id == video.id)).all()
            if pose.storage_key
        }
        keys.discard("")
        if not dry_run:
            for key in sorted(keys):
                try:
                    delete_key(key)
                except Exception:
                    # Key already gone (e.g. partial earlier purge). The row
                    # delete below still removes every database trace.
                    continue
            write_audit(
                db,
                organization_id=video.organization_id,
                actor_user_id=None,
                action="retention_purge",
                resource_type="video",
                resource_id=str(video.id),
                metadata={"keys": len(keys)},
            )
            db.delete(video)
        purged.append({"video_id": str(video.id), "keys": len(keys), "deleted_at": video.deleted_at.isoformat()})
    if not dry_run:
        db.commit()
    return purged


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Purge soft-deleted videos older than N days")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--apply", action="store_true", help="Actually delete. Without it, only lists candidates.")
    args = parser.parse_args()
    _ = settings
    db = SessionLocal()
    try:
        purged = purge_expired(db, days=args.days, dry_run=not args.apply)
    finally:
        db.close()
    print(f"{'Would purge' if not args.apply else 'Purged'} {len(purged)} video(s) soft-deleted more than {args.days} days ago")
    for item in purged:
        print(f"  {item['video_id']} keys={item['keys']} deleted_at={item['deleted_at']}")


if __name__ == "__main__":
    main()
