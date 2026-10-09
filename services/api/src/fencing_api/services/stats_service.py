import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from fencing_domain.intelligence import athlete_intelligence, bout_momentum, bout_reading
from fencing_domain.statistics import (
    AnnotationView,
    BoutView,
    ScoreView,
    TouchView,
    athlete_statistics,
    bout_statistics,
)

from fencing_api.models import Annotation, Athlete, Bout, BoutParticipant, ScoreEvent, TouchEvent, Video


def _video_weapon(db: Session, cache: dict, video_id) -> tuple[str | None, uuid.UUID | None]:
    if video_id is None:
        return None, None
    if video_id not in cache:
        video = db.get(Video, video_id)
        cache[video_id] = video
    video = cache[video_id]
    if video is None:
        return None, None
    if video.bout_id:
        bout = db.get(Bout, video.bout_id)
        if bout is not None:
            return bout.weapon, bout.id
    return video.weapon, video.bout_id


def collect_athlete(db: Session, organization_id: uuid.UUID, athlete_id: uuid.UUID, weapon: str | None = None) -> dict:
    ann_views, touch_views, score_views, bout_views = athlete_views(db, organization_id, athlete_id)
    return athlete_statistics(str(athlete_id), ann_views, touch_views, score_views, bout_views, weapon=weapon)


def collect_intelligence(db: Session, organization_id: uuid.UUID, athlete_id: uuid.UUID, weapon: str | None = None) -> dict:
    ann_views, touch_views, score_views, bout_views = athlete_views(db, organization_id, athlete_id)
    return athlete_intelligence(str(athlete_id), ann_views, touch_views, score_views, bout_views, weapon=weapon)


def athlete_views(
    db: Session, organization_id: uuid.UUID, athlete_id: uuid.UUID
) -> tuple[list[AnnotationView], list[TouchView], list[ScoreView], list[BoutView]]:
    """Load every record that involves the athlete as domain views. Validation is decided by the domain."""
    annotations = db.scalars(
        select(Annotation).where(
            Annotation.organization_id == organization_id,
            (Annotation.actor_athlete_id == athlete_id) | (Annotation.opponent_athlete_id == athlete_id),
        )
    ).all()
    touches = db.scalars(
        select(TouchEvent).where(
            TouchEvent.organization_id == organization_id,
            (TouchEvent.scorer_athlete_id == athlete_id) | (TouchEvent.receiver_athlete_id == athlete_id),
        )
    ).all()
    bouts = db.scalars(select(Bout).where(Bout.organization_id == organization_id)).all()
    participants = db.scalars(
        select(BoutParticipant).where(BoutParticipant.athlete_id == athlete_id)
    ).all()
    bout_ids = {item.bout_id for item in participants}
    relevant_bouts = [bout for bout in bouts if bout.id in bout_ids]
    scores = db.scalars(select(ScoreEvent).where(ScoreEvent.organization_id == organization_id, ScoreEvent.validated.is_(True))).all()
    video_cache: dict = {}
    ann_views = []
    for item in annotations:
        weapon_name, bout_id = _video_weapon(db, video_cache, item.video_id)
        ann_views.append(
            AnnotationView(
                id=str(item.id),
                athlete_id=str(item.actor_athlete_id) if item.actor_athlete_id else None,
                opponent_id=str(item.opponent_athlete_id) if item.opponent_athlete_id else None,
                action_code=item.action_type_code,
                outcome=item.outcome,
                target_area=item.target_area,
                piste_position=item.piste_position,
                validated=item.status == "validated",
                video_id=str(item.video_id),
                bout_id=str(bout_id) if bout_id else None,
                start_ms=item.start_ms,
                weapon=weapon_name,
            )
        )
    touch_views = []
    for item in touches:
        touch_views.append(
            TouchView(
                id=str(item.id),
                scorer_id=str(item.scorer_athlete_id),
                receiver_id=str(item.receiver_athlete_id),
                valid=item.valid,
                validated=item.validated,
                target_area=item.target_area,
                timestamp_ms=item.timestamp_ms,
                bout_id=str(item.bout_id) if item.bout_id else None,
                video_id=str(item.video_id) if item.video_id else None,
                weapon=item.weapon,
            )
        )
    side_by_bout: dict[uuid.UUID, dict[str, str]] = {}
    if relevant_bouts:
        rows = db.scalars(select(BoutParticipant).where(BoutParticipant.bout_id.in_([bout.id for bout in relevant_bouts]))).all()
        for row in rows:
            side_by_bout.setdefault(row.bout_id, {})[row.side] = str(row.athlete_id)
    score_views = []
    for item in scores:
        if item.bout_id not in bout_ids:
            continue
        sides = side_by_bout.get(item.bout_id, {})
        bout = next((candidate for candidate in relevant_bouts if candidate.id == item.bout_id), None)
        score_views.append(
            ScoreView(
                timestamp_ms=item.timestamp_ms,
                bout_id=str(item.bout_id) if item.bout_id else None,
                left_athlete_id=sides.get("left"),
                right_athlete_id=sides.get("right"),
                left_score=item.left_score,
                right_score=item.right_score,
                weapon=bout.weapon if bout else None,
            )
        )
    bout_views = []
    for bout in relevant_bouts:
        sides = side_by_bout.get(bout.id, {})
        opponents = tuple(athlete for side, athlete in sides.items() if athlete != str(athlete_id))
        bout_views.append(
            BoutView(
                id=str(bout.id),
                weapon=bout.weapon,
                started_on=bout.started_on.isoformat() if bout.started_on else None,
                opponent_ids=opponents,
                competition_id=str(bout.competition_id) if bout.competition_id else None,
            )
        )
    return ann_views, touch_views, score_views, bout_views


