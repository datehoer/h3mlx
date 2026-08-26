"""Technical MP4 verification and stable fingerprints."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


def sha256_file(path: str | Path, chunk_size: int = 8 << 20) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def probe(path: str | Path) -> dict[str, Any]:
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        raise RuntimeError("ffprobe is required for media verification")
    source = Path(path).expanduser().resolve()
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            (
                "format=filename,duration,size,bit_rate,format_name:"
                "stream=index,codec_name,codec_type,width,height,r_frame_rate,"
                "avg_frame_rate,nb_frames,channels,channel_layout,sample_rate,bit_rate"
            ),
            "-of",
            "json",
            str(source),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "ffprobe failed")
    return json.loads(result.stdout)


def verify(
    path: str | Path,
    *,
    width: int | None = None,
    height: int | None = None,
    frames: int | None = None,
    fps: int = 24,
    sample_rate: int = 32_000,
    channels: int = 2,
    checksum: bool = True,
) -> dict[str, Any]:
    source = Path(path).expanduser().resolve()
    issues: list[str] = []
    if not source.is_file() or source.stat().st_size == 0:
        return {
            "ok": False,
            "path": str(source),
            "issues": ["output file is missing or empty"],
        }
    data = probe(source)
    streams = data.get("streams", [])
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    audio = next((item for item in streams if item.get("codec_type") == "audio"), None)
    if video is None:
        issues.append("video stream is missing")
    if audio is None:
        issues.append("audio stream is missing")
    if video is not None:
        if video.get("codec_name") != "h264":
            issues.append(f"expected H.264 video, got {video.get('codec_name')}")
        if width is not None and int(video.get("width", -1)) != width:
            issues.append(f"expected width {width}, got {video.get('width')}")
        if height is not None and int(video.get("height", -1)) != height:
            issues.append(f"expected height {height}, got {video.get('height')}")
        if video.get("r_frame_rate") != f"{fps}/1":
            issues.append(f"expected {fps} FPS, got {video.get('r_frame_rate')}")
        if frames is not None and int(video.get("nb_frames", -1)) != frames:
            issues.append(
                f"expected {frames} encoded frames, got {video.get('nb_frames')}"
            )
    if audio is not None:
        if audio.get("codec_name") != "aac":
            issues.append(f"expected AAC audio, got {audio.get('codec_name')}")
        if int(audio.get("sample_rate", -1)) != sample_rate:
            issues.append(
                f"expected {sample_rate} Hz audio, got {audio.get('sample_rate')}"
            )
        if int(audio.get("channels", -1)) != channels:
            issues.append(f"expected {channels} channels, got {audio.get('channels')}")
    duration = float(data.get("format", {}).get("duration", 0.0))
    if frames is not None:
        expected_duration = frames / fps
        if abs(duration - expected_duration) > 1 / fps:
            issues.append(
                f"expected duration {expected_duration:.6f}s, got {duration:.6f}s"
            )
    report: dict[str, Any] = {
        "ok": not issues,
        "path": str(source),
        "issues": issues,
        "probe": data,
    }
    if checksum:
        report["sha256"] = sha256_file(source)
    return report
