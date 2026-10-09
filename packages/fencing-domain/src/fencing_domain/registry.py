"""Known external datasets. Nothing here downloads or vendors their files."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    version: str
    source_url: str
    license: str
    access_status: str
    import_status: str
    modalities: tuple[str, ...]
    labels: tuple[str, ...]
    schema: str
    allowed_uses: tuple[str, ...]
    notes: str
    rgb_competition_footage: bool = False
    bundled: bool = False


DATASETS: tuple[DatasetSpec, ...] = (
    DatasetSpec(
        name="MFAD",
        version="github-main",
        source_url="https://github.com/EMRGSZU/MFAD",
        license="unspecified",
        access_status="external",
        import_status="adapter-ready",
        modalities=("skeleton", "imu"),
        labels=("lunge", "one_step_forward_lunge", "fleche"),
        schema="mfad-npy-and-imu-txt",
        allowed_uses=("local-inspection-only",),
        notes=(
            "https://github.com/EMRGSZU/MFAD has no license file. Treat it as all rights reserved and do not redistribute it. "
            "Place a local copy under data/datasets/MFAD with skeleton/*.npy and sensor/<code>/{hand,left_foot,right_foot}.txt. "
            "Skeleton names are {level}_p{fencer}_a{action}_{rep}.npy. Levels are amateur, sub-elite, and elite. "
            "Actions are lunge, one-step forward lunge, and fleche. This is depth-camera skeleton and IMU data, not RGB competition video."
        ),
        rgb_competition_footage=False,
    ),
    DatasetSpec(
        name="FFD",
        version="public-page",
        source_url="https://home.agh.edu.pl/~fmal/ffd/",
        license="unspecified",
        access_status="external",
        import_status="adapter-ready",
        modalities=("kinect_skeleton", "kinect_depth", "imu"),
        labels=(
            "step_forward",
            "step_backward",
            "rapid_lunge",
            "incremental_speed_lunge",
            "lunge_with_waiting",
            "jumping_sliding_lunge",
        ),
        schema="matlab-body-mat",
        allowed_uses=("local-inspection-only",),
        notes=(
            "Published Kinect and IMU footwork set at https://home.agh.edu.pl/~fmal/ffd/. "
            "The page does not state a license, so the files are not downloaded or redistributed. "
            "Place a local copy under data/datasets/FFD. "
            "Files are *_Body.mat (n×161), *_IMU.mat (n×10), *_Rot.mat (n×17), and *_Depth.avi. "
            "RGB is not included. Kinect results do not transfer to smartphone video."
        ),
        rgb_competition_footage=False,
    ),
    DatasetSpec(
        name="FIE-fencing-dataset",
        version="github-main",
        source_url="https://github.com/amichaelsen/fie-fencing-dataset",
        license="GPL-3.0",
        access_status="external",
        import_status="adapter-ready",
        modalities=("tabular",),
        labels=("competition", "bout", "athlete", "ranking"),
        schema="fie-csv-v1",
        allowed_uses=("import-user-supplied-csv",),
        notes=(
            "The generator repository is GPL-3.0. This project does not copy that code. "
            "A separate CSV reader understands the published column names. "
            "Competition results may have their own rights beyond the repository license. "
            "Kaggle mirrors must be checked individually; a CC0 label on one export does not "
            "relicense the generator."
        ),
    ),
    DatasetSpec(
        name="fencing-AI",
        version="github-master",
        source_url="https://github.com/sholtodouglas/fencing-AI",
        license="unspecified",
        access_status="external",
        import_status="not-imported",
        modalities=("rgb_video", "scoreboard"),
        labels=("left_point", "right_point", "no_point"),
        schema="method-reference",
        allowed_uses=(),
        notes=(
            "https://github.com/sholtodouglas/fencing-AI has no license file. Its code, clips, and classifier file are not reused. "
            "The published method cuts clips at scoreboard lights and trains a model on those clips. "
            "This product keeps an original light detector. A light is a candidate event, not a referee decision."
        ),
        rgb_competition_footage=True,
    ),
    DatasetSpec(
        name="FencingVision",
        version="github-main",
        source_url="https://github.com/Ph1n-Pham/fencing-vision",
        license="unspecified",
        access_status="external",
        import_status="not-imported",
        modalities=("rgb_video", "annotation"),
        labels=(),
        schema="method-reference",
        allowed_uses=(),
        notes=(
            "https://github.com/Ph1n-Pham/fencing-vision has no license file. Its code, YOLOv8 weights, and labeled clips are not reused. "
            "The published app segments body parts for video review. This product uses the Apache-2.0 pose landmarker for joint positions instead."
        ),
        rgb_competition_footage=True,
    ),
    DatasetSpec(
        name="FIE-rules-taxonomy",
        version="public-index",
        source_url="https://fie.org/documents/rules",
        license="official-documents-not-vendored",
        access_status="reference",
        import_status="taxonomy-seeded",
        modalities=("taxonomy",),
        labels=("weapon", "target", "action", "priority", "scoring"),
        schema="fencing-domain-taxonomy-v1",
        allowed_uses=("terminology",),
        notes="Rule PDFs are not stored in this repository. The taxonomy records the source URL and version label.",
    ),
    DatasetSpec(
        name="athlete-uploads",
        version="product",
        source_url="local",
        license="private",
        access_status="private",
        import_status="product-feature",
        modalities=("rgb_video", "annotation"),
        labels=(),
        schema="consent-record",
        allowed_uses=("owner-analysis",),
        notes="Private uploads are never used for training unless a consent record grants that purpose.",
    ),
    DatasetSpec(
        name="FI-synthetic-epee",
        version="1",
        source_url="local",
        license="Apache-2.0",
        access_status="bundled",
        import_status="installed",
        modalities=("tabular",),
        labels=("lunge", "advance", "retreat", "fleche", "en_garde"),
        schema="synthetic-action-csv-v1",
        allowed_uses=("pipeline-check",),
        notes=(
            "Original rows written for this project. They are not MFAD, FFD, FIE, fencing-AI, or FencingVision samples. "
            "Use them to exercise import and evaluation code. They are not competition footage and not a trained recognizer."
        ),
        bundled=True,
    ),
)


FFD_CLASS_MAP = {
    "SF": "step_forward",
    "SB": "step_backward",
    "R": "rapid_lunge",
    "IS": "incremental_speed_lunge",
    "W": "lunge_with_waiting",
    "WW": "lunge_with_waiting",
    "JS": "jumping_sliding_lunge",
}

MFAD_ACTION_MAP = {
    "1": "lunge",
    "2": "one_step_forward_lunge",
    "3": "fleche",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def doctor(root: Path | None) -> dict:
    """Report installed, missing, restricted and incompatible datasets.

    A dataset is installed only when a local manifest exists under
    `{root}/{name}/manifest.json` and every listed file is present with the
    expected sha256. Restricted means the license does not allow redistribution
    or training. Incompatible means the license is unspecified or the upstream
    code license forbids copying it into this application.
    """
    root = root or Path("data/datasets")
    reports = []
    for spec in DATASETS:
        entry = {
            "name": spec.name,
            "version": spec.version,
            "source_url": spec.source_url,
            "license": spec.license,
            "access_status": spec.access_status,
            "import_status": spec.import_status,
            "modalities": list(spec.modalities),
            "labels": list(spec.labels),
            "schema": spec.schema,
            "allowed_uses": list(spec.allowed_uses),
            "notes": spec.notes,
            "rgb_competition_footage": spec.rgb_competition_footage,
            "sample_count": None,
            "file_hashes": {},
            "provenance": spec.source_url,
        }
        if spec.license in {"unspecified", "GPL-3.0"}:
            entry["compatibility"] = "incompatible"
        elif spec.license == "private":
            entry["compatibility"] = "restricted"
        elif spec.license == "official-documents-not-vendored":
            entry["compatibility"] = "reference"
        else:
            entry["compatibility"] = "usable"

        if spec.bundled:
            manifest_path = Path(__file__).resolve().parent / "bundled" / spec.name / "manifest.json"
        else:
            manifest_path = root / spec.name / "manifest.json"
        if spec.name == "FIE-rules-taxonomy":
            entry["presence"] = "reference"
        elif spec.name == "athlete-uploads":
            entry["presence"] = "product"
        elif not manifest_path.is_file():
            entry["presence"] = "missing"
        else:
            manifest = json.loads(manifest_path.read_text())
            files = manifest.get("files") or []
            hashes = {}
            missing_files = []
            for item in files:
                file_path = manifest_path.parent / item["path"]
                if not file_path.is_file():
                    missing_files.append(item["path"])
                    continue
                actual = sha256_file(file_path)
                hashes[item["path"]] = actual
                if item.get("sha256") and item["sha256"] != actual:
                    missing_files.append(item["path"])
            entry["file_hashes"] = hashes
            entry["sample_count"] = manifest.get("sample_count", len(files))
            entry["presence"] = "invalid" if missing_files else "installed"
            entry["missing_files"] = missing_files
            if entry["compatibility"] == "incompatible" and entry["presence"] == "installed":
                entry["compatibility"] = "restricted"
        reports.append(entry)

    return {
        "root": str(root),
        "datasets": reports,
        "counts": {
            "installed": sum(1 for item in reports if item["presence"] == "installed"),
            "missing": sum(1 for item in reports if item["presence"] == "missing"),
            "invalid": sum(1 for item in reports if item["presence"] == "invalid"),
            "restricted": sum(1 for item in reports if item["compatibility"] == "restricted"),
            "incompatible": sum(1 for item in reports if item["compatibility"] == "incompatible"),
        },
    }
