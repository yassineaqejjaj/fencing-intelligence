"""Transcode fencing video to a browser-playable MP4 and a thumbnail.

The worker shells out to ffmpeg and ffprobe. It does not interpret fencing actions.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


class VideoProcessingError(RuntimeError):
    pass


def require_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise VideoProcessingError("ffmpeg and ffprobe must be installed")


def probe(source: Path) -> dict:
    require_ffmpeg()
    completed = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(source),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise VideoProcessingError(completed.stderr.strip() or "ffprobe failed")
    payload = json.loads(completed.stdout or "{}")
    streams = payload.get("streams", [])
    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    has_audio = any(stream.get("codec_type") == "audio" for stream in streams)
    if video_stream is None:
        raise VideoProcessingError("No video stream found")
    width = int(video_stream.get("width") or 0)
    height = int(video_stream.get("height") or 0)
    fps = _frame_rate(video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate") or "0/1")
    duration = float(payload.get("format", {}).get("duration") or video_stream.get("duration") or 0)
    rotation = 0
    for side in video_stream.get("side_data_list") or []:
        if "rotation" in side:
            rotation = int(side["rotation"])
    tags = video_stream.get("tags") or {}
    if "rotate" in tags:
        rotation = int(tags["rotate"])
    if rotation in {90, 270, -90}:
        width, height = height, width
    orientation = "portrait" if height > width else "landscape" if width > height else "square"
    return {
        "duration_seconds": duration,
        "fps": fps,
        "width": width,
        "height": height,
        "orientation": orientation,
        "rotation": rotation,
        "has_audio": has_audio,
        "probe": {"format": payload.get("format", {}), "video": {"codec": video_stream.get("codec_name"), "width": width, "height": height}},
    }


def transcode(source: Path, playback: Path, thumbnail: Path) -> dict:
    """Write an H.264 MP4 with faststart and a JPEG thumbnail."""
    metadata = probe(source)
    playback.parent.mkdir(parents=True, exist_ok=True)
    thumbnail.parent.mkdir(parents=True, exist_ok=True)
    transcode_cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-vf",
        "scale='min(1920,iw)':-2",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
    ]
    if metadata.get("has_audio"):
        transcode_cmd.extend(["-c:a", "aac"])
    else:
        transcode_cmd.append("-an")
    transcode_cmd.append(str(playback))
    _run(transcode_cmd, "transcode")
    thumb_cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        "0.2",
        "-i",
        str(playback),
        "-frames:v",
        "1",
        str(thumbnail),
    ]
    _run(thumb_cmd, "thumbnail")
    metadata["playback_bytes"] = playback.stat().st_size
    metadata["thumbnail_bytes"] = thumbnail.stat().st_size
    return metadata


def _run(command: list[str], label: str) -> None:
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise VideoProcessingError(f"{label} failed: {detail[-500:]}")


def _frame_rate(value: str) -> float:
    if not value or value == "0/0":
        return 0.0
    if "/" in value:
        num, den = value.split("/", 1)
        denominator = float(den)
        if denominator == 0:
            return 0.0
        return float(num) / denominator
    return float(value)
