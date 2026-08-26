"""h3mlx command-line interface."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from pathlib import Path

from .config import load_config
from .doctor import inspect
from .runner import latest_runs, run_generation
from .verification import verify


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="h3mlx", description="Run and audit MiniMax H3 on Apple Silicon."
    )
    parser.add_argument("--config", default="h3mlx.local.toml")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="check runtime, models, memory, and tools")
    doctor.add_argument("--json", action="store_true")

    show = sub.add_parser("show-config", help="show resolved local configuration")
    show.add_argument("--json", action="store_true")

    generate = sub.add_parser("generate", help="generate and record one auditable run")
    prompt_group = generate.add_mutually_exclusive_group(required=True)
    prompt_group.add_argument("--prompt")
    prompt_group.add_argument("--prompt-file")
    generate.add_argument("--preset")
    generate.add_argument("--name", default="generation")
    generate.add_argument("--output")
    generate.add_argument("--width", type=int)
    generate.add_argument("--height", type=int)
    generate.add_argument("--frames", type=int)
    generate.add_argument("--steps", type=int)
    generate.add_argument("--seed", type=int)
    generate.add_argument("--budget", type=int)
    generate.add_argument("--dry-run", action="store_true")

    status = sub.add_parser("status", help="show recent recorded runs")
    status.add_argument("--limit", type=int, default=10)
    status.add_argument("--json", action="store_true")

    check = sub.add_parser("verify", help="verify an existing generated MP4")
    check.add_argument("path")
    check.add_argument("--width", type=int)
    check.add_argument("--height", type=int)
    check.add_argument("--frames", type=int)
    check.add_argument("--no-checksum", action="store_true")
    check.add_argument("--write")
    return parser


def _dump(value) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, default=str))


def main() -> int:
    args = _parser().parse_args()
    try:
        config = load_config(args.config)
        if args.command == "doctor":
            report = inspect(config)
            if args.json:
                _dump(report)
            else:
                print(f"status: {report['status']}")
                print(f"device: {report['device'].get('device_name', 'unknown')}")
                print(
                    "versions: "
                    + ", ".join(
                        f"{key}={value}" for key, value in report["versions"].items()
                    )
                )
                print(f"models: {len(report['models'])}/6 readable")
                for warning in report["warnings"]:
                    print(f"warning: {warning}")
                for issue in report["issues"]:
                    print(f"blocked: {issue}")
            return 0 if report["status"] == "ok" else 2

        if args.command == "show-config":
            value = {
                "source": str(config.source),
                "runtime": {
                    key: str(value) for key, value in asdict(config.runtime).items()
                },
                "models": {key: str(value) for key, value in config.models.items()},
                "output_dir": str(config.output_dir),
                "run_dir": str(config.run_dir),
                "default_preset": config.default_preset,
                "presets": {
                    key: asdict(value) for key, value in config.presets.items()
                },
            }
            _dump(value)
            return 0

        if args.command == "generate":
            prompt = args.prompt
            if args.prompt_file:
                prompt = (
                    Path(args.prompt_file)
                    .expanduser()
                    .read_text(encoding="utf-8")
                    .rstrip()
                )
            preset_name = args.preset or config.default_preset
            base = config.preset(preset_name)
            overrides = {
                key: value
                for key, value in {
                    "width": args.width,
                    "height": args.height,
                    "frames": args.frames,
                    "steps": args.steps,
                    "seed": args.seed,
                    "budget": args.budget,
                }.items()
                if value is not None
            }
            if overrides:
                custom_name = f"{preset_name}+cli"
                config.presets[custom_name] = replace(base, **overrides)
                preset_name = custom_name
            manifest = run_generation(
                config,
                prompt=prompt or "",
                preset_name=preset_name,
                name=args.name,
                output=args.output,
                dry_run=args.dry_run,
            )
            _dump(manifest)
            return 0 if manifest["status"] in ("completed", "dry_run") else 1

        if args.command == "status":
            runs = latest_runs(config, args.limit)
            if args.json:
                _dump(runs)
            elif not runs:
                print("no recorded runs")
            else:
                for run in runs:
                    print(
                        f"{run.get('run_id', '?')}  {run.get('status', '?')}  {run.get('output', '')}"
                    )
            return 0

        if args.command == "verify":
            report = verify(
                args.path,
                width=args.width,
                height=args.height,
                frames=args.frames,
                checksum=not args.no_checksum,
            )
            if args.write:
                Path(args.write).write_text(
                    json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
            _dump(report)
            return 0 if report["ok"] else 2
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as error:
        print(f"error: {error}")
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
