import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fencing_api.audit import write_audit
from fencing_api.database import get_db
from fencing_api.deps import Principal, require_role
from fencing_api.errors import AppError
from fencing_api.mailer import send_email
from fencing_api.minors import GUARDIAN_CONSENT_PURPOSE, guardian_consent_granted, is_minor
from fencing_api.models import (
    Athlete,
    Bout,
    BoutParticipant,
    Club,
    CoachAssignment,
    Competition,
    ConsentRecord,
    Invitation,
    OrganizationMembership,
    ScoreEvent,
    Team,
    TeamMembership,
    TouchEvent,
    User,
)
from fencing_api.security import expiry_from_now, hash_token, new_token, utcnow
from fencing_domain.competitions import CATEGORIES
from fencing_api.services.access import bout_sides, not_found, require_athlete, require_bout, same_org

router = APIRouter(tags=["catalog"])
WEAPONS = {"epee", "foil", "sabre"}
ROLES = {"administrator", "club_administrator", "coach", "athlete", "analyst", "viewer"}


def _weapon(value: str) -> str:
    if value not in WEAPONS:
        raise AppError("invalid_weapon", 422, "Weapon must be epee, foil, or sabre")
    return value


def _page(page: int, page_size: int) -> tuple[int, int]:
    return max(page, 1), min(max(page_size, 1), 100)


class ClubIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    country: str = ""
    city: str = ""


class AthleteIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=200)
    club_id: uuid.UUID | None = None
    country: str = ""
    weapon: str
    dominant_hand: str = "right"
    experience_level: str = "unspecified"
    training_objectives: str = ""
    user_id: uuid.UUID | None = None
    license_number: str = ""
    birth_year: int | None = None
    category: str = "unspecified"


def _license_fields(payload: AthleteIn) -> tuple[str, int | None, str]:
    from datetime import date

    license_number = payload.license_number.strip()
    if len(license_number) > 40:
        raise AppError("invalid_license", 422, "License number is too long")
    birth_year = payload.birth_year
    if birth_year is not None and not 1900 <= birth_year <= date.today().year:
        raise AppError("invalid_birth_year", 422, "Birth year is out of range")
    if payload.category not in CATEGORIES:
        raise AppError("invalid_category", 422, "Unknown age category")
    return license_number, birth_year, payload.category


def _license_taken(db: Session, organization_id: uuid.UUID, license_number: str, exclude: uuid.UUID | None = None) -> bool:
    if not license_number:
        return False
    query = select(Athlete).where(Athlete.organization_id == organization_id, Athlete.license_number == license_number)
    if exclude is not None:
        query = query.where(Athlete.id != exclude)
    return db.scalar(query) is not None


class TeamIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    club_id: uuid.UUID | None = None


class InviteIn(BaseModel):
    email: EmailStr
    role: str


class AcceptIn(BaseModel):
    token: str


