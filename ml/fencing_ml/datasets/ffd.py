"""Inspect a local Fencing Footwork Dataset directory."""

from __future__ import annotations

from pathlib import Path

from fencing_domain.registry import FFD_CLASS_MAP


def inspect_ffd(root: Path) -> dict:
    if not root.is_dir():
        raise FileNotFoundError("FFD directory does not exist")
    kinds = {
        "*_Body.mat": "kinect_skeleton",
        "*_IMU.mat": "imu",
        "*_Rot.mat": "imu_rotation",
        "*_Depth.avi": "kinect_depth",
    }
    samples = []
    labels: dict[str, int] = {}
    counts = {modality: 0 for modality in kinds.values()}
    for pattern, modality in kinds.items():
        for path in sorted(root.rglob(pattern)):
            label = _label(path)
            counts[modality] += 1
            if modality == "kinect_skeleton":
                labels[label or "unlabeled"] = labels.get(label or "unlabeled", 0) + 1
            samples.append(
                {
                    "external_id": str(path.relative_to(root)),
                    "label": label,
                    "modality": modality,
                    "capture": "kinect" if modality.startswith("kinect") else "x-imu",
                }
            )
    if not samples:
        raise FileNotFoundError("No FFD Body, IMU, rotation, or depth files found")
    return {
        "name": "FFD",
        "source_url": "https://home.agh.edu.pl/~fmal/ffd/",
        "rgb_competition_footage": False,
        "modalities": [name for name, count in counts.items() if count],
        "sample_count": counts["kinect_skeleton"],
        "file_counts": counts,
        "labels": labels,
        "samples": samples,
        "license": "unspecified",
        "note": "Kinect accuracy does not transfer to smartphone RGB video. RGB is not part of this dataset.",
    }


def _label(path: Path) -> str:
    for part in path.parts:
        mapped = FFD_CLASS_MAP.get(part.upper()) or FFD_CLASS_MAP.get(part)
        if mapped:
            return mapped
    stem = path.stem.upper()
    for code, mapped in FFD_CLASS_MAP.items():
        if stem.startswith(code + "_") or f"_{code}_" in f"_{stem}_":
            return mapped
    return ""


def read_body_matrix(path: Path) -> dict:
    """Load one Kinect skeleton matrix when SciPy is installed."""
    try:
        import scipy.io
    except ImportError as exc:
        raise RuntimeError("scipy is required to read MATLAB skeleton files") from exc
    payload = scipy.io.loadmat(path)
    arrays = {key: value for key, value in payload.items() if not key.startswith("_")}
    if not arrays:
        raise RuntimeError("MATLAB file did not contain an array")
    name, array = next(iter(arrays.items()))
    return {"variable": name, "shape": list(array.shape), "columns": int(array.shape[1]) if array.ndim == 2 else None}
