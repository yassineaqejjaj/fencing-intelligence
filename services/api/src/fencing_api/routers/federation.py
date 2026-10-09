"""Federation pilot: entries, poule sheets, standings, DE draws, referees.

Poules and draws are generated from stored entries only. Byes never invent
athletes, tied DE bouts never auto-advance, and a referee cannot officiate a
bout involving their own linked athlete.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from fencing_api.audit import write_audit
from fencing_api.database import get_db
from fencing_api.deps import Principal, require_role
from fencing_api.errors import AppError
from fencing_api.models import (
    Athlete,
    Bout,
    BoutParticipant,
    Competition,
    CompetitionEntry,
    OrganizationMembership,
)
from fencing_api.services.access import bout_sides, require_athlete, require_bout, same_org
from fencing_domain.competitions import de_first_round, poule_groups, rank_standings, round_robin_pairs, StandingRow

router = APIRouter(tags=["federation"])

NEXT_ROUND = {"Quarter-final": "Semi-final", "Semi-final": "Final"}


class EntryIn(BaseModel):
    athlete_id: uuid.UUID
    seed: int = Field(default=0, ge=0, le=10000)


class PoulesIn(BaseModel):
    poule_size: int = Field(default=6, ge=2, le=8)


class DrawIn(BaseModel):
    size: int = Field(default=8, ge=2, le=32)
    use_standings: bool = True


class RefereeIn(BaseModel):
    user_id: uuid.UUID | None = None


def _competition(db: Session, principal: Principal, competition_id: uuid.UUID) -> Competition:
    row = db.get(Competition, competition_id)
    if row is None or row.organization_id != principal.organization.id:
        raise AppError("not_found", 404, "Competition not found")
    return row


def _entries(db: Session, competition: Competition) -> list[CompetitionEntry]:
    return db.scalars(
        select(CompetitionEntry)
        .where(CompetitionEntry.competition_id == competition.id)
        .order_by(CompetitionEntry.seed, CompetitionEntry.created_at)
    ).all()


def _entry_athletes(db: Session, competition: Competition) -> dict[str, Athlete]:
    rows = _entries(db, competition)
    athletes = db.scalars(select(Athlete).where(Athlete.id.in_([row.athlete_id for row in rows]))).all() if rows else []
    return {str(item.id): item for item in athletes}


def _make_bout(
    db: Session,
    principal: Principal,
    competition: Competition,
    left_id: uuid.UUID | None,
    right_id: uuid.UUID | None,
    score_limit: int,
    round_name: str,
    label: str,
    status: str = "scheduled",
    note: str = "",
) -> Bout:
    row = Bout(
        organization_id=principal.organization.id,
        competition_id=competition.id,
        weapon=competition.weapon or "epee",
        status=status,
        score_limit=score_limit,
        round=round_name,
        bracket_label=label,
        started_on=competition.start_date,
        notes=note,
        created_by=principal.user.id,
    )
    db.add(row)
    db.flush()
    if left_id is not None:
        db.add(BoutParticipant(bout_id=row.id, athlete_id=left_id, side="left", score=0))
    if right_id is not None:
        db.add(BoutParticipant(bout_id=row.id, athlete_id=right_id, side="right", score=0))
    return row


@router.get("/competitions/{competition_id}/entries")
def list_entries(competition_id: uuid.UUID, principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    competition = _competition(db, principal, competition_id)
    athletes = _entry_athletes(db, competition)
    return {
        "items": [
            {
                "athlete_id": str(row.athlete_id),
                "display_name": athletes.get(str(row.athlete_id)).display_name if athletes.get(str(row.athlete_id)) else "?",
                "seed": row.seed,
            }
            for row in _entries(db, competition)
        ]
    }


@router.post("/competitions/{competition_id}/entries", status_code=201)
def add_entry(competition_id: uuid.UUID, payload: EntryIn, principal: Principal = Depends(require_role("coach")), db: Session = Depends(get_db)):
    competition = _competition(db, principal, competition_id)
    athlete = require_athlete(db, principal, payload.athlete_id)
    if competition.weapon and athlete.weapon != competition.weapon:
        raise AppError("wrong_weapon", 422, "Athlete weapon does not match the competition")
    if db.scalar(select(CompetitionEntry).where(CompetitionEntry.competition_id == competition.id, CompetitionEntry.athlete_id == athlete.id)) is not None:
        raise AppError("already_entered", 422, "Athlete is already entered")
    row = CompetitionEntry(organization_id=principal.organization.id, competition_id=competition.id, athlete_id=athlete.id, seed=payload.seed)
    db.add(row)
    write_audit(db, organization_id=principal.organization.id, actor_user_id=principal.user.id, action="enter", resource_type="competition", resource_id=str(competition.id))
    db.commit()
    return {"athlete_id": str(athlete.id), "seed": row.seed}


@router.delete("/competitions/{competition_id}/entries/{athlete_id}")
def remove_entry(competition_id: uuid.UUID, athlete_id: uuid.UUID, principal: Principal = Depends(require_role("coach")), db: Session = Depends(get_db)):
    competition = _competition(db, principal, competition_id)
    row = db.scalar(select(CompetitionEntry).where(CompetitionEntry.competition_id == competition.id, CompetitionEntry.athlete_id == athlete_id))
    if row is None:
        raise AppError("not_found", 404, "Entry not found")
    drawn = db.scalar(select(Bout).where(Bout.competition_id == competition.id, Bout.round.in_(["poule", "de"])))
    if drawn is not None:
        raise AppError("draw_started", 422, "The draw has started; remove generated bouts before withdrawing an athlete")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.post("/competitions/{competition_id}/poules", status_code=201)
def generate_poules(competition_id: uuid.UUID, payload: PoulesIn, principal: Principal = Depends(require_role("coach")), db: Session = Depends(get_db)):
    competition = _competition(db, principal, competition_id)
    rows = _entries(db, competition)
    if len(rows) < 2:
        raise AppError("too_few_entries", 422, "Enter at least two athletes before drawing poules")
    existing = db.scalars(select(Bout).where(Bout.competition_id == competition.id, Bout.round == "poule")).all()
    if existing:
        raise AppError("poules_exist", 422, "Poule bouts already exist for this competition")
    order = [str(row.athlete_id) for row in rows]
    created = 0
    for group_index, group in enumerate(poule_groups(order, payload.poule_size)):
        label = chr(ord("A") + group_index)
        for bout_index, (left, right) in enumerate(round_robin_pairs(group), start=1):
            _make_bout(
                db, principal, competition,
                uuid.UUID(left), uuid.UUID(right), 5, "poule", f"Poule {label} · bout {bout_index}",
            )
            created += 1
    write_audit(db, organization_id=principal.organization.id, actor_user_id=principal.user.id, action="draw_poules", resource_type="competition", resource_id=str(competition.id))
    db.commit()
    return {"poules": len(poule_groups(order, payload.poule_size)), "bouts": created}


@router.get("/competitions/{competition_id}/standings")
def standings(competition_id: uuid.UUID, principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    competition = _competition(db, principal, competition_id)
    athletes = _entry_athletes(db, competition)
    poule_bouts = db.scalars(select(Bout).where(Bout.competition_id == competition.id, Bout.round == "poule")).all()
    totals: dict[str, dict] = {key: {"bouts": 0, "victories": 0, "scored": 0, "conceded": 0} for key in athletes}
    for bout in poule_bouts:
        if bout.status == "scheduled":
            continue
        sides = bout_sides(db, bout.id)
        left, right = sides.get("left"), sides.get("right")
        if left is None or right is None:
            continue
        for key, scored, conceded in (
            (str(left.athlete_id), left.score, right.score),
            (str(right.athlete_id), right.score, left.score),
        ):
            if key not in totals:
                continue
            totals[key]["bouts"] += 1
            totals[key]["scored"] += scored
            totals[key]["conceded"] += conceded
            if scored > conceded:
                totals[key]["victories"] += 1
    ranked = rank_standings([StandingRow(key, **values) for key, values in totals.items()])
    return {
        "formula_version": 1,
        "items": [
            {
                "athlete_id": row.athlete_id,
                "display_name": athletes[row.athlete_id].display_name if row.athlete_id in athletes else "?",
                "bouts": row.bouts,
                "victories": row.victories,
                "scored": row.scored,
                "conceded": row.conceded,
                "indicator": row.indicator,
            }
            for row in ranked
        ],
    }


@router.post("/competitions/{competition_id}/de", status_code=201)
def generate_de(competition_id: uuid.UUID, payload: DrawIn, principal: Principal = Depends(require_role("coach")), db: Session = Depends(get_db)):
    competition = _competition(db, principal, competition_id)
    if payload.size < 2 or (payload.size & (payload.size - 1)) != 0:
        raise AppError("invalid_size", 422, "DE size must be a power of two")
    if db.scalars(select(Bout).where(Bout.competition_id == competition.id, Bout.round == "de")).first() is not None:
        raise AppError("de_exists", 422, "DE bouts already exist for this competition")
    order = [item["athlete_id"] for item in standings(competition_id, principal, db)["items"]] if payload.use_standings else [str(row.athlete_id) for row in _entries(db, competition)]
    if len(order) < 2:
        raise AppError("too_few_entries", 422, "Enter at least two athletes before drawing the DE")
    created = []
    for left, right, label in de_first_round(order, payload.size):
        row = _make_bout(db, principal, competition, uuid.UUID(left) if left else None, uuid.UUID(right) if right else None, 15, "de", label)
        if left is None or right is None:
            row.status = "completed"
            row.notes = "Bye — the entered athlete advances automatically"
        created.append({"id": str(row.id), "label": label})
    write_audit(db, organization_id=principal.organization.id, actor_user_id=principal.user.id, action="draw_de", resource_type="competition", resource_id=str(competition.id))
    db.commit()
    return {"bouts": created}


@router.post("/competitions/{competition_id}/de/next", status_code=201)
def advance_de(competition_id: uuid.UUID, principal: Principal = Depends(require_role("coach")), db: Session = Depends(get_db)):
    competition = _competition(db, principal, competition_id)
    rounds = db.scalars(select(Bout.round).where(Bout.competition_id == competition.id, Bout.round == "de")).first()
    if rounds is None:
        raise AppError("no_de", 422, "Generate the DE draw first")
    latest = db.scalars(select(Bout).where(Bout.competition_id == competition.id, Bout.round == "de").order_by(Bout.created_at.desc())).all()
    current_label = latest[0].bracket_label.split(" · ")[0] if latest else ""
    current = [bout for bout in latest if bout.bracket_label.startswith(current_label)] if current_label else []
    if current_label == "Final":
        raise AppError("complete", 422, "The final has already been drawn")
    winners: list[uuid.UUID] = []
    for bout in sorted(current, key=lambda item: item.bracket_label):
        if bout.status != "completed":
            raise AppError("undecided", 422, f"Bout {bout.bracket_label} is not completed; the referee must set the score")
        sides = bout_sides(db, bout.id)
        left, right = sides.get("left"), sides.get("right")
        if left is not None and right is None:
            winners.append(left.athlete_id)
        elif right is not None and left is None:
            winners.append(right.athlete_id)
        elif left is not None and right is not None:
            if left.score == right.score:
                raise AppError("undecided", 422, f"Bout {bout.bracket_label} is tied; the referee must set the score")
            winners.append(left.athlete_id if left.score > right.score else right.athlete_id)
    if len(winners) < 2 or len(winners) % 2 == 1:
        raise AppError("undecided", 422, "The current round does not produce an even set of winners")
    next_name = NEXT_ROUND.get(current_label, f"Winners of {current_label}")
    created = []
    for index in range(0, len(winners), 2):
        row = _make_bout(db, principal, competition, winners[index], winners[index + 1], 15, "de", f"{next_name} · match {index // 2 + 1}")
        created.append({"id": str(row.id), "label": row.bracket_label})
    write_audit(db, organization_id=principal.organization.id, actor_user_id=principal.user.id, action="advance_de", resource_type="competition", resource_id=str(competition.id))
    db.commit()
    return {"bouts": created}


@router.patch("/bouts/{bout_id}/referee")
def assign_referee(bout_id: uuid.UUID, payload: RefereeIn, principal: Principal = Depends(require_role("coach")), db: Session = Depends(get_db)):
    bout = require_bout(db, principal, bout_id)
    if payload.user_id is None:
        bout.referee_user_id = None
        db.commit()
        return {"ok": True, "referee_user_id": None}
    membership = db.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == principal.organization.id,
            OrganizationMembership.user_id == payload.user_id,
        )
    )
    if membership is None or membership.role not in {"coach", "club_administrator", "administrator"}:
        raise AppError("invalid_referee", 422, "The referee must be a coach or administrator in this organization")
    sides = bout_sides(db, bout.id)
    linked = {row.athlete_id for row in sides.values()}
    conflict = db.scalars(select(Athlete).where(Athlete.id.in_(linked), Athlete.user_id == payload.user_id)).first() if linked else None
    if conflict is not None:
        raise AppError("referee_conflict", 422, "A referee cannot officiate a bout involving their own athlete record")
    bout.referee_user_id = payload.user_id
    write_audit(db, organization_id=principal.organization.id, actor_user_id=principal.user.id, action="assign_referee", resource_type="bout", resource_id=str(bout.id))
    db.commit()
    return {"ok": True, "referee_user_id": str(payload.user_id)}
