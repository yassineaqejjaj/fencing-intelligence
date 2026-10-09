"""Normalize a skeleton array to a root-centered, scale-free sequence.

Joint indices for MFAD are not documented in a redistributable schema, so this
uses the mean joint as the origin and the mean distance from that origin as the
scale. It does not invent anatomical names.
"""

from __future__ import annotations


def normalize_sequence(array):
    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("numpy is required for skeleton normalization") from exc
    data = np.asarray(array, dtype="float64")
    if data.ndim != 3 or data.shape[-1] not in {2, 3}:
        raise ValueError(f"Expected shape (frames, joints, 2 or 3), got {data.shape}")
    origin = data.mean(axis=1, keepdims=True)
    centered = data - origin
    scale = np.linalg.norm(centered, axis=2).mean(axis=1, keepdims=True)
    scale = np.maximum(scale, 1e-6)
    normalized = centered / scale[:, :, None]
    velocity = np.diff(normalized, axis=0, prepend=normalized[:1])
    return {"normalized": normalized, "velocity": velocity, "frame_count": int(data.shape[0]), "joint_count": int(data.shape[1])}


def temporal_summary(normalized) -> dict:
    import numpy as np

    speed = np.linalg.norm(normalized["velocity"], axis=2).mean(axis=1)
    return {
        "frame_count": normalized["frame_count"],
        "joint_count": normalized["joint_count"],
        "mean_speed": float(speed.mean()) if speed.size else None,
        "max_speed": float(speed.max()) if speed.size else None,
    }
