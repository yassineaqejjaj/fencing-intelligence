"""Invented club records for the local demo account.

Statistics are computed from these rows. They are not a real athlete's results.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from fencing_api.database import SessionLocal
from fencing_domain.competitions import StandingRow, de_first_round, rank_standings, round_robin_pairs

from fencing_api.minors import GUARDIAN_CONSENT_PURPOSE
from fencing_api.models import (
    Annotation,
    Athlete,
    Bout,
    BoutParticipant,
    Club,
    CoachAssignment,
    Competition,
    CompetitionEntry,
    ConsentRecord,
    Exercise,
    FencingPhrase,
    OrganizationMembership,
    Report,
    ScoreEvent,
    Team,
    TeamMembership,
    TouchEvent,
    TrainingAssignment,
    TrainingSession,
    User,
    Video,
    VideoJob,
)
from fencing_api.services.video_jobs import run_video_job
from fencing_api.storage import upload_file

DEMO_SOURCE = "demo"
DEMO_EXTERNAL = "demo-poule-2026"
OPEN_EXTERNAL = "demo-open-lyon-2026"
NOTE = "Invented for the demo. Not a real bout."
OPEN_NOTE = "Invented Open de Lyon. Not a real event."


def ensure_demo_account(db: Session) -> None:
    """Create the public demo coach and club when they are missing.

    The password is the one printed on the landing page. The rows it unlocks
    are invented. This is safe to run again.
    """
    from fencing_api.security import hash_password
    from fencing_api.seed import seed as seed_catalog

    user = db.scalar(select(User).where(User.email == "demo@example.com"))
    if user is None:
        user = User(
            email="demo@example.com",
            password_hash=hash_password("DemoFence2026"),
            display_name="Demo Coach",
            locale="fr",
        )
        db.add(user)
        db.flush()
    membership = db.scalar(select(OrganizationMembership).where(OrganizationMembership.user_id == user.id))
    if membership is None:
        slug = "salle-des-demos"
        suffix = 2
        while db.scalar(select(Organization.id).where(Organization.slug == slug)):
            slug = f"salle-des-demos-{suffix}"
            suffix += 1
        club_org = Organization(name="Salle des démos", slug=slug)
        db.add(club_org)
        db.flush()
        db.add(OrganizationMembership(organization_id=club_org.id, user_id=user.id, role="administrator"))
        db.flush()
    seed_catalog(db)


def seed_demo(db: Session, sample_video: Path | None = None) -> str:
    ensure_demo_account(db)
    user = db.scalar(select(User).where(User.email == "demo@example.com"))
    if user is None:
        raise RuntimeError("Sign-in account demo@example.com does not exist yet")
    membership = db.scalar(select(OrganizationMembership).where(OrganizationMembership.user_id == user.id))
    if membership is None:
        raise RuntimeError("Demo account has no organization")
    org = membership.organization_id
    existing = db.scalar(
        select(Competition).where(
            Competition.organization_id == org,
            Competition.source == DEMO_SOURCE,
            Competition.external_id == DEMO_EXTERNAL,
        )
    )
    if existing is not None:
        status = _seed_open(db, user, org)
        _seed_bout_sheets(db, user, org)
        return status

    club = Club(organization_id=org, name="Salle des démos", country="FR", city="Lyon")
    db.add(club)
    db.flush()
    athletes = {
        "ines": Athlete(
            organization_id=org,
            club_id=club.id,
            display_name="Inès Morel",
            country="FR",
            weapon="epee",
            dominant_hand="right",
            experience_level="club",
            training_objectives="Finish attacks on the arm.",
        ),
        "marc": Athlete(
            organization_id=org,
            club_id=club.id,
            display_name="Marc Adel",
            country="FR",
            weapon="epee",
            dominant_hand="left",
            experience_level="club",
            training_objectives="",
        ),
        "chloe": Athlete(
            organization_id=org,
            club_id=club.id,
            display_name="Chloé Nguyen",
            country="FR",
            weapon="foil",
            dominant_hand="right",
            experience_level="club",
            training_objectives="",
        ),
    }
    db.add_all(athletes.values())
    db.flush()
    competition = Competition(
        organization_id=org,
        external_id=DEMO_EXTERNAL,
        name="Demo poule",
        location="Lyon",
        country="FR",
        weapon="epee",
        category="club",
        season="2026",
        start_date=date(2026, 9, 12),
        source=DEMO_SOURCE,
        source_url="",
    )
    db.add(competition)
    db.flush()

    bouts = []
    for started, left, right, weapon in (
        (date(2026, 9, 12), "ines", "marc", "epee"),
        (date(2026, 9, 26), "ines", "marc", "epee"),
        (date(2026, 10, 3), "ines", "marc", "epee"),
    ):
        bout = Bout(
            organization_id=org,
            competition_id=competition.id,
            weapon=weapon,
            status="completed",
            piste="1",
            score_limit=5,
            started_on=started,
            notes=NOTE,
            created_by=user.id,
        )
        db.add(bout)
        db.flush()
        db.add(BoutParticipant(bout_id=bout.id, athlete_id=athletes[left].id, side="left", score=0))
        db.add(BoutParticipant(bout_id=bout.id, athlete_id=athletes[right].id, side="right", score=0))
        bouts.append(bout)

    video = Video(
        organization_id=org,
        bout_id=bouts[0].id,
        athlete_id=athletes["ines"].id,
        title="Demo poule · piste 1",
        weapon="epee",
        status="uploaded",
        visibility="club",
        original_filename="sample.mp4",
        content_type="video/mp4",
        camera_perspective="side",
        training_consent=False,
        calibration={"piste_length_m": 14, "point_a": {"x": 0.12, "y": 0.62}, "point_b": {"x": 0.88, "y": 0.62}},
        created_by=user.id,
    )
    db.add(video)
    db.flush()
    if sample_video and sample_video.is_file():
        key = f"org/{org}/videos/{video.id}/original"
        video.storage_key = key
        video.size_bytes = sample_video.stat().st_size
        upload_file(sample_video, key, "video/mp4")
        db.add(VideoJob(video_id=video.id, organization_id=org, kind="transcode", status="queued"))
    else:
        video.status = "ready"
        video.duration_seconds = 12
        video.fps = 25
        video.width = 320
        video.height = 240
        video.error = ""
    db.flush()
    phrase = FencingPhrase(
        organization_id=org,
        video_id=video.id,
        bout_id=bouts[0].id,
        start_ms=400,
        end_ms=2200,
        validated=True,
        source="human",
        notes=NOTE,
        created_by=user.id,
    )
    db.add(phrase)
    db.flush()

    actions = [
        ("attack", "no_touch", "weapon_arm", 0.42),
        ("attack", "no_touch", "chest", 0.55),
        ("attack", "touch_for", "weapon_arm", 0.61),
        ("attack", "off_target", "mask", 0.48),
        ("riposte", "no_touch", "chest", 0.37),
        ("riposte", "touch_for", "weapon_arm", 0.33),
        ("parry", "no_touch", None, 0.4),
        ("attack", "no_touch", "flank", 0.7),
        ("counter_attack", "no_touch", "chest", 0.52),
        ("lunge", "touch_for", "weapon_arm", 0.66),
    ]
    for index, (code, outcome, target, position) in enumerate(actions):
        db.add(
            Annotation(
                organization_id=org,
                video_id=video.id,
                phrase_id=phrase.id if index < 3 else None,
                mode="simplified",
                status="validated",
                source="human",
                actor_athlete_id=athletes["ines"].id,
                opponent_athlete_id=athletes["marc"].id,
                action_type_code=code,
                start_ms=400 + index * 700,
                end_ms=900 + index * 700,
                target_area=target,
                piste_position=position,
                outcome=outcome,
                body={"demo": True},
                notes=NOTE,
                created_by=user.id,
            )
        )

    # Inès scores 2, 3, 2 and concedes 3, 2, 2. Five of the six conceded touches land on the weapon arm.
    sheets = [
        (bouts[0], [("ines", "weapon_arm"), ("marc", "weapon_arm"), ("ines", "chest"), ("marc", "weapon_arm"), ("marc", "weapon_arm")]),
        (bouts[1], [("ines", "weapon_arm"), ("marc", "flank"), ("ines", "weapon_arm"), ("ines", "chest"), ("marc", "weapon_arm")]),
        (bouts[2], [("marc", "weapon_arm"), ("ines", "abdomen"), ("ines", "weapon_arm"), ("marc", "weapon_arm")]),
    ]
    for bout, sequence in sheets:
        left = right = 0
        for step, (scorer, target) in enumerate(sequence, start=1):
            if scorer == "ines":
                left += 1
            else:
                right += 1
            scorer_id = athletes[scorer].id
            receiver_id = athletes["marc"].id if scorer == "ines" else athletes["ines"].id
            db.add(
                TouchEvent(
                    organization_id=org,
                    bout_id=bout.id,
                    video_id=video.id,
                    scorer_athlete_id=scorer_id,
                    receiver_athlete_id=receiver_id,
                    timestamp_ms=step * 1000,
                    target_area=target,
                    weapon="epee",
                    valid=True,
                    validated=True,
                    points=1,
                    source="human",
                    created_by=user.id,
                )
            )
            db.add(
                ScoreEvent(
                    organization_id=org,
                    bout_id=bout.id,
                    video_id=video.id,
                    timestamp_ms=step * 1000,
                    left_score=left,
                    right_score=right,
                    source="touch",
                    validated=True,
                    note=NOTE,
                    created_by=user.id,
                )
            )
        for participant in db.scalars(select(BoutParticipant).where(BoutParticipant.bout_id == bout.id)).all():
            participant.score = left if participant.side == "left" else right

    for title, minutes, rpe, day in (
        ("Footwork and finish", 75, 6, 6),
        ("Parry-riposte", 60, 7, 8),
        ("Poule review", 40, 4, 8),
    ):
        db.add(
            TrainingSession(
                organization_id=org,
                athlete_id=athletes["ines"].id,
                coach_user_id=user.id,
                title=title,
                scheduled_for=datetime(2026, 10, day, 18, 0, tzinfo=timezone.utc),
                duration_minutes=minutes,
                rpe=rpe,
                coach_notes=NOTE,
            )
        )
    db.commit()
    if sample_video and sample_video.is_file():
        run_video_job(str(video.id))
    _seed_open(db, user, org)
    _seed_bout_sheets(db, user, org)
    return "seeded"


# Winner, winner score, loser score, whether the winner trailed by two before winning.
OPEN_RESULTS = {
    frozenset({"ines", "marc"}): ("ines", 5, 3, True),
    frozenset({"ines", "lea"}): ("ines", 5, 2, False),
    frozenset({"ines", "noah"}): ("ines", 5, 4, True),
    frozenset({"ines", "amina"}): ("amina", 5, 3, False),
    frozenset({"ines", "hugo"}): ("ines", 5, 1, False),
    frozenset({"marc", "lea"}): ("marc", 5, 4, False),
    frozenset({"marc", "noah"}): ("noah", 5, 4, False),
    frozenset({"marc", "amina"}): ("marc", 5, 2, False),
    frozenset({"marc", "hugo"}): ("marc", 5, 0, False),
    frozenset({"lea", "noah"}): ("lea", 5, 3, False),
    frozenset({"lea", "amina"}): ("lea", 5, 4, True),
    frozenset({"lea", "hugo"}): ("lea", 5, 2, False),
    frozenset({"noah", "amina"}): ("noah", 5, 3, False),
    frozenset({"noah", "hugo"}): ("noah", 5, 1, False),
    frozenset({"amina", "hugo"}): ("amina", 5, 2, False),
}

INES_DATES = {
    "marc": date(2026, 10, 11),
    "lea": date(2026, 10, 12),
    "noah": date(2026, 10, 13),
    "amina": date(2026, 10, 14),
    "hugo": date(2026, 10, 15),
}


def _seed_open(db: Session, user: User, org) -> str:
    """Club season around one invented épée event. Safe to run twice."""
    existing = db.scalar(
        select(Competition).where(
            Competition.organization_id == org,
            Competition.source == DEMO_SOURCE,
            Competition.external_id == OPEN_EXTERNAL,
        )
    )
    if existing is not None:
        return "already-seeded"

    club = db.scalar(select(Club).where(Club.organization_id == org, Club.name == "Salle des démos"))
    if club is None:
        club = Club(organization_id=org, name="Salle des démos", country="FR", city="Lyon")
        db.add(club)
        db.flush()

    specs = {
        "ines": ("Inès Morel", "epee", "right", "national", "Finish on the arm, then keep the lead.", "FR-2026-0101", 2002, "senior"),
        "marc": ("Marc Adel", "epee", "left", "national", "Stop the fleche and riposte.", "FR-2026-0102", 2001, "senior"),
        "chloe": ("Chloé Nguyen", "foil", "right", "club", "Take the blade before attacking.", "FR-2026-0301", 2003, "senior"),
        "lea": ("Léa Bernard", "epee", "right", "national", "Keep distance when trailing.", "FR-2026-0142", 2004, "senior"),
        "noah": ("Noah Petit", "epee", "left", "club", "Choose the counter-attack later.", "FR-2026-0188", 2003, "senior"),
        "amina": ("Amina Diallo", "epee", "right", "national", "Attack the hand in the middle.", "FR-2026-0211", 2005, "senior"),
        "hugo": ("Hugo Keller", "epee", "right", "youth", "Learn the phrase before adding speed.", "FR-2026-0440", 2010, "u17"),
        "camille": ("Camille Rossi", "foil", "right", "club", "Hold priority through the march.", "FR-2026-0308", 2004, "senior"),
        "kenji": ("Kenji Sato", "sabre", "right", "national", "Finish the attack on the march.", "FR-2026-0501", 2000, "senior"),
        "sami": ("Sami Elbaz", "sabre", "left", "club", "Parry the first attack.", "FR-2026-0502", 2002, "senior"),
    }
    athletes: dict[str, Athlete] = {}
    for key, (name, weapon, hand, level, goal, license_number, year, category) in specs.items():
        row = db.scalar(select(Athlete).where(Athlete.organization_id == org, Athlete.display_name == name))
        if row is None:
            row = Athlete(
                organization_id=org,
                club_id=club.id,
                display_name=name,
                country="FR",
                weapon=weapon,
                dominant_hand=hand,
                experience_level=level,
                training_objectives=goal,
                license_number=license_number,
                birth_year=year,
                category=category,
            )
            db.add(row)
            db.flush()
        else:
            if not row.license_number:
                row.license_number = license_number
            if row.birth_year is None:
                row.birth_year = year
            if row.category in {"", "unspecified"}:
                row.category = category
            if row.club_id is None:
                row.club_id = club.id
            if not row.training_objectives:
                row.training_objectives = goal
        athletes[key] = row

    if db.scalar(select(ConsentRecord).where(ConsentRecord.athlete_id == athletes["hugo"].id, ConsentRecord.purpose == GUARDIAN_CONSENT_PURPOSE)) is None:
        db.add(
            ConsentRecord(
                organization_id=org,
                user_id=user.id,
                athlete_id=athletes["hugo"].id,
                purpose=GUARDIAN_CONSENT_PURPOSE,
                granted=True,
                policy_version="1",
                details={"guardian_name": "Claire Keller", "note": OPEN_NOTE},
            )
        )

    team = db.scalar(select(Team).where(Team.organization_id == org, Team.name == "Équipe senior épée"))
    if team is None:
        team = Team(organization_id=org, club_id=club.id, name="Équipe senior épée")
        db.add(team)
        db.flush()
        for key in ("ines", "marc", "lea", "noah", "amina"):
            db.add(TeamMembership(team_id=team.id, athlete_id=athletes[key].id))

    for key in ("ines", "hugo", "chloe", "kenji"):
        if db.scalar(select(CoachAssignment).where(CoachAssignment.coach_user_id == user.id, CoachAssignment.athlete_id == athletes[key].id)) is None:
            db.add(CoachAssignment(organization_id=org, coach_user_id=user.id, athlete_id=athletes[key].id))

    competition = Competition(
        organization_id=org,
        external_id=OPEN_EXTERNAL,
        name="Open de Lyon",
        location="Lyon",
        country="FR",
        weapon="epee",
        category="senior",
        gender="mixed",
        season="2026-2027",
        start_date=date(2026, 10, 18),
        end_date=date(2026, 10, 19),
        source=DEMO_SOURCE,
        source_url="",
    )
    db.add(competition)
    db.flush()
    seeds = [("ines", 1), ("marc", 2), ("lea", 3), ("noah", 4), ("amina", 5), ("hugo", 6)]
    for key, seed in seeds:
        db.add(CompetitionEntry(organization_id=org, competition_id=competition.id, athlete_id=athletes[key].id, seed=seed))
    db.flush()

    order = [str(athletes[key].id) for key, _seed in seeds]
    keys_by_id = {str(athletes[key].id): key for key, _seed in seeds}
    totals = {key: {"bouts": 0, "victories": 0, "scored": 0, "conceded": 0} for key, _seed in seeds}
    for index, (left_id, right_id) in enumerate(round_robin_pairs(order), start=1):
        left_key = keys_by_id[left_id]
        right_key = keys_by_id[right_id]
        winner, winner_score, loser_score, comeback = OPEN_RESULTS[frozenset({left_key, right_key})]
        left_score = winner_score if winner == left_key else loser_score
        right_score = loser_score if winner == left_key else winner_score
        other = right_key if left_key == "ines" else left_key if right_key == "ines" else ""
        bout = Bout(
            organization_id=org,
            competition_id=competition.id,
            weapon="epee",
            status="completed",
            piste=str((index % 4) + 1),
            score_limit=5,
            round="poule",
            bracket_label=f"Poule A · bout {index}",
            referee_user_id=user.id,
            started_on=INES_DATES.get(other, date(2026, 10, 18)),
            notes=OPEN_NOTE,
            created_by=user.id,
        )
        db.add(bout)
        db.flush()
        db.add(BoutParticipant(bout_id=bout.id, athlete_id=athletes[left_key].id, side="left", score=left_score))
        db.add(BoutParticipant(bout_id=bout.id, athlete_id=athletes[right_key].id, side="right", score=right_score))
        _play(db, org, user.id, bout, athletes[left_key], athletes[right_key], left_key, right_key, left_score, right_score, winner == left_key, comeback)
        for key, scored, conceded in ((left_key, left_score, right_score), (right_key, right_score, left_score)):
            totals[key]["bouts"] += 1
            totals[key]["scored"] += scored
            totals[key]["conceded"] += conceded
            if scored > conceded:
                totals[key]["victories"] += 1

    ranked = rank_standings([StandingRow(str(athletes[key].id), **values) for key, values in totals.items()])
    for left_id, right_id, label in de_first_round([row.athlete_id for row in ranked], 8):
        bout = Bout(
            organization_id=org,
            competition_id=competition.id,
            weapon="epee",
            status="completed" if left_id is None or right_id is None else "scheduled",
            piste="1",
            score_limit=15,
            round="de",
            bracket_label=label,
            referee_user_id=user.id,
            started_on=date(2026, 10, 19),
            notes="Bye — the entered athlete advances automatically" if left_id is None or right_id is None else OPEN_NOTE,
            created_by=user.id,
        )
        db.add(bout)
        db.flush()
        if left_id:
            db.add(BoutParticipant(bout_id=bout.id, athlete_id=left_id, side="left", score=15 if right_id else 0))
        if right_id:
            db.add(BoutParticipant(bout_id=bout.id, athlete_id=right_id, side="right", score=8 if left_id else 0))
        if left_id and right_id:
            left_key = keys_by_id[left_id]
            right_key = keys_by_id[right_id]
            _play(db, org, user.id, bout, athletes[left_key], athletes[right_key], left_key, right_key, 15, 8, True, True)
            bout.status = "completed"

    _weapon_bout(db, org, user, athletes["chloe"], athletes["camille"], "foil", date(2026, 10, 4), "LLLLRRLLR")
    _weapon_bout(db, org, user, athletes["chloe"], athletes["camille"], "foil", date(2026, 10, 20), "RRLLLLL")
    _weapon_bout(db, org, user, athletes["kenji"], athletes["sami"], "sabre", date(2026, 10, 6), "LLRLL")
    _weapon_bout(db, org, user, athletes["kenji"], athletes["sami"], "sabre", date(2026, 10, 21), "RLLLRL")

    video = db.scalar(select(Video).where(Video.organization_id == org, Video.title == "Demo poule · piste 1"))
    if video is not None and db.scalar(select(Annotation).where(Annotation.video_id == video.id, Annotation.notes == "demo-open-actions")) is None:
        for index, (code, outcome) in enumerate([("riposte", "touch_for")] * 6 + [("parry", "no_touch")] * 5):
            db.add(
                Annotation(
                    organization_id=org,
                    video_id=video.id,
                    mode="tactical",
                    status="validated",
                    source="human",
                    actor_athlete_id=athletes["ines"].id,
                    opponent_athlete_id=athletes["marc"].id,
                    action_type_code=code,
                    start_ms=8000 + index * 250,
                    end_ms=8200 + index * 250,
                    target_area="weapon_arm" if outcome == "touch_for" else None,
                    outcome=outcome,
                    body={"demo": True},
                    notes="demo-open-actions",
                    created_by=user.id,
                )
            )
        db.add(
            Annotation(
                organization_id=org,
                video_id=video.id,
                mode="simplified",
                status="draft",
                source="movement",
                actor_athlete_id=athletes["ines"].id,
                opponent_athlete_id=athletes["marc"].id,
                action_type_code="attack",
                start_ms=11000,
                end_ms=11400,
                outcome="no_touch",
                confidence=0.42,
                body={"demo": True, "experimental": True},
                notes="Machine hint. Validate before it counts.",
                created_by=user.id,
            )
        )

    session = db.scalar(select(TrainingSession).where(TrainingSession.organization_id == org, TrainingSession.athlete_id == athletes["ines"].id))
    exercise = db.scalar(select(Exercise).where(Exercise.code == "parry_riposte_quarte", Exercise.organization_id.is_(None)))
    if session is not None and exercise is not None:
        if db.scalar(select(TrainingAssignment).where(TrainingAssignment.session_id == session.id, TrainingAssignment.exercise_id == exercise.id)) is None:
            db.add(
                TrainingAssignment(
                    organization_id=org,
                    session_id=session.id,
                    exercise_id=exercise.id,
                    athlete_id=athletes["ines"].id,
                    status="assigned",
                    note=OPEN_NOTE,
                )
            )

    db.commit()
    _seed_report(db, user, org, athletes["ines"])
    return "open-seeded"


def _play(db, org, user_id, bout, left, right, left_key, right_key, left_score, right_score, winner_is_left, comeback) -> None:
    letters = _letters(left_score, right_score, winner_is_left, comeback)
    left_now = right_now = 0
    for step, letter in enumerate(letters, start=1):
        if letter == "L":
            left_now += 1
            scorer, receiver, scorer_key, receiver_key = left, right, left_key, right_key
        else:
            right_now += 1
            scorer, receiver, scorer_key, receiver_key = right, left, right_key, left_key
        target = "weapon_arm" if receiver_key == "ines" else ("chest" if step % 2 == 0 else "flank")
        db.add(
            TouchEvent(
                organization_id=org,
                bout_id=bout.id,
                scorer_athlete_id=scorer.id,
                receiver_athlete_id=receiver.id,
                timestamp_ms=step * 1000,
                target_area=target,
                weapon=bout.weapon,
                valid=True,
                validated=True,
                points=1,
                source="human",
                created_by=user_id,
            )
        )
        db.add(
            ScoreEvent(
                organization_id=org,
                bout_id=bout.id,
                timestamp_ms=step * 1000,
                left_score=left_now,
                right_score=right_now,
                source="touch",
                validated=True,
                note=OPEN_NOTE,
                created_by=user_id,
            )
        )


def _letters(left_score: int, right_score: int, winner_is_left: bool, comeback: bool) -> list[str]:
    if comeback and winner_is_left and right_score >= 2:
        return ["R", "R", *["L"] * left_score, *["R"] * (right_score - 2)]
    if comeback and not winner_is_left and left_score >= 2:
        return ["L", "L", *["R"] * right_score, *["L"] * (left_score - 2)]
    letters: list[str] = []
    left = right = 0
    while left < left_score or right < right_score:
        if left < left_score and (left <= right or right >= right_score):
            letters.append("L")
            left += 1
        elif right < right_score:
            letters.append("R")
            right += 1
        else:
            letters.append("L")
            left += 1
    return letters


def _weapon_bout(db, org, user, left, right, weapon, day, sequence: str) -> None:
    left_score = sequence.count("L")
    right_score = sequence.count("R")
    bout = Bout(
        organization_id=org,
        weapon=weapon,
        status="completed",
        piste="2",
        score_limit=5,
        started_on=day,
        notes=OPEN_NOTE,
        referee_user_id=user.id,
        created_by=user.id,
    )
    db.add(bout)
    db.flush()
    db.add(BoutParticipant(bout_id=bout.id, athlete_id=left.id, side="left", score=left_score))
    db.add(BoutParticipant(bout_id=bout.id, athlete_id=right.id, side="right", score=right_score))
    left_now = right_now = 0
    for step, letter in enumerate(sequence, start=1):
        if letter == "L":
            left_now += 1
            scorer, receiver = left, right
        else:
            right_now += 1
            scorer, receiver = right, left
        db.add(
            TouchEvent(
                organization_id=org,
                bout_id=bout.id,
                scorer_athlete_id=scorer.id,
                receiver_athlete_id=receiver.id,
                timestamp_ms=step * 1000,
                target_area="chest",
                weapon=weapon,
                valid=True,
                validated=True,
                points=1,
                source="human",
                created_by=user.id,
            )
        )
        db.add(
            ScoreEvent(
                organization_id=org,
                bout_id=bout.id,
                timestamp_ms=step * 1000,
                left_score=left_now,
                right_score=right_now,
                source="touch",
                validated=True,
                note=OPEN_NOTE,
                created_by=user.id,
            )
        )


def _seed_report(db: Session, user: User, org, athlete: Athlete) -> None:
    from fencing_api.services.reports import build_performance_pdf, safe_filename
    from fencing_api.services.stats_service import collect_athlete
    from fencing_api.storage import upload_bytes

    title = "Open de Lyon — lecture"
    if db.scalar(select(Report).where(Report.organization_id == org, Report.athlete_id == athlete.id, Report.title == title)) is not None:
        return
    stats = collect_athlete(db, org, athlete.id, weapon="epee")
    pdf = build_performance_pdf(title=title, athlete_name=athlete.display_name, stats=stats, model_note="No model. Counts come from validated touches.")
    key = f"org/{org}/reports/{safe_filename(title)}.pdf"
    try:
        upload_bytes(pdf, key, "application/pdf")
    except Exception:
        db.rollback()
        return
    db.add(
        Report(
            organization_id=org,
            athlete_id=athlete.id,
            kind="performance",
            title=title,
            storage_key=key,
            content_type="application/pdf",
            source={"demo": True, "data_status": stats.get("data_status")},
            created_by=user.id,
        )
    )
    db.commit()


SHEET_PREFIX = "Fiche démo · "


def _seed_bout_sheets(db: Session, user: User, org) -> None:
    """Validated action sheets for invented completed bouts.

    There is no video file. Production fills the same reading after a person
    uploads the bout and validates the marks. Machine drafts are not written.
    """
    bouts = db.scalars(
        select(Bout).where(
            Bout.organization_id == org,
            Bout.status == "completed",
            Bout.notes.contains("Invented"),
        )
    ).all()
    for bout in bouts:
        videos = db.scalars(select(Video).where(Video.bout_id == bout.id, Video.deleted_at.is_(None))).all()
        sheet = next((item for item in videos if item.title.startswith(SHEET_PREFIX)), None)
        if sheet is None:
            video_ids = [item.id for item in videos]
            if video_ids and db.scalar(
                select(Annotation.id).where(Annotation.video_id.in_(video_ids), Annotation.status == "validated").limit(1)
            ) is not None:
                continue
        participants = db.scalars(select(BoutParticipant).where(BoutParticipant.bout_id == bout.id)).all()
        sides = {item.side: item for item in participants}
        left = sides.get("left")
        right = sides.get("right")
        if left is None or right is None:
            continue
        if sheet is None:
            label = bout.bracket_label or str(bout.id)[:8]
            sheet = Video(
                organization_id=org,
                bout_id=bout.id,
                athlete_id=left.athlete_id,
                title=f"{SHEET_PREFIX}{label}",
                weapon=bout.weapon,
                status="ready",
                visibility="club",
                duration_seconds=12,
                fps=25,
                width=320,
                height=240,
                created_by=user.id,
            )
            db.add(sheet)
            db.flush()
        else:
            for mark in db.scalars(select(Annotation).where(Annotation.video_id == sheet.id, Annotation.notes == "demo-bout-sheet")).all():
                db.delete(mark)
        if left.score >= right.score:
            stronger, weaker = left, right
        else:
            stronger, weaker = right, left
        _sheet_marks(db, org, user, sheet, stronger.athlete_id, weaker.athlete_id, stronger.score, "riposte", "attack")
        _sheet_marks(db, org, user, sheet, weaker.athlete_id, stronger.athlete_id, weaker.score, "attack", "parry", offset=20)
    db.commit()


def _strength_attempts(score: int) -> tuple[int, int] | None:
    """Successes that fit inside the bout score, at a rate the reading can call a strength."""
    if score >= 5:
        return 5, 5
    if score == 4:
        return 4, 5
    if score == 3:
        return 3, 5
    if score == 2:
        return 2, 4
    return None


def _sheet_marks(
    db: Session,
    org,
    user: User,
    video: Video,
    athlete_id,
    opponent_id,
    score: int,
    strong: str,
    weak: str,
    offset: int = 0,
) -> None:
    strength = _strength_attempts(score)
    marks: list[tuple[str, str]] = []
    if strength is not None:
        successes, attempts = strength
        marks.extend([(strong, "touch_for")] * successes)
        marks.extend([(strong, "no_touch")] * (attempts - successes))
        marks.extend([(weak, "no_touch")] * 5)
    else:
        weak_successes = 1 if score >= 1 else 0
        marks.extend([(weak, "touch_for")] * weak_successes)
        marks.extend([(weak, "no_touch")] * (5 - weak_successes))
    for index, (action, outcome) in enumerate(marks):
        start = (offset + index) * 400
        db.add(
            Annotation(
                organization_id=org,
                video_id=video.id,
                mode="action",
                status="validated",
                source="human",
                actor_athlete_id=athlete_id,
                opponent_athlete_id=opponent_id,
                action_type_code=action,
                start_ms=start,
                end_ms=start + 300,
                outcome=outcome,
                notes="demo-bout-sheet",
                created_by=user.id,
            )
        )


def main() -> None:
    sample = Path("/tmp/fi-media/sample.mp4")
    db = SessionLocal()
    try:
        print(seed_demo(db, sample if sample.is_file() else None))
    finally:
        db.close()


if __name__ == "__main__":
    main()
