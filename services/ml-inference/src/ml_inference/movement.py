"""Heuristic footwork labels from a single horizontal body coordinate.

This is a geometric rule set, not a classifier trained on fencing video.
`position` is a normalized horizontal coordinate in the image. Increasing
position means movement toward the right of the frame. The caller must say
which direction is forward for the fencer. Without that mapping, labels stay
in image coordinates (`image_right`, `image_left`) instead of advance/retreat.
"""

from __future__ import annotations


def _speed(samples: list[dict], index: int) -> float:
    if index == 0:
        return 0.0
    previous = samples[index - 1]
    current = samples[index]
    dt = (current["t_ms"] - previous["t_ms"]) / 1000
    if dt <= 0:
        return 0.0
    return (current["position"] - previous["position"]) / dt


def classify_track(samples: list[dict], *, forward: str | None = None) -> list[dict]:
    """Label contiguous motion segments.

    `forward` is "image_right" or "image_left" when the piste direction is known.
    Otherwise tactical names such as advance are not used.
    """
    if len(samples) < 3:
        return []
    labels: list[dict] = []
    current: dict | None = None
    for index in range(1, len(samples)):
        speed = _speed(samples, index)
        kind = _kind(speed, forward, low_stance=bool(samples[index].get("low_stance")))
        if current and current["label"] == kind:
            current["end_ms"] = samples[index]["t_ms"]
            current["peak_speed"] = max(current["peak_speed"], abs(speed))
            continue
        if current and current["end_ms"] - current["start_ms"] >= 120:
            labels.append(current)
        current = {
            "label": kind,
            "start_ms": samples[index - 1]["t_ms"],
            "end_ms": samples[index]["t_ms"],
            "peak_speed": abs(speed),
            "source": "heuristic",
            "experimental": True,
            "model": "heuristic-movement",
            "model_version": "0.1.0",
        }
    if current and current["end_ms"] - current["start_ms"] >= 120:
        labels.append(current)
    return [item for item in labels if item["label"] != "hold" or item["end_ms"] - item["start_ms"] >= 400]


def _kind(speed: float, forward: str | None, *, low_stance: bool) -> str:
    magnitude = abs(speed)
    if magnitude < 0.08:
        return "en_garde" if low_stance else "hold"
    direction = "image_right" if speed > 0 else "image_left"
    if magnitude > 2.0:
        base = "fleche"
    elif magnitude > 1.2:
        base = "lunge"
    else:
        base = "move"
    if forward is None:
        return f"{base}_{direction}" if base != "move" else direction
    moving_forward = direction == forward
    if base == "fleche":
        return "fleche" if moving_forward else "retreat"
    if base == "lunge":
        return "lunge" if moving_forward else "retreat"
    return "advance" if moving_forward else "retreat"
