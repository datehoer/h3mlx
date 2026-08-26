"""Configuration loading for h3mlx.

The project never copies or owns model weights. A local TOML file points to an
existing mlx-h3 checkout, its virtual environment, model files, and output root.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MODEL_KEYS = (
    "tokenizer",
    "text_encoder",
    "dit",
    "video_vae",
    "audio_vae",
    "turbo_lora",
)


def _path(value: str, base: Path) -> Path:
    expanded = Path(os.path.expandvars(value)).expanduser()
    return expanded if expanded.is_absolute() else (base / expanded).resolve()


@dataclass(frozen=True)
class RuntimeConfig:
    repo: Path
    executable: Path
    python: Path


@dataclass(frozen=True)
class ModelConfig:
    tokenizer: Path
    text_encoder: Path
    dit: Path
    video_vae: Path
    audio_vae: Path
    turbo_lora: Path

    def items(self):
        for key in MODEL_KEYS:
            yield key, getattr(self, key)


@dataclass(frozen=True)
class Preset:
    width: int
    height: int
    frames: int
    steps: int
    seed: int
    budget: int

    def __post_init__(self) -> None:
        if self.width < 32 or self.height < 32:
            raise ValueError("preset width and height must be at least 32")
        if self.width % 32 or self.height % 32:
            raise ValueError("preset width and height must be multiples of 32")
        if self.width * self.height > 768 * 1344:
            raise ValueError("preset canvas exceeds the H3 768*1344 pixel limit")
        if self.frames < 5 or self.frames > 362 or self.frames % 17 != 5:
            raise ValueError(
                "preset frames must be in [5, 362] and satisfy frames % 17 == 5"
            )
        if not 4 <= self.steps <= 8:
            raise ValueError("Turbo preset steps must be in [4, 8]")
        if self.seed < 0:
            raise ValueError("preset seed must be non-negative")
        if self.budget < 1:
            raise ValueError("preset budget must be positive")


@dataclass(frozen=True)
class ProjectConfig:
    source: Path
    runtime: RuntimeConfig
    models: ModelConfig
    output_dir: Path
    run_dir: Path
    default_preset: str
    presets: dict[str, Preset]

    def preset(self, name: str | None = None) -> Preset:
        selected = name or self.default_preset
        try:
            return self.presets[selected]
        except KeyError as error:
            choices = ", ".join(sorted(self.presets))
            raise ValueError(
                f"unknown preset {selected!r}; choose one of: {choices}"
            ) from error


def _required_table(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"missing [{key}] table")
    return value


def load_config(path: str | Path = "h3mlx.local.toml") -> ProjectConfig:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(
            f"configuration not found: {source}\n"
            "Copy h3mlx.example.toml to h3mlx.local.toml and edit its paths."
        )
    with source.open("rb") as handle:
        data = tomllib.load(handle)
    base = source.parent
    runtime_data = _required_table(data, "runtime")
    models_data = _required_table(data, "models")
    storage_data = _required_table(data, "storage")
    defaults_data = _required_table(data, "defaults")
    presets_data = _required_table(data, "presets")

    missing_models = [key for key in MODEL_KEYS if key not in models_data]
    if missing_models:
        raise ValueError(f"missing model paths: {', '.join(missing_models)}")

    presets: dict[str, Preset] = {}
    for name, raw in presets_data.items():
        if not isinstance(raw, dict):
            raise ValueError(f"[presets.{name}] must be a table")
        presets[name] = Preset(
            width=int(raw["width"]),
            height=int(raw["height"]),
            frames=int(raw["frames"]),
            steps=int(raw["steps"]),
            seed=int(raw["seed"]),
            budget=int(raw["budget"]),
        )
    if not presets:
        raise ValueError("at least one [presets.NAME] table is required")

    config = ProjectConfig(
        source=source,
        runtime=RuntimeConfig(
            repo=_path(str(runtime_data["repo"]), base),
            executable=_path(str(runtime_data["executable"]), base),
            python=_path(str(runtime_data["python"]), base),
        ),
        models=ModelConfig(
            **{key: _path(str(models_data[key]), base) for key in MODEL_KEYS}
        ),
        output_dir=_path(str(storage_data["output_dir"]), base),
        run_dir=_path(str(storage_data["run_dir"]), base),
        default_preset=str(defaults_data["preset"]),
        presets=presets,
    )
    config.preset()
    return config
