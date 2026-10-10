"""Link a salle athlete to one public FIE profile.

Search and import stay inside the club. The snapshot is the identity,
ranking, medals, and head-to-head the FIE page publishes for that fencer.
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
from fencing_api.models import Athlete
from fencing_api.routers.catalog import WEAPONS, _athlete_out, _license_taken
from fencing_api.security import utcnow
from fencing_api.services.access import require_athlete
from fencing_api.services.fie_profiles import fetch_snapshot, parse_fie_id, search_fencers
from fencing_domain.competitions import CATEGORIES

router = APIRouter(prefix="/federation/fie", tags=["fie"])


class FieQuery(BaseModel):
    q: str = Field(min_length=2, max_length=80)


class FieLinkIn(BaseModel):
    fie_id: int | None = None
    profile_url: str = ""


@router.get("/search")
def search(q: str, principal: Principal = Depends(require_role("viewer"))):
    del principal
    return {"items": search_fencers(q)}


@router.post("/athletes", status_code=201)
def create_from_fie(payload: FieLinkIn, principal: Principal = Depends(require_role("coach")), db: Session = Depends(get_db)):
    snapshot = fetch_snapshot(parse_fie_id(payload.fie_id, payload.profile_url))
    if snapshot.get("weapon") not in WEAPONS:
        raise AppError("fie_weapon_missing", 422, "This FIE profile has no weapon, so it cannot fill a salle athlete")
    row = Athlete(
        organization_id=principal.organization.id,
        display_name=str(snapshot.get("display_name") or "Fencer")[:200],
        weapon=snapshot["weapon"],
        dominant_hand="right",
    )
    db.add(row)
    db.flush()
    _apply(db, principal, row, snapshot)
    write_audit(
        db,
        organization_id=principal.organization.id,
        actor_user_id=principal.user.id,
        action="fie_link",
        resource_type="athlete",
        resource_id=str(row.id),
        metadata={"fie_id": row.fie_id},
    )
    db.commit()
    db.refresh(row)
    return _athlete_out(row, db, include_profile=True)


@router.post("/athletes/{athlete_id}")
def link_athlete(athlete_id: uuid.UUID, payload: FieLinkIn, principal: Principal = Depends(require_role("coach")), db: Session = Depends(get_db)):
    row = require_athlete(db, principal, athlete_id)
    snapshot = fetch_snapshot(parse_fie_id(payload.fie_id, payload.profile_url))
    _apply(db, principal, row, snapshot)
    write_audit(
        db,
        organization_id=principal.organization.id,
        actor_user_id=principal.user.id,
        action="fie_link",
        resource_type="athlete",
        resource_id=str(row.id),
        metadata={"fie_id": row.fie_id},
    )
    db.commit()
    db.refresh(row)
    return _athlete_out(row, db, include_profile=True)


def _apply(db: Session, principal: Principal, row: Athlete, snapshot: dict) -> None:
    weapon = snapshot.get("weapon")
    if weapon not in WEAPONS:
        raise AppError("fie_weapon_missing", 422, "This FIE profile has no weapon, so it cannot fill a salle athlete")
    license_number = str(snapshot.get("license_number") or "")
    if _license_taken(db, principal.organization.id, license_number, exclude=row.id):
        raise AppError("license_taken", 409, "That license number is already registered")
    taken = db.scalar(
        select(Athlete.id).where(
            Athlete.organization_id == principal.organization.id,
            Athlete.fie_id == snapshot["fie_id"],
            Athlete.id != row.id,
        )
    )
    if taken is not None:
        raise AppError("fie_taken", 409, "That FIE profile is already linked to another athlete in this salle")
    category = snapshot.get("category") if snapshot.get("category") in CATEGORIES else "unspecified"
    row.display_name = str(snapshot.get("display_name") or row.display_name)[:200]
    row.country = str(snapshot.get("country") or "")[:80]
    row.weapon = weapon
    if snapshot.get("hand") in {"left", "right"}:
        row.dominant_hand = snapshot["hand"]
    row.license_number = license_number
    row.birth_year = snapshot.get("birth_year") if isinstance(snapshot.get("birth_year"), int) else None
    row.category = category
    row.fie_id = int(snapshot["fie_id"])
    row.fie_profile = snapshot
    row.fie_synced_at = utcnow()
