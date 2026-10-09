"""Guardian consent for minor athletes.

An athlete is a minor when their birth year makes them under 18 in the
current year. Recording, sharing, or training on a minor's video requires a
guardian consent record. Latest record wins, so a guardian can revoke.
"""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from fencing_api.models import ConsentRecord

GUARDIAN_CONSENT_PURPOSE = "guardian_consent"
ADULT_AGE = 18


def is_minor(birth_year: int | None, today: date | None = None) -> bool:
    if birth_year is None:
        return False
    current = (today or date.today()).year
    return current - birth_year < ADULT_AGE


def guardian_consent(db: Session, athlete_id) -> ConsentRecord | None:
    return db.scalar(
        select(ConsentRecord)
        .where(ConsentRecord.athlete_id == athlete_id, ConsentRecord.purpose == GUARDIAN_CONSENT_PURPOSE)
        .order_by(ConsentRecord.created_at.desc())
        .limit(1)
    )


def guardian_consent_granted(db: Session, athlete_id) -> bool:
    record = guardian_consent(db, athlete_id)
    return record is not None and record.granted
