"""Inspect a local MFAD checkout. Samples are not redistributed."""

from __future__ import annotations

import re
from pathlib import Path

from fencing_domain.registry import MFAD_ACTION_MAP

SKELETON_NAME = re.compile(r"^(?P<level>\d+)_p(?P<fencer>\d+)_a(?P<action>[123])_(?P<rep>\d+)\.npy$")
LEVELS = {"1": "amateur", "2": "subelite", "3": "elite"}
SENSOR_FILES = {"hand.txt", "left_foot.txt", "right_foot.txt"}


def inspect_mfad(root: Path) -> dict:
    skeleton = root / "skeleton"
    sensor = root / "sensor"
    if not skeleton.is_dir() and not sensor.is_dir():
        raise FileNotFoundError("MFAD layout not recognized. Expected skeleton/ and or sensor/ directories.")
    samples = []
    fencers: set[str] = set()
    labels: dict[str, int] = {}
    if skeleton.is_dir():
        for path in sorted(skeleton.glob("*.npy")):
            match = SKELETON_NAME.match(path.name)
            if not match:
                samples.append({"external_id": path.name, "label": "", "modality": "skeleton", "valid_name": False})
                continue
            label = MFAD_ACTION_MAP[match.group("action")]
            fencers.add(match.group("fencer"))
            labels[label] = labels.get(label, 0) + 1
            samples.append(
                {
                    "external_id": path.name,
                    "label": label,
                    "modality": "skeleton",
                    "fencer": match.group("fencer"),
                    "level": match.group("level"),
                    "level_name": LEVELS.get(match.group("level"), "unknown"),
                    "repetition": match.group("rep"),
                    "valid_name": True,
                }
            )
    sensor_groups = []
    if sensor.is_dir():
        for folder in sorted(path for path in sensor.iterdir() if path.is_dir()):
            action = folder.name[-1:]
            label = MFAD_ACTION_MAP.get(action, "")
            files = sorted(item.name for item in folder.glob("*.txt"))
            code = folder.name
            sensor_groups.append(
                {
                    "external_id": code,
                    "level": code[:1],
                    "level_name": LEVELS.get(code[:1], "unknown"),
                    "fencer": code[1:-1],
                    "label": label,
                    "modality": "imu",
                    "files": files,
                    "expected_files_present": SENSOR_FILES.issubset(set(files)),
                    "segments": {name: _imu_segments(folder / name) for name in files if name in SENSOR_FILES},
                }
            )
    return {
        "name": "MFAD",
        "rgb_competition_footage": False,
        "modalities": [name for name, present in (("skeleton", bool(samples)), ("imu", bool(sensor_groups))) if present],
        "sample_count": len(samples) + len(sensor_groups),
        "skeleton_count": len(samples),
        "sensor_group_count": len(sensor_groups),
        "fencer_count": len(fencers),
        "labels": labels,
        "samples": samples,
        "sensor_groups": sensor_groups,
        "license": "unspecified",
        "allowed_uses": ["local-inspection-only"],
        "source_url": "https://github.com/EMRGSZU/MFAD",
    }


def _imu_segments(path: Path) -> int:
    """Count attempts separated by the published marker row. Values are not stored."""
    count = 0
    previous_marker = False
    for line in path.read_text(errors="replace").splitlines():
        parts = line.split()
        marker = len(parts) >= 7 and parts[-6:] == ["0", "0", "0", "0", "0", "1000"]
        if marker and not previous_marker:
            count += 1
        previous_marker = marker
    return count
