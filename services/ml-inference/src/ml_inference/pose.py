"""Pose landmarks from the Apache-2.0 MediaPipe pose landmarker.

The output is image-normalized joint positions. It is not a fencing action,
priority decision, or measured distance.
"""

from __future__ import annotations

from pathlib import Path

from ml_inference.frames import CapabilityUnavailable


def model_file() -> Path:
    return Path(__file__).resolve().parent / "models" / "pose_landmarker_lite.task"


def estimate_rgb(rgb) -> dict:
    landmarker = _landmarker()
    try:
        poses = _detect(landmarker, rgb)
    finally:
        landmarker.close()
    return {
        "poses": poses,
        "claim_accuracy": False,
        "tactical_labels": False,
        "note": "Joint positions only. They do not identify an attack, parry, or priority.",
    }


def estimate_poses(video_path: Path, *, step_ms: int = 400, limit: int = 12) -> dict:
    try:
        import cv2
    except ImportError as exc:
        raise CapabilityUnavailable("OpenCV is not installed") from exc
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise CapabilityUnavailable("Could not open the video for pose estimation")
    fps = capture.get(cv2.CAP_PROP_FPS) or 25
    step = max(1, int(round((step_ms / 1000) * fps)))
    frames = []
    index = 0
    landmarker = _landmarker()
    try:
        while len(frames) < limit:
            ok, frame = capture.read()
            if not ok:
                break
            if index % step == 0:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append({"t_ms": int(index / fps * 1000), "poses": _detect(landmarker, rgb)})
            index += 1
    finally:
        capture.release()
        landmarker.close()
    poses = sum(len(frame["poses"]) for frame in frames)
    return {
        "model": "pose_landmarker_lite",
        "model_license": "Apache-2.0",
        "claim_accuracy": False,
        "tactical_labels": False,
        "frames_sampled": len(frames),
        "poses_found": poses,
        "frames": frames,
        "note": "Joint positions only. They do not identify an attack, parry, or priority.",
    }


def _landmarker():
    path = model_file()
    if not path.is_file():
        raise CapabilityUnavailable("The pose landmarker file is not installed")
    try:
        import mediapipe as mp
        from mediapipe.tasks.python.core.base_options import BaseOptions
        from mediapipe.tasks.python.vision import PoseLandmarker, PoseLandmarkerOptions, RunningMode
    except ImportError as exc:
        raise CapabilityUnavailable("mediapipe is not installed") from exc
    options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(path)),
        running_mode=RunningMode.IMAGE,
        num_poses=2,
    )
    return PoseLandmarker.create_from_options(options)


def _detect(landmarker, rgb) -> list[dict]:
    import mediapipe as mp
    import numpy as np

    image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
    result = landmarker.detect(image)
    poses = []
    for pose in result.pose_landmarks:
        poses.append(
            {
                "landmarks": [
                    {"i": index, "x": point.x, "y": point.y, "visibility": point.visibility}
                    for index, point in enumerate(pose)
                ]
            }
        )
    return poses