def collect_bout_momentum(db: Session, bout: Bout) -> dict:
    sides = {item.side: item for item in db.scalars(select(BoutParticipant).where(BoutParticipant.bout_id == bout.id)).all()}
    touches = db.scalars(select(TouchEvent).where(TouchEvent.bout_id == bout.id)).all()
    views = [
        TouchView(
            id=str(item.id),
            scorer_id=str(item.scorer_athlete_id),
            receiver_id=str(item.receiver_athlete_id),
            valid=item.valid,
            validated=item.validated,
            target_area=item.target_area,
            timestamp_ms=item.timestamp_ms,
            bout_id=str(bout.id),
            video_id=str(item.video_id) if item.video_id else None,
            weapon=item.weapon,
        )
        for item in touches
    ]
    left = sides.get("left")
    right = sides.get("right")
    block = bout_momentum(views, str(left.athlete_id) if left else None, str(right.athlete_id) if right else None)
    block["bout_id"] = str(bout.id)
    block["left_athlete_id"] = str(left.athlete_id) if left else None
    block["right_athlete_id"] = str(right.athlete_id) if right else None
    return block


def collect_bout_reading(db: Session, bout: Bout) -> dict:
    """Per-fencer strengths and weaknesses for one bout. Validated rows only."""
    stats = collect_bout(db, bout)
    participants = db.scalars(select(BoutParticipant).where(BoutParticipant.bout_id == bout.id)).all()
    sides = {item.side: item for item in participants}
    left = sides.get("left")
    right = sides.get("right")
    videos = db.scalars(select(Video).where(Video.bout_id == bout.id, Video.deleted_at.is_(None))).all()
    video_ids = [video.id for video in videos]
    ann_rows = db.scalars(select(Annotation).where(Annotation.video_id.in_(video_ids))).all() if video_ids else []
    annotations = [
        AnnotationView(
            id=str(item.id),
            athlete_id=str(item.actor_athlete_id) if item.actor_athlete_id else None,
            opponent_id=str(item.opponent_athlete_id) if item.opponent_athlete_id else None,
            action_code=item.action_type_code,
            outcome=item.outcome,
            target_area=item.target_area,
            piste_position=item.piste_position,
            validated=item.status == "validated",
            video_id=str(item.video_id),
            bout_id=str(bout.id),
            start_ms=item.start_ms,
            weapon=bout.weapon,
        )
        for item in ann_rows
    ]
    touches = db.scalars(select(TouchEvent).where(TouchEvent.bout_id == bout.id)).all()
    touch_views = [
        TouchView(
            id=str(item.id),
            scorer_id=str(item.scorer_athlete_id),
            receiver_id=str(item.receiver_athlete_id),
            valid=item.valid,
            validated=item.validated,
            target_area=item.target_area,
            timestamp_ms=item.timestamp_ms,
            bout_id=str(bout.id),
            video_id=str(item.video_id) if item.video_id else None,
            weapon=item.weapon,
        )
        for item in touches
    ]
    payload = bout_reading(
        str(left.athlete_id) if left else None,
        str(right.athlete_id) if right else None,
        annotations,
        touch_views,
    )
    payload["bout_id"] = str(bout.id)
    payload["weapon"] = bout.weapon
    payload["statistics_status"] = stats["data_status"]
    return payload


