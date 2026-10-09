import uuid
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from fencing_domain.registry import doctor

from fencing_api.config import get_settings
from fencing_api.database import get_db
from fencing_api.deps import Principal, require_role
from fencing_api.errors import AppError
from fencing_api.models import (
    Competition,
    Dataset,
    DatasetSample,
    DatasetVersion,
    ExternalAthlete,
    HistoricalBout,
    ModelVersion,
)
from fencing_ml.datasets.fie_csv import ImportErrorReport, import_fie_csv_tree
from fencing_ml.datasets.ffd import inspect_ffd
from fencing_ml.datasets.mfad import inspect_mfad

router = APIRouter(tags=["research"])


class ImportIn(BaseModel):
    name: str
    relative_path: str = Field(min_length=1, max_length=300)


def _safe_path(relative: str) -> Path:
    root = Path(get_settings().data_import_root).resolve()
    candidate = (root / relative).resolve()
    if root != candidate and root not in candidate.parents:
        raise AppError("invalid_path", 400, "Import path must stay inside the configured data directory")
    return candidate


@router.get("/datasets/doctor")
def datasets_doctor(principal: Principal = Depends(require_role("analyst"))):
    return doctor(Path(get_settings().dataset_manifest_root))


@router.get("/datasets")
def list_datasets(principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    catalog = doctor(Path(get_settings().dataset_manifest_root))
    rows = db.scalars(select(Dataset).where((Dataset.organization_id.is_(None)) | (Dataset.organization_id == principal.organization.id))).all()
    return {
        "catalog": catalog,
        "imports": [
            {"id": str(row.id), "name": row.name, "license": row.license, "access_status": row.access_status, "notes": row.notes}
            for row in rows
        ],
    }


@router.post("/datasets/import", status_code=201)
def import_dataset(payload: ImportIn, principal: Principal = Depends(require_role("administrator")), db: Session = Depends(get_db)):
    path = _safe_path(payload.relative_path)
    name = payload.name.strip()
    if name == "FIE-fencing-dataset":
        try:
            parsed = import_fie_csv_tree(path)
        except ImportErrorReport as exc:
            raise AppError("import_failed", 400, str(exc)) from exc
        return _store_fie(db, principal, parsed)
    if name == "MFAD":
        try:
            parsed = inspect_mfad(path)
        except FileNotFoundError as exc:
            raise AppError("import_failed", 400, str(exc)) from exc
        return _store_inspected(db, principal, parsed, license="unspecified", allowed=["local-inspection-only"])
    if name == "FFD":
        try:
            parsed = inspect_ffd(path)
        except FileNotFoundError as exc:
            raise AppError("import_failed", 400, str(exc)) from exc
        return _store_inspected(db, principal, parsed, license="unspecified", allowed=["local-inspection-only"])
    raise AppError("unsupported_dataset", 400, "This dataset cannot be imported. Unlicensed repositories are not downloaded.")


def _store_fie(db: Session, principal: Principal, parsed: dict) -> dict:
    dataset = Dataset(
        organization_id=principal.organization.id,
        name="FIE-fencing-dataset",
        source_url="https://github.com/amichaelsen/fie-fencing-dataset",
        license="GPL-3.0",
        access_status="user-supplied",
        allowed_uses=["import-user-supplied-csv"],
        notes="Original CSV reader. Upstream generator code was not copied.",
    )
    db.add(dataset)
    db.flush()
    version = DatasetVersion(
        dataset_id=dataset.id,
        version="user-import",
        import_status="imported",
        sample_count=len(parsed["bouts"]),
        modalities=["tabular"],
        labels=["competition", "bout", "athlete"],
        schema_name="fie-csv-v1",
        provenance=parsed["provenance"],
    )
    db.add(version)
    db.flush()
    competitions = {}
    for item in parsed["competitions"]:
        existing = db.scalar(
            select(Competition).where(
                Competition.organization_id == principal.organization.id,
                Competition.source == "fie-csv",
                Competition.external_id == item["external_id"],
            )
        )
        if existing is None:
            existing = Competition(
                organization_id=principal.organization.id,
                external_id=item["external_id"],
                name=item["name"] or item["external_id"],
                country=item["country"],
                weapon=item["weapon"],
                category=item["category"],
                gender=item["gender"],
                season=item["season"],
                source="fie-csv",
                source_url=item["source_url"],
            )
            if item["start_date"]:
                existing.start_date = _date(item["start_date"])
            if item["end_date"]:
                existing.end_date = _date(item["end_date"])
            db.add(existing)
            db.flush()
        competitions[item["external_id"]] = existing
    for item in parsed["athletes"]:
        existing = db.scalar(
            select(ExternalAthlete).where(
                ExternalAthlete.organization_id == principal.organization.id,
                ExternalAthlete.source == "fie-csv",
                ExternalAthlete.external_id == item["external_id"],
            )
        )
        if existing is None:
            db.add(
                ExternalAthlete(
                    organization_id=principal.organization.id,
                    source="fie-csv",
                    external_id=item["external_id"],
                    display_name=item["display_name"],
                    country=item["country"],
                    dominant_hand=item["dominant_hand"],
                )
            )
        elif item["display_name"] and not existing.display_name:
            existing.display_name = item["display_name"]
    inserted = 0
    for item in parsed["bouts"]:
        exists = db.scalar(
            select(HistoricalBout.id).where(
                HistoricalBout.organization_id == principal.organization.id,
                HistoricalBout.source == "fie-csv",
                HistoricalBout.fingerprint == item["fingerprint"],
            )
        )
        if exists:
            continue
        competition = competitions.get(item["tournament_external_id"])
        db.add(
            HistoricalBout(
                organization_id=principal.organization.id,
                competition_id=competition.id if competition else None,
                source="fie-csv",
                fingerprint=item["fingerprint"],
                fencer_external_id=item["fencer_external_id"],
                opponent_external_id=item["opponent_external_id"],
                fencer_score=item["fencer_score"],
                opponent_score=item["opponent_score"],
                winner_external_id=item["winner_external_id"],
                bout_date=_date(item["bout_date"]) if item["bout_date"] else None,
                payload=item["payload"],
            )
        )
        inserted += 1
        if inserted <= 5000:
            db.add(
                DatasetSample(
                    dataset_version_id=version.id,
                    external_id=item["fingerprint"][:80],
                    label="bout",
                    modality="tabular",
                    metadata_json={"tournament": item["tournament_external_id"]},
                )
            )
    db.commit()
    return {
        "dataset_id": str(dataset.id),
        "competitions": len(parsed["competitions"]),
        "athletes": len(parsed["athletes"]),
        "bouts_inserted": inserted,
        "duplicate_bouts": parsed["duplicate_bouts"],
        "rejected_bouts": parsed["rejected_bouts"],
        "provenance": parsed["provenance"],
    }


def _store_inspected(db: Session, principal: Principal, parsed: dict, *, license: str, allowed: list[str]) -> dict:
    dataset = Dataset(
        organization_id=principal.organization.id,
        name=parsed["name"],
        source_url="",
        license=license,
        access_status="local-only",
        allowed_uses=allowed,
        notes=parsed.get("note") or "Local inspection only. Samples are not redistributed.",
    )
    db.add(dataset)
    db.flush()
    version = DatasetVersion(
        dataset_id=dataset.id,
        version="local",
        import_status="inspected",
        sample_count=parsed.get("sample_count") or 0,
        modalities=[item for item in parsed.get("modalities") or [] if item],
        labels=list((parsed.get("labels") or {}).keys()),
        schema_name=parsed["name"].lower(),
        provenance={"rgb_competition_footage": parsed.get("rgb_competition_footage", False)},
    )
    db.add(version)
    db.flush()
    for sample in (parsed.get("samples") or [])[:2000]:
        db.add(
            DatasetSample(
                dataset_version_id=version.id,
                external_id=str(sample.get("external_id") or "")[:200],
                label=sample.get("label") or "",
                modality=sample.get("modality") or "",
                metadata_json={key: value for key, value in sample.items() if key not in {"external_id", "label", "modality"}},
            )
        )
    db.commit()
    return {"dataset_id": str(dataset.id), "sample_count": version.sample_count, "license": license, "training_allowed": False}


def _date(value: str):
    from datetime import date

    year, month, day = value.split("-")
    return date(int(year), int(month), int(day))


@router.get("/models")
def list_models(principal: Principal = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    rows = db.scalars(select(ModelVersion).order_by(ModelVersion.name)).all()
    return {
        "items": [
            {
                "id": str(row.id),
                "name": row.name,
                "version": row.version,
                "status": row.status,
                "metrics": row.metrics,
                "notes": row.notes,
            }
            for row in rows
        ]
    }


@router.get("/target-areas")
def target_areas(principal: Principal = Depends(require_role("viewer"))):
    from fencing_domain.taxonomy import TARGET_AREAS, target_valid_for_weapon

    items = []
    for area in TARGET_AREAS:
        items.append(
            {
                **area,
                "valid": {
                    "epee": target_valid_for_weapon("epee", area["code"]),
                    "foil": target_valid_for_weapon("foil", area["code"]),
                    "sabre": target_valid_for_weapon("sabre", area["code"]),
                },
            }
        )
    return {"items": items, "note": "Validity is a coaching aid, not a referee decision."}
