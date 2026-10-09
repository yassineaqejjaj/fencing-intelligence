"""Original scoreboard light detector.

A bright red or green cluster inside a user-selected region creates a candidate
touch time. It does not decide which fencer has priority and it does not read
an official referee call from the lamp.
"""

from __future__ import annotations


def _channel_mean(frame: list[list[tuple[int, int, int]]], roi: dict) -> tuple[float, float, float]:
    height = len(frame)
    width = len(frame[0]) if height else 0
    x0 = max(0, min(width - 1, int(roi["x"] * width)))
    y0 = max(0, min(height - 1, int(roi["y"] * height)))
    x1 = max(x0 + 1, min(width, int((roi["x"] + roi["w"]) * width)))
    y1 = max(y0 + 1, min(height, int((roi["y"] + roi["h"]) * height)))
    count = 0
    red = green = blue = 0
    for y in range(y0, y1):
        for x in range(x0, x1):
            r, g, b = frame[y][x]
            red += r
            green += g
            blue += b
            count += 1
    if count == 0:
        return 0.0, 0.0, 0.0
    return red / count, green / count, blue / count


def detect_light_candidates(frames: list[dict], roi: dict) -> list[dict]:
    """`frames` items are `{t_ms, pixels}` where pixels are RGB rows.

    A candidate is emitted when red or green becomes dominant and stays above
    the threshold for at least one sample. Score digits are not read.
    """
    if not roi or roi.get("w", 0) <= 0 or roi.get("h", 0) <= 0:
        return []
    active: str | None = None
    started: int | None = None
    candidates: list[dict] = []
    for frame in frames:
        red, green, blue = _channel_mean(frame["pixels"], roi)
        color = None
        if red > 140 and red > green * 1.6 and red > blue * 1.4:
            color = "red"
        elif green > 140 and green > red * 1.6 and green > blue * 1.4:
            color = "green"
        if color and active is None:
            active = color
            started = frame["t_ms"]
        elif color is None and active is not None:
            candidates.append(
                {
                    "color": active,
                    "start_ms": started,
                    "end_ms": frame["t_ms"],
                    "source": "scoreboard_candidate",
                    "validated": False,
                    "score_value": None,
                    "score_value_status": "not_extracted",
                    "referee_decision": None,
                    "note": "Light change only. A person must confirm the touch and the score.",
                }
            )
            active = None
            started = None
    if active is not None and frames:
        candidates.append(
            {
                "color": active,
                "start_ms": started,
                "end_ms": frames[-1]["t_ms"],
                "source": "scoreboard_candidate",
                "validated": False,
                "score_value": None,
                "score_value_status": "not_extracted",
                "referee_decision": None,
                "note": "Light change only. A person must confirm the touch and the score.",
            }
        )
    return candidates


def pixel_distance(point_a: dict, point_b: dict, width: int, height: int) -> float:
    ax = point_a["x"] * width
    ay = point_a["y"] * height
    bx = point_b["x"] * width
    by = point_b["y"] * height
    return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5


def calibrated_distance_m(point_a: dict, point_b: dict, calibration: dict | None, width: int, height: int) -> dict:
    pixels = pixel_distance(point_a, point_b, width, height)
    if not calibration or not calibration.get("piste_length_m") or not calibration.get("point_a") or not calibration.get("point_b"):
        return {"unit": "pixels", "value": pixels, "meters": None, "reason": "not_calibrated"}
    reference = pixel_distance(calibration["point_a"], calibration["point_b"], width, height)
    if reference <= 0:
        return {"unit": "pixels", "value": pixels, "meters": None, "reason": "invalid_calibration"}
    meters = pixels / reference * float(calibration["piste_length_m"])
    return {"unit": "meters", "value": meters, "meters": meters, "reason": None}