def collect_bout(db: Session, bout: Bout) -> dict:
    participants = db.scalars(select(BoutParticipant).where(BoutParticipant.bout_id == bout.id)).all()
    sides = {item.side: item for item in participants}
    left = sides.get("left")
    right = sides.get("right")
    annotations = []
    videos = db.scalars(select(Video).where(Video.bout_id == bout.id, Video.deleted_at.is_(None))).all()
    video_ids = [video.id for video in videos]
    ann_rows = []
    if video_ids:
        ann_rows = db.scalars(select(Annotation).where(Annotation.video_id.in_(video_ids))).all()
    for item in ann_rows:
        annotations.append(
            AnnotationView(
                id=str(item.id),
                athlete_id=str(item.actor_athlete_id) if item.actor_athlete_id else None,
                opponent_id=str(item.opponent_athlete_id) if item.opponent_athlete_id else None,
                action_code=item.action_type_code,
                outcome=item.outcome,
                target_area=item.target_area,
                piste_position=item.piste_position,
                validated=item.status == "validated",
                video_id=str(item.video_id),
                bout_id=str(bout.id),
                start_ms=item.start_ms,
                weapon=bout.weapon,
            )
        )
    touches = db.scalars(select(TouchEvent).where(TouchEvent.bout_id == bout.id)).all()
    touch_views = [
        TouchView(
            id=str(item.id),
            scorer_id=str(item.scorer_athlete_id),
            receiver_id=str(item.receiver_athlete_id),
            valid=item.valid,
            validated=item.validated,
            target_area=item.target_area,
            timestamp_ms=item.timestamp_ms,
            bout_id=str(bout.id),
            video_id=str(item.video_id) if item.video_id else None,
            weapon=item.weapon,
        )
        for item in touches
    ]
    scores = db.scalars(select(ScoreEvent).where(ScoreEvent.bout_id == bout.id, ScoreEvent.validated.is_(True)).order_by(ScoreEvent.timestamp_ms)).all()
    score_views = [
        ScoreView(item.timestamp_ms, str(bout.id), str(left.athlete_id) if left else None, str(right.athlete_id) if right else None, item.left_score, item.right_score, bout.weapon)
        for item in scores
    ]
    bout_view = BoutView(
        str(bout.id),
        bout.weapon,
        bout.started_on.isoformat() if bout.started_on else None,
        tuple(str(item.athlete_id) for item in participants),
        str(bout.competition_id) if bout.competition_id else None,
    )
    return bout_statistics(
        str(left.athlete_id) if left else None,
        str(right.athlete_id) if right else None,
        annotations,
        touch_views,
        score_views,
        bout_view,
    )


def athlete_names(db: Session, organization_id: uuid.UUID) -> dict[str, str]:
    rows = db.scalars(select(Athlete).where(Athlete.organization_id == organization_id)).all()
    return {str(row.id): row.display_name for row in rows}