class CompetitionIn(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    weapon: str = ""
    location: str = ""
    country: str = ""
    category: str = ""
    start_date: date | None = None
    end_date: date | None = None


class BoutIn(BaseModel):
    weapon: str
    competition_id: uuid.UUID | None = None
    left_athlete_id: uuid.UUID
    right_athlete_id: uuid.UUID
    score_limit: int = 5
    piste: str = ""
    started_on: date | None = None
    notes: str = ""


class TouchIn(BaseModel):
    scorer_athlete_id: uuid.UUID
    receiver_athlete_id: uuid.UUID
    timestamp_ms: int = 0
    target_area: str | None = None
    video_id: uuid.UUID | None = None
    annotation_id: uuid.UUID | None = None
    valid: bool = True
    points: int = 1


class ScoreIn(BaseModel):
    left_score: int = Field(ge=0, le=99)
    right_score: int = Field(ge=0, le=99)
    timestamp_ms: int = 0
    video_id: uuid.UUID | None = None


def _club_out(row: Club) -> dict:
    return {"id": str(row.id), "name": row.name, "country": row.country, "city": row.city}


def _fie_summary(profile: dict | None) -> dict | None:
    if not isinstance(profile, dict):
        return None
    record = profile.get("record") if isinstance(profile.get("record"), dict) else {}
    return {
        "fie_id": profile.get("fie_id"),
        "rank": profile.get("rank"),
        "points": profile.get("points"),
        "season": profile.get("season"),
        "source_url": profile.get("source_url"),
        "wins": record.get("wins"),
        "losses": record.get("losses"),
    }


def _athlete_out(row: Athlete, db: Session | None = None, *, include_profile: bool = False) -> dict:
    minor = is_minor(row.birth_year)
    consent: bool | None = guardian_consent_granted(db, row.id) if (db is not None and minor) else None
    return {
        "id": str(row.id),
        "display_name": row.display_name,
        "club_id": str(row.club_id) if row.club_id else None,
        "country": row.country,
        "weapon": row.weapon,
        "dominant_hand": row.dominant_hand,
        "experience_level": row.experience_level,
        "training_objectives": row.training_objectives,
        "user_id": str(row.user_id) if row.user_id else None,
        "license_number": row.license_number,
        "birth_year": row.birth_year,
        "category": row.category,
        "is_minor": minor,
        "guardian_consent_granted": consent,
        "fie_id": row.fie_id,
        "fie_synced_at": row.fie_synced_at.isoformat() if row.fie_synced_at else None,
        "fie_summary": _fie_summary(row.fie_profile),
        "fie_profile": row.fie_profile if include_profile else None,
    }


@router.get("/clubs")
def list_clubs(page: int = 1, page_size: int = 20, principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    page, page_size = _page(page, page_size)
    query = select(Club).where(Club.organization_id == principal.organization.id)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(query.order_by(Club.name).offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": [_club_out(row) for row in rows], "page": page, "page_size": page_size, "total": total}


@router.post("/clubs", status_code=201)
def create_club(payload: ClubIn, principal: Principal = Depends(require_role("club_administrator")), db: Session = Depends(get_db)):
    row = Club(organization_id=principal.organization.id, name=payload.name.strip(), country=payload.country.strip(), city=payload.city.strip())
    db.add(row)
    write_audit(db, organization_id=principal.organization.id, actor_user_id=principal.user.id, action="create", resource_type="club", resource_id="pending")
    db.commit()
    db.refresh(row)
    return _club_out(row)


@router.get("/athletes")
def list_athletes(page: int = 1, page_size: int = 50, principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    page, page_size = _page(page, page_size)
    query = select(Athlete).where(Athlete.organization_id == principal.organization.id)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(query.order_by(Athlete.display_name).offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": [_athlete_out(row, db) for row in rows], "page": page, "page_size": page_size, "total": total}


@router.post("/athletes", status_code=201)
def create_athlete(payload: AthleteIn, principal: Principal = Depends(require_role("coach")), db: Session = Depends(get_db)):
    if payload.dominant_hand not in {"left", "right"}:
        raise AppError("invalid_hand", 422, "Dominant hand must be left or right")
    if payload.club_id is not None:
        same_org(db.get(Club, payload.club_id), principal.organization.id, "Club")
    license_number, birth_year, category = _license_fields(payload)
    if _license_taken(db, principal.organization.id, license_number):
        raise AppError("license_taken", 409, "That license number is already registered")
    row = Athlete(
        organization_id=principal.organization.id,
        display_name=payload.display_name.strip(),
        club_id=payload.club_id,
        country=payload.country.strip(),
        weapon=_weapon(payload.weapon),
        dominant_hand=payload.dominant_hand,
        experience_level=payload.experience_level,
        training_objectives=payload.training_objectives,
        user_id=payload.user_id,
        license_number=license_number,
        birth_year=birth_year,
        category=category,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    write_audit(db, organization_id=principal.organization.id, actor_user_id=principal.user.id, action="create", resource_type="athlete", resource_id=str(row.id))
    db.commit()
    return _athlete_out(row, db)


@router.get("/athletes/{athlete_id}")
def get_athlete(athlete_id: uuid.UUID, principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    return _athlete_out(require_athlete(db, principal, athlete_id), db, include_profile=True)


@router.patch("/athletes/{athlete_id}")
def update_athlete(athlete_id: uuid.UUID, payload: AthleteIn, principal: Principal = Depends(require_role("coach")), db: Session = Depends(get_db)):
    row = require_athlete(db, principal, athlete_id)
    license_number, birth_year, category = _license_fields(payload)
    if _license_taken(db, principal.organization.id, license_number, exclude=row.id):
        raise AppError("license_taken", 409, "That license number is already registered")
    row.display_name = payload.display_name.strip()
    row.country = payload.country.strip()
    row.weapon = _weapon(payload.weapon)
    row.dominant_hand = payload.dominant_hand
    row.experience_level = payload.experience_level
    row.training_objectives = payload.training_objectives
    row.club_id = payload.club_id
    row.license_number = license_number
    row.birth_year = birth_year
    row.category = category
    db.commit()
    return _athlete_out(row, db)


class GuardianConsentIn(BaseModel):
    granted: bool
    guardian_name: str = Field(default="", max_length=200)
    note: str = Field(default="", max_length=500)


@router.post("/athletes/{athlete_id}/guardian-consent")
def record_guardian_consent(athlete_id: uuid.UUID, payload: GuardianConsentIn, principal: Principal = Depends(require_role("coach")), db: Session = Depends(get_db)):
    row = require_athlete(db, principal, athlete_id)
    if not is_minor(row.birth_year):
        raise AppError("not_minor", 422, "Guardian consent only applies to minor athletes")
    record = ConsentRecord(
        organization_id=principal.organization.id,
        user_id=principal.user.id,
        athlete_id=row.id,
        purpose=GUARDIAN_CONSENT_PURPOSE,
        granted=payload.granted,
        policy_version="1",
        details={"guardian_name": payload.guardian_name.strip(), "note": payload.note.strip()},
    )
    db.add(record)
    write_audit(db, organization_id=principal.organization.id, actor_user_id=principal.user.id, action="guardian_consent", resource_type="athlete", resource_id=str(row.id), metadata={"granted": payload.granted})
    db.commit()
    return {"athlete_id": str(row.id), "is_minor": True, "granted": payload.granted}


class AthleteImportIn(BaseModel):
    csv_text: str = Field(min_length=1, max_length=200_000)


@router.post("/athletes/import", status_code=201)
def import_athletes(payload: AthleteImportIn, principal: Principal = Depends(require_role("coach")), db: Session = Depends(get_db)):
    import csv
    from datetime import date
    from io import StringIO

    reader = csv.DictReader(StringIO(payload.csv_text))
    expected = {"display_name", "weapon", "license_number", "birth_year", "category", "club", "country", "dominant_hand"}
    if reader.fieldnames is None or not expected.issuperset({name.strip() for name in reader.fieldnames}):
        raise AppError("invalid_csv", 422, "CSV needs headers: display_name, weapon, license_number, birth_year, category, club, country, dominant_hand")
    created = updated = skipped = 0
    errors: list[str] = []
    for line, record in enumerate(reader, start=2):
        if line > 2001:
            errors.append("stopping after 2000 rows")
            break
        name = (record.get("display_name") or "").strip()
        weapon = (record.get("weapon") or "").strip()
        license_number = (record.get("license_number") or "").strip()
        birth_raw = (record.get("birth_year") or "").strip()
        category = (record.get("category") or "").strip() or "unspecified"
        club_name = (record.get("club") or "").strip()
        if not name or weapon not in WEAPONS or category not in CATEGORIES or len(license_number) > 40:
            skipped += 1
            errors.append(f"line {line}: name, weapon, category, or license is invalid")
            continue
        birth_year: int | None = None
        if birth_raw:
            try:
                birth_year = int(birth_raw)
            except ValueError:
                skipped += 1
                errors.append(f"line {line}: birth_year is not a number")
                continue
            if not 1900 <= birth_year <= date.today().year:
                skipped += 1
                errors.append(f"line {line}: birth_year is out of range")
                continue
        club_id = None
        if club_name:
            club = db.scalar(select(Club).where(Club.organization_id == principal.organization.id, Club.name == club_name))
            if club is None:
                club = Club(organization_id=principal.organization.id, name=club_name[:200])
                db.add(club)
                db.flush()
            club_id = club.id
        existing = db.scalar(select(Athlete).where(Athlete.organization_id == principal.organization.id, Athlete.license_number == license_number)) if license_number else None
        if existing is not None:
            existing.display_name = name
            existing.weapon = weapon
            existing.birth_year = birth_year
            existing.category = category
            if club_id is not None:
                existing.club_id = club_id
            updated += 1
            continue
        if license_number and _license_taken(db, principal.organization.id, license_number):
            skipped += 1
            errors.append(f"line {line}: license is already registered")
            continue
        db.add(
            Athlete(
                organization_id=principal.organization.id,
                display_name=name[:200],
                club_id=club_id,
                country=(record.get("country") or "").strip()[:80],
                weapon=weapon,
                dominant_hand=(record.get("dominant_hand") or "right").strip() or "right",
                license_number=license_number,
                birth_year=birth_year,
                category=category,
            )
        )
        db.flush()
        created += 1
    write_audit(db, organization_id=principal.organization.id, actor_user_id=principal.user.id, action="import_athletes", resource_type="athlete", resource_id=f"{created}-created")
    db.commit()
    return {"created": created, "updated": updated, "skipped": skipped, "errors": errors[:20]}


@router.post("/athletes/{athlete_id}/coaches", status_code=201)
def assign_coach(athlete_id: uuid.UUID, user_id: uuid.UUID, principal: Principal = Depends(require_role("club_administrator")), db: Session = Depends(get_db)):
    require_athlete(db, principal, athlete_id)
    membership = db.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == principal.organization.id,
            OrganizationMembership.user_id == user_id,
        )
    )
    if membership is None or membership.role not in {"coach", "club_administrator", "administrator"}:
        raise AppError("invalid_coach", 422, "That user is not a coach in this organization")
    existing = db.scalar(select(CoachAssignment).where(CoachAssignment.coach_user_id == user_id, CoachAssignment.athlete_id == athlete_id))
    if existing is None:
        db.add(CoachAssignment(organization_id=principal.organization.id, coach_user_id=user_id, athlete_id=athlete_id))
        db.commit()
    return {"ok": True}


@router.post("/teams", status_code=201)
def create_team(payload: TeamIn, principal: Principal = Depends(require_role("club_administrator")), db: Session = Depends(get_db)):
    if payload.club_id:
        same_org(db.get(Club, payload.club_id), principal.organization.id, "Club")
    row = Team(organization_id=principal.organization.id, club_id=payload.club_id, name=payload.name.strip())
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": str(row.id), "name": row.name, "club_id": str(row.club_id) if row.club_id else None}


@router.post("/teams/{team_id}/athletes/{athlete_id}", status_code=201)
def add_team_athlete(team_id: uuid.UUID, athlete_id: uuid.UUID, principal: Principal = Depends(require_role("coach")), db: Session = Depends(get_db)):
    team = same_org(db.get(Team, team_id), principal.organization.id, "Team")
    require_athlete(db, principal, athlete_id)
    if db.scalar(select(TeamMembership).where(TeamMembership.team_id == team.id, TeamMembership.athlete_id == athlete_id)) is None:
        db.add(TeamMembership(team_id=team.id, athlete_id=athlete_id))
        db.commit()
    return {"ok": True}


@router.get("/organizations/current")
def current_org(principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    members = db.execute(
        select(OrganizationMembership, User).join(User, User.id == OrganizationMembership.user_id).where(
            OrganizationMembership.organization_id == principal.organization.id
        )
    ).all()
    return {
        "id": str(principal.organization.id),
        "name": principal.organization.name,
        "slug": principal.organization.slug,
        "members": [
            {"user_id": str(user.id), "email": user.email, "display_name": user.display_name, "role": membership.role}
            for membership, user in members
        ],
    }


@router.post("/organizations/invitations", status_code=201)
def invite(payload: InviteIn, principal: Principal = Depends(require_role("club_administrator")), db: Session = Depends(get_db)):
    if payload.role not in ROLES:
        raise AppError("invalid_role", 422, "Unknown role")
    token = new_token()
    row = Invitation(
        organization_id=principal.organization.id,
        email=payload.email.lower(),
        role=payload.role,
        token_hash=hash_token(token),
        expires_at=expiry_from_now(days=7),
        created_by=principal.user.id,
    )
    db.add(row)
    db.commit()
    email_sent = send_email(payload.email.lower(), "Invitation to Fencing Intelligence", f"Invitation token:\n{token}\n")
    body = {"id": str(row.id), "email": row.email, "role": row.role, "expires_at": row.expires_at.isoformat(), "email_sent": email_sent}
    if not email_sent:
        # No SMTP: hand the token to the inviter (an authorized club
        # administrator) so they can transmit it out of band. Without this
        # the invitation would be unusable and fail silently.
        body["token"] = token
    return body


@router.post("/invitations/accept")
def accept_invitation(payload: AcceptIn, principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    # viewer dependency still requires a membership. A brand new user accepts after register into their own org,
    # then joins another. That matches a user who already has an account.
    row = db.scalar(select(Invitation).where(Invitation.token_hash == hash_token(payload.token)))
    if row is None or row.accepted_at is not None or row.expires_at <= utcnow():
        raise AppError("invalid_token", 400, "Invitation is invalid or expired")
    if row.email != principal.user.email:
        raise AppError("forbidden", 403, "This invitation was sent to a different email")
    existing = db.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == row.organization_id,
            OrganizationMembership.user_id == principal.user.id,
        )
    )
    if existing is None:
        db.add(OrganizationMembership(organization_id=row.organization_id, user_id=principal.user.id, role=row.role))
    row.accepted_at = utcnow()
    db.commit()
    return {"ok": True, "organization_id": str(row.organization_id), "role": row.role}


@router.get("/competitions")
def list_competitions(principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    rows = db.scalars(select(Competition).where(Competition.organization_id == principal.organization.id).order_by(Competition.start_date.desc().nulls_last())).all()
    return {"items": [_competition_out(row) for row in rows]}


@router.get("/competitions/{competition_id}")
def get_competition(competition_id: uuid.UUID, principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    row = db.get(Competition, competition_id)
    if row is None or row.organization_id != principal.organization.id:
        raise AppError("not_found", 404, "Competition not found")
    return _competition_out(row)


@router.post("/competitions", status_code=201)
def create_competition(payload: CompetitionIn, principal: Principal = Depends(require_role("coach")), db: Session = Depends(get_db)):
    weapon = _weapon(payload.weapon) if payload.weapon else ""
    row = Competition(
        organization_id=principal.organization.id,
        external_id=str(uuid.uuid4()),
        name=payload.name.strip(),
        weapon=weapon,
        location=payload.location,
        country=payload.country,
        category=payload.category,
        start_date=payload.start_date,
        end_date=payload.end_date,
        source="manual",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _competition_out(row)


def _competition_out(row: Competition) -> dict:
    return {
        "id": str(row.id),
        "name": row.name,
        "weapon": row.weapon,
        "country": row.country,
        "location": row.location,
        "category": row.category,
        "start_date": row.start_date.isoformat() if row.start_date else None,
        "end_date": row.end_date.isoformat() if row.end_date else None,
        "source": row.source,
        "external_id": row.external_id,
    }


def _bout_out(db: Session, row: Bout) -> dict:
    sides = bout_sides(db, row.id)
    return {
        "id": str(row.id),
        "weapon": row.weapon,
        "status": row.status,
        "competition_id": str(row.competition_id) if row.competition_id else None,
        "piste": row.piste,
        "score_limit": row.score_limit,
        "round": row.round,
        "bracket_label": row.bracket_label,
        "referee_user_id": str(row.referee_user_id) if row.referee_user_id else None,
        "started_on": row.started_on.isoformat() if row.started_on else None,
        "notes": row.notes,
        "left": _side_out(sides.get("left")),
        "right": _side_out(sides.get("right")),
    }


def _side_out(row: BoutParticipant | None) -> dict | None:
    if row is None:
        return None
    return {"athlete_id": str(row.athlete_id), "score": row.score}


@router.get("/bouts")
def list_bouts(principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    rows = db.scalars(select(Bout).where(Bout.organization_id == principal.organization.id).order_by(Bout.created_at.desc())).all()
    return {"items": [_bout_out(db, row) for row in rows]}


@router.post("/bouts", status_code=201)
def create_bout(payload: BoutIn, principal: Principal = Depends(require_role("coach")), db: Session = Depends(get_db)):
    if payload.left_athlete_id == payload.right_athlete_id:
        raise AppError("invalid_bout", 422, "A bout needs two athletes")
    require_athlete(db, principal, payload.left_athlete_id)
    require_athlete(db, principal, payload.right_athlete_id)
    if payload.competition_id:
        same_org(db.get(Competition, payload.competition_id), principal.organization.id, "Competition")
    row = Bout(
        organization_id=principal.organization.id,
        competition_id=payload.competition_id,
        weapon=_weapon(payload.weapon),
        score_limit=payload.score_limit,
        piste=payload.piste,
        started_on=payload.started_on,
        notes=payload.notes,
        created_by=principal.user.id,
        status="scheduled",
    )
    db.add(row)
    db.flush()
    db.add(BoutParticipant(bout_id=row.id, athlete_id=payload.left_athlete_id, side="left", score=0))
    db.add(BoutParticipant(bout_id=row.id, athlete_id=payload.right_athlete_id, side="right", score=0))
    db.commit()
    return _bout_out(db, row)


@router.get("/bouts/{bout_id}")
def get_bout(bout_id: uuid.UUID, principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    return _bout_out(db, require_bout(db, principal, bout_id))


def _record_score_event(db: Session, principal: Principal, bout: Bout, timestamp_ms: int, video_id, source: str, note: str = "") -> None:
    sides = bout_sides(db, bout.id)
    left = sides.get("left")
    right = sides.get("right")
    db.add(
        ScoreEvent(
            organization_id=principal.organization.id,
            bout_id=bout.id,
            video_id=video_id,
            timestamp_ms=timestamp_ms,
            left_score=left.score if left else 0,
            right_score=right.score if right else 0,
            source=source,
            validated=True,
            note=note,
            created_by=principal.user.id,
        )
    )


@router.post("/bouts/{bout_id}/touches", status_code=201)
def add_touch(bout_id: uuid.UUID, payload: TouchIn, principal: Principal = Depends(require_role("analyst")), db: Session = Depends(get_db)):
    bout = require_bout(db, principal, bout_id)
    sides = bout_sides(db, bout.id)
    known = {item.athlete_id for item in sides.values()}
    if payload.scorer_athlete_id not in known or payload.receiver_athlete_id not in known:
        raise AppError("invalid_touch", 422, "Touch athletes must be the bout participants")
    if payload.points < 1:
        raise AppError("invalid_touch", 422, "Points must be at least 1")
    touch = TouchEvent(
        organization_id=principal.organization.id,
        bout_id=bout.id,
        video_id=payload.video_id,
        annotation_id=payload.annotation_id,
        scorer_athlete_id=payload.scorer_athlete_id,
        receiver_athlete_id=payload.receiver_athlete_id,
        timestamp_ms=payload.timestamp_ms,
        target_area=payload.target_area,
        weapon=bout.weapon,
        valid=payload.valid,
        validated=True,
        points=payload.points,
        source="human",
        created_by=principal.user.id,
    )
    db.add(touch)
    if payload.valid:
        for participant in sides.values():
            if participant.athlete_id == payload.scorer_athlete_id:
                participant.score += payload.points
    bout.status = "in_progress"
    db.flush()
    _record_score_event(db, principal, bout, payload.timestamp_ms, payload.video_id, "touch")
    db.commit()
    db.refresh(touch)
    return {"id": str(touch.id), "bout": _bout_out(db, bout)}


@router.post("/bouts/{bout_id}/score")
def set_score(bout_id: uuid.UUID, payload: ScoreIn, principal: Principal = Depends(require_role("analyst")), db: Session = Depends(get_db)):
    bout = require_bout(db, principal, bout_id)
    sides = bout_sides(db, bout.id)
    if "left" not in sides or "right" not in sides:
        raise AppError("invalid_bout", 422, "Bout is missing a participant")
    sides["left"].score = payload.left_score
    sides["right"].score = payload.right_score
    _record_score_event(db, principal, bout, payload.timestamp_ms, payload.video_id, "manual_set")
    db.commit()
    return _bout_out(db, bout)


@router.post("/bouts/{bout_id}/complete")
def complete_bout(bout_id: uuid.UUID, principal: Principal = Depends(require_role("analyst")), db: Session = Depends(get_db)):
    bout = require_bout(db, principal, bout_id)
    if bout.status == "completed":
        raise AppError("already_completed", 422, "Bout is already completed")
    bout.status = "completed"
    write_audit(db, organization_id=principal.organization.id, actor_user_id=principal.user.id, action="complete_bout", resource_type="bout", resource_id=str(bout.id))
    db.commit()
    return _bout_out(db, bout)


@router.get("/bouts/{bout_id}/touches")
def list_touches(bout_id: uuid.UUID, principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    bout = require_bout(db, principal, bout_id)
    rows = db.scalars(select(TouchEvent).where(TouchEvent.bout_id == bout.id).order_by(TouchEvent.timestamp_ms)).all()
    return {
        "items": [
            {
                "id": str(row.id),
                "scorer_athlete_id": str(row.scorer_athlete_id),
                "receiver_athlete_id": str(row.receiver_athlete_id),
                "timestamp_ms": row.timestamp_ms,
                "target_area": row.target_area,
                "valid": row.valid,
                "validated": row.validated,
                "points": row.points,
                "source": row.source,
            }
            for row in rows
        ]
    }


@router.get("/bouts/{bout_id}/score-events")
def list_scores(bout_id: uuid.UUID, principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    bout = require_bout(db, principal, bout_id)
    rows = db.scalars(select(ScoreEvent).where(ScoreEvent.bout_id == bout.id).order_by(ScoreEvent.timestamp_ms, ScoreEvent.created_at)).all()
    return {
        "items": [
            {
                "id": str(row.id),
                "timestamp_ms": row.timestamp_ms,
                "left_score": row.left_score,
                "right_score": row.right_score,
                "source": row.source,
                "validated": row.validated,
            }
            for row in rows
        ]
    }
