from sqlalchemy import select
from sqlalchemy.orm import Session

from fencing_domain.recommendations import EXERCISES
from fencing_domain.taxonomy import ACTION_TYPES, RULE_SOURCES

from fencing_api.models import ActionType, Exercise, ModelVersion


def _model(db: Session, name: str, notes: str, metrics: dict | None = None) -> None:
    row = db.scalar(select(ModelVersion).where(ModelVersion.name == name, ModelVersion.version == "0.1.0"))
    if row is None:
        db.add(ModelVersion(name=name, version="0.1.0", status="experimental", metrics=metrics or {}, notes=notes))


def seed(db: Session) -> None:
    source = RULE_SOURCES[0]["id"]
    version = RULE_SOURCES[0]["version"]
    existing_codes = set(db.scalars(select(ActionType.code)))
    for item in ACTION_TYPES:
        if item.code in existing_codes:
            continue
        db.add(
            ActionType(
                code=item.code,
                category=item.category,
                label_en=item.label_en,
                label_fr=item.label_fr,
                weapons=list(item.weapons),
                experimental=item.experimental,
                rule_source=source,
                rule_version=version,
            )
        )
    existing_exercises = set(db.scalars(select(Exercise.code).where(Exercise.organization_id.is_(None))))
    for item in EXERCISES:
        if item["code"] in existing_exercises:
            continue
        db.add(
            Exercise(
                organization_id=None,
                code=item["code"],
                name_en=item["name_en"],
                name_fr=item["name_fr"],
                description_en=item["description_en"],
                description_fr=item["description_fr"],
                weapons=item["weapons"],
                duration_minutes=item["duration_minutes"],
            )
        )
    _model(
        db,
        "heuristic-movement",
        "Geometric rules on a tracked horizontal position. Not trained on fencing video. No accuracy is claimed.",
    )
    _model(
        db,
        "scoreboard-lights",
        "Detects red and green dominance inside a selected region. Does not extract score digits and does not make a referee decision.",
    )
    _model(
        db,
        "pose-landmarker",
        "Apache-2.0 MediaPipe pose landmarker. Returns joint positions for up to two people. It does not name fencing actions.",
        {"claim_accuracy": False, "tactical_labels": False},
    )
    _model(
        db,
        "synthetic-baseline",
        "Logistic regression on two separated synthetic clusters. The holdout score is a pipeline check, not fencing recognition accuracy.",
        {"claim_accuracy": False, "synthetic": True, "holdout_accuracy": 1.0, "holdout_size": 4, "classes": ["advance", "lunge"]},
    )
