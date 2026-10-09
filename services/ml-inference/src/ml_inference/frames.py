"""Optional OpenCV helpers. Missing OpenCV is reported as unavailable, not as a result."""

from __future__ import annotations

from pathlib import Path


class CapabilityUnavailable(RuntimeError):
    pass


def sample_roi_colors(video_path: Path, roi: dict, *, step_ms: int = 200, limit: int = 400) -> list[dict]:
    try:
        import cv2
    except ImportError as exc:
        raise CapabilityUnavailable("opencv-python-headless is not installed") from exc
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise CapabilityUnavailable("Could not open the video for frame sampling")
    fps = capture.get(cv2.CAP_PROP_FPS) or 25
    step = max(1, int(round((step_ms / 1000) * fps)))
    frames = []
    index = 0
    try:
        while len(frames) < limit:
            ok, frame = capture.read()
            if not ok:
                break
            if index % step == 0:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                height, width = rgb.shape[:2]
                x0 = max(0, min(width - 1, int(roi["x"] * width)))
                y0 = max(0, min(height - 1, int(roi["y"] * height)))
                x1 = max(x0 + 1, min(width, int((roi["x"] + roi["w"]) * width)))
                y1 = max(y0 + 1, min(height, int((roi["y"] + roi["h"]) * height)))
                crop = rgb[y0:y1, x0:x1]
                pixels = [[(int(pixel[0]), int(pixel[1]), int(pixel[2])) for pixel in row] for row in crop]
                frames.append({"t_ms": int(index / fps * 1000), "pixels": pixels})
            index += 1
    finally:
        capture.release()
    return frames
