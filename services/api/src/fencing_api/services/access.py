import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from fencing_api.deps import Principal
from fencing_api.errors import AppError
from fencing_api.models import Athlete, Bout, BoutParticipant, CoachAssignment, Video

PRIVILEGED = {"administrator", "club_administrator", "analyst"}


def not_found(name: str) -> AppError:
    return AppError("not_found", 404, f"{name} not found")


def same_org(row, organization_id: uuid.UUID, name: str):
    if row is None or getattr(row, "organization_id", None) != organization_id:
        raise not_found(name)
    if getattr(row, "deleted_at", None) is not None:
        raise not_found(name)
    return row


def can_read_video(db: Session, principal: Principal, video: Video) -> bool:
    if video.organization_id != principal.organization.id or video.deleted_at is not None:
        return False
    role = principal.membership.role
    if role in PRIVILEGED:
        return True
    if video.visibility == "club":
        return True
    if video.created_by == principal.user.id:
        return True
    if role == "coach" and video.athlete_id is not None:
        assigned = db.scalar(
            select(CoachAssignment.id).where(
                CoachAssignment.organization_id == principal.organization.id,
                CoachAssignment.coach_user_id == principal.user.id,
                CoachAssignment.athlete_id == video.athlete_id,
            )
        )
        return assigned is not None
    if role == "athlete" and video.athlete_id is not None:
        linked = db.scalar(
            select(Athlete.id).where(
                Athlete.organization_id == principal.organization.id,
                Athlete.user_id == principal.user.id,
                Athlete.id == video.athlete_id,
            )
        )
        return linked is not None
    return False


def require_video(db: Session, principal: Principal, video_id: uuid.UUID) -> Video:
    video = db.get(Video, video_id)
    if video is None or not can_read_video(db, principal, video):
        raise not_found("Video")
    return video


def require_bout(db: Session, principal: Principal, bout_id: uuid.UUID) -> Bout:
    bout = db.get(Bout, bout_id)
    return same_org(bout, principal.organization.id, "Bout")


def require_athlete(db: Session, principal: Principal, athlete_id: uuid.UUID) -> Athlete:
    athlete = db.get(Athlete, athlete_id)
    return same_org(athlete, principal.organization.id, "Athlete")


def bout_sides(db: Session, bout_id: uuid.UUID) -> dict[str, BoutParticipant]:
    rows = db.scalars(select(BoutParticipant).where(BoutParticipant.bout_id == bout_id)).all()
    return {row.side: row for row in rows}
