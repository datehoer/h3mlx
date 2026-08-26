"""Read-only environment and checkpoint compatibility checks."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .config import ProjectConfig
from .safetensors import summarize


EXPECTED_QUANTIZATION = {
    "text_encoder": "affine 2-bit g64",
    "dit": "affine 4-bit g64",
}


def _run(
    command: list[str], cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command, cwd=cwd, capture_output=True, text=True, check=False
        )
    except OSError as error:
        return subprocess.CompletedProcess(command, 127, "", str(error))


def _runtime_versions(config: ProjectConfig) -> tuple[dict[str, str], str | None]:
    if not config.runtime.python.is_file():
        return {}, "runtime Python is missing"
    code = (
        "import importlib.metadata as m, json, platform; "
        "print(json.dumps({'python': platform.python_version(), "
        "'mlx': m.version('mlx'), 'mlx_h3': m.version('mlx-h3')}))"
    )
    result = _run([str(config.runtime.python), "-c", code])
    if result.returncode:
        return {}, result.stderr.strip() or "could not query runtime versions"
    return json.loads(result.stdout), None


def _mlx_device(config: ProjectConfig) -> tuple[dict[str, Any], str | None]:
    code = "import mlx.core as mx, json; print(json.dumps(mx.device_info()))"
    result = _run([str(config.runtime.python), "-c", code])
    if result.returncode:
        return {}, result.stderr.strip() or "could not query MLX device"
    return json.loads(result.stdout), None


def _git(config: ProjectConfig) -> dict[str, Any]:
    commit = _run(["git", "rev-parse", "--short", "HEAD"], config.runtime.repo)
    status = _run(["git", "status", "--short"], config.runtime.repo)
    return {
        "commit": commit.stdout.strip() if commit.returncode == 0 else None,
        "dirty": bool(status.stdout.strip()),
        "changes": status.stdout.splitlines(),
    }


def inspect(config: ProjectConfig) -> dict[str, Any]:
    issues: list[str] = []
    warnings: list[str] = []
    system = {
        "platform": platform.platform(),
        "system": platform.system(),
        "machine": platform.machine(),
    }
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        issues.append("h3mlx requires macOS on Apple Silicon (Darwin arm64)")

    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if ffmpeg is None:
        issues.append("ffmpeg is not available on PATH")
    if ffprobe is None:
        issues.append("ffprobe is not available on PATH")
    if not config.runtime.repo.is_dir():
        issues.append(f"runtime repository is missing: {config.runtime.repo}")
    if not config.runtime.executable.is_file():
        issues.append(f"mlx-h3 executable is missing: {config.runtime.executable}")

    versions, version_error = _runtime_versions(config)
    if version_error:
        issues.append(version_error)
    device, device_error = _mlx_device(config)
    if device_error:
        issues.append(device_error)
    else:
        limit = int(device.get("max_recommended_working_set_size", 0))
        for name, preset in config.presets.items():
            if preset.budget * (1 << 30) >= limit:
                issues.append(
                    f"preset {name} budget {preset.budget} GiB is not below the "
                    f"MLX working-set limit {limit / (1 << 30):.1f} GiB"
                )

    models: dict[str, Any] = {}
    for role, path in config.models.items():
        if not path.is_file():
            issues.append(f"missing {role}: {path}")
            continue
        if path.suffix == ".safetensors":
            try:
                models[role] = summarize(path)
            except (OSError, ValueError, json.JSONDecodeError) as error:
                issues.append(f"could not read {role} header: {error}")
        else:
            models[role] = {
                "path": str(path),
                "resolved_path": str(path.resolve()),
                "is_symlink": path.is_symlink(),
                "size_bytes": os.path.getsize(path.resolve()),
            }
    for role, expected in EXPECTED_QUANTIZATION.items():
        actual = models.get(role, {}).get("metadata", {}).get("quantization")
        if actual != expected:
            issues.append(f"{role} quantization is {actual!r}, expected {expected!r}")
    if models.get("video_vae", {}).get("dtypes") != {"F16": 562}:
        warnings.append("Video VAE does not match the verified 562-tensor FP16 file")
    if models.get("audio_vae", {}).get("dtypes") != {"F32": 917}:
        warnings.append("Audio VAE does not match the verified 917-tensor FP32 file")
    if models.get("turbo_lora", {}).get("dtypes") != {"BF16": 518}:
        warnings.append(
            "Turbo LoRA does not match the verified 518-tensor BF16 adapter"
        )

    loader = config.runtime.repo / "src/mlx_h3/loading.py"
    if loader.is_file() and "unsupported quantization metadata" not in loader.read_text(
        encoding="utf-8"
    ):
        issues.append(
            "mlx-h3 loader lacks the local compact quantization-metadata patch "
            "required by these 2-bit/4-bit MLX-Serve checkpoints"
        )

    usage = shutil.disk_usage(
        config.output_dir.parent if config.output_dir.parent.exists() else Path("/")
    )
    if usage.free < 2 * (1 << 30):
        warnings.append("less than 2 GiB free near the output directory")

    runtime_git = _git(config) if config.runtime.repo.is_dir() else {}
    if runtime_git.get("dirty"):
        warnings.append(
            "external mlx-h3 checkout has uncommitted changes; the verified profile "
            "expects the compact-metadata loader patch and its test"
        )

    return {
        "status": "ok" if not issues else "blocked",
        "issues": issues,
        "warnings": warnings,
        "config": str(config.source),
        "system": system,
        "device": device,
        "versions": versions,
        "runtime_git": runtime_git,
        "tools": {"ffmpeg": ffmpeg, "ffprobe": ffprobe},
        "models": models,
        "storage": {
            "output_dir": str(config.output_dir),
            "run_dir": str(config.run_dir),
            "free_bytes": usage.free,
        },
    }
