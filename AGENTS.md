# Agent Guide

This repository is the operational layer for reproducible MiniMax H3 generation on
Apple Silicon. It delegates inference to an existing pure-MLX `mlx-h3` checkout and
adds configuration, preflight checks, run manifests, logs, and media verification.

## Read order

1. Read this file.
2. Read `README.md` for the user contract and commands.
3. Read `references/verified-profile.md` before changing models or performance settings.
4. Read `references/architecture.md` before changing the execution pipeline.
5. Read the selected case under `cases/` when reproducing a known run.

## Non-negotiable rules

- This is a macOS Apple Silicon + MLX project. Do not introduce CUDA, PyTorch, or
  ComfyUI into the verified route.
- Treat the external `mlx-h3` checkout as the inference engine. Do not copy its source
  or model weights into this repository.
- Run `./bin/h3mlx doctor` before generation after any runtime, model, OS, MLX, or path
  change. A blocked doctor result means do not start inference.
- Never overwrite an existing output. Every run must get its own run directory,
  prompt file, log, manifest, and verification report.
- Never start a full generation merely to test code. Use unit tests, `doctor`,
  `generate --dry-run`, or the `smoke` preset unless the user explicitly requests an
  expensive render.
- Preserve staged residency in `mlx-h3`: text encoder, DiT, Video VAE, Audio VAE,
  then FFmpeg. Do not make all checkpoints resident together.
- Preserve the local `mlx-h3` compact-quantization metadata patch. The verified
  2-bit/4-bit MLX-Serve weights require it.
- Keep model files, local path configuration, generated media, and runtime run folders
  out of Git. Curated case records under `cases/` are the only tracked prompt/log
  exception.
- Verify both video and audio streams. A file existing is not sufficient evidence of
  success.
- Do not compute multi-gigabyte checkpoint hashes by default. Safetensors metadata,
  resolved path, byte size, tensor count, and dtype distribution are the fast identity
  checks; use full hashes only when provenance or corruption is in doubt.

## Validated commands

```sh
./bin/h3mlx doctor
./bin/h3mlx generate --prompt-file /path/to/prompt.txt --preset preview --name preview
./bin/h3mlx generate --prompt-file /path/to/prompt.txt --preset final10 --name final
./bin/h3mlx status
./bin/h3mlx verify /path/to/result.mp4 --width 640 --height 352 --frames 243
```

## Required validation after code changes

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
./bin/h3mlx doctor
./bin/h3mlx generate --prompt "test" --preset smoke --dry-run
python3 scripts/check_public_tree.py
```

Do not run the non-dry smoke render without explicit authorization: it still invokes a
large generative model.
