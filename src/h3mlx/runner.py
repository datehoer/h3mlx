"""Auditable subprocess runner for the external mlx-h3 CLI."""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import Preset, ProjectConfig
from .verification import verify


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-.")
    return cleaned[:80] or "generation"


def build_command(
    config: ProjectConfig,
    prompt: str,
    preset: Preset,
    output: Path,
) -> list[str]:
    models = config.models
    return [
        str(config.runtime.executable),
        prompt,
        "--width",
        str(preset.width),
        "--height",
        str(preset.height),
        "--frames",
        str(preset.frames),
        "--steps",
        str(preset.steps),
        "--seed",
        str(preset.seed),
        "--budget",
        str(preset.budget),
        "--tokenizer",
        str(models.tokenizer),
        "--text-encoder",
        str(models.text_encoder),
        "--dit",
        str(models.dit),
        "--video-vae",
        str(models.video_vae),
        "--audio-vae",
        str(models.audio_vae),
        "--turbo-lora",
        str(models.turbo_lora),
        "--output",
        str(output),
    ]


def run_generation(
    config: ProjectConfig,
    *,
    prompt: str,
    preset_name: str | None = None,
    name: str = "generation",
    output: str | Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    if not prompt.strip():
        raise ValueError("prompt must not be empty")
    selected_name = preset_name or config.default_preset
    preset = config.preset(selected_name)
    now = datetime.now().astimezone()
    run_id = f"{now:%Y%m%d-%H%M%S}-{_slug(name)}"
    output_path = (
        Path(output).expanduser().resolve()
        if output is not None
        else config.output_dir / f"{run_id}.mp4"
    )
    run_path = config.run_dir / run_id
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_path}")
    command = build_command(config, prompt, preset, output_path)
    public_command = command.copy()
    public_command[1] = f"<prompt from {run_path / 'prompt.txt'}>"
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "run_id": run_id,
        "status": "dry_run" if dry_run else "running",
        "created_at": now.isoformat(),
        "config": str(config.source),
        "preset": selected_name,
        "parameters": asdict(preset),
        "runtime_repo": str(config.runtime.repo),
        "models": {key: str(path) for key, path in config.models.items()},
        "prompt_file": str(run_path / "prompt.txt"),
        "log_file": str(run_path / "run.log"),
        "output": str(output_path),
        "command": public_command,
    }
    if dry_run:
        return manifest

    run_path.mkdir(parents=True, exist_ok=False)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    (run_path / "prompt.txt").write_text(prompt.rstrip() + "\n", encoding="utf-8")
    _write_json(run_path / "manifest.json", manifest)
    started = datetime.now().astimezone()
    return_code = -1
    interrupted = False
    try:
        with (run_path / "run.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                command,
                cwd=config.runtime.repo,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=os.environ.copy(),
            )
            assert process.stdout is not None
            try:
                for line in process.stdout:
                    print(line, end="", flush=True)
                    log.write(line)
                    log.flush()
                return_code = process.wait()
            except KeyboardInterrupt:
                interrupted = True
                process.terminate()
                return_code = process.wait()
    except OSError as error:
        manifest["launch_error"] = str(error)
    ended = datetime.now().astimezone()
    manifest["return_code"] = return_code
    manifest["started_at"] = started.isoformat()
    manifest["ended_at"] = ended.isoformat()
    manifest["elapsed_seconds"] = (ended - started).total_seconds()

    if return_code == 0 and output_path.is_file():
        report = verify(
            output_path,
            width=preset.width,
            height=preset.height,
            frames=preset.frames,
        )
        _write_json(run_path / "verification.json", report)
        manifest["verification_file"] = str(run_path / "verification.json")
        manifest["status"] = "completed" if report["ok"] else "verification_failed"
    else:
        manifest["status"] = "interrupted" if interrupted else "failed"
    _write_json(run_path / "manifest.json", manifest)
    if interrupted:
        raise KeyboardInterrupt
    return manifest


def latest_runs(config: ProjectConfig, limit: int = 10) -> list[dict[str, Any]]:
    if not config.run_dir.is_dir():
        return []
    manifests = sorted(config.run_dir.glob("*/manifest.json"), reverse=True)
    runs: list[dict[str, Any]] = []
    for path in manifests[:limit]:
        try:
            runs.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            runs.append({"status": "invalid_manifest", "manifest": str(path)})
    return runs
