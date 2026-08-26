---
name: h3mlx
description: Run, diagnose, record, and verify local MiniMax H3 text-to-video-and-audio generation on Apple Silicon through an existing pure-MLX mlx-h3 runtime and local 2-bit text-encoder / 4-bit DiT checkpoint set.
---

# H3 MLX

Use this skill when the user wants to generate MiniMax H3 video with native stereo
audio on this Apple Silicon machine, reproduce a recorded run, inspect the local MLX
environment, or understand its models and performance.

## Scope and route

The verified route is:

```text
prompt -> tokenizer -> 2-bit Qwen3-VL text encoder
       -> 4-bit MiniMax-H3 FL2VA DiT + BF16 Turbo LoRA
       -> dense FP16 Video VAE -> dense FP32 Audio VAE
       -> FFmpeg H.264/AAC MP4
```

It uses the external checkout and paths in `h3mlx.local.toml`. It is not the Windows
ComfyUI route from h3lite and it is not the separate `mmh3turbo` package.

## Workflow

1. Read `AGENTS.md`, then `references/verified-profile.md`.
2. Run `./bin/h3mlx doctor`. Stop if it reports `blocked`.
3. Clarify the requested duration, canvas, shot structure, audio, and output name.
4. Start with `smoke` for pipeline diagnosis or `preview` for content iteration.
5. Use `final10` only after a preview succeeds or when the user explicitly accepts the
   observed roughly 33-minute runtime on the verified M1 Max profile.
6. Put long prompts in an untracked UTF-8 file and invoke `generate --prompt-file`.
7. Let the wrapper create the run manifest and tee the complete runtime log.
8. Require `verification.json` to report `ok: true`, then manually inspect first,
   middle, and final frames and listen to the soundtrack.

## Prompt rules

- Establish subject, environment, light, camera position, and opening state first.
- Write actions and sound events in playback order.
- For one continuous shot, avoid describing incompatible cuts or simultaneous camera
  positions.
- Treat “no dialogue” as preserving ambient and action sound; request silence only when
  no audio is wanted.
- H3 has no separate negative-prompt/CFG pass in this runtime. Negative phrases are
  ordinary text constraints, not guaranteed exclusions.
- A long list of actions in ten seconds can exceed temporal adherence even when the
  prompt is under the 4096-token limit. Prefer a preview and split genuinely distinct
  shots into separate generations.

## Presets

| Preset | Canvas | Frames / duration | Steps | Use |
| --- | ---: | ---: | ---: | --- |
| `smoke` | 512x288 | 22 / 0.917s | 4 | Wiring and output check |
| `preview` | 640x352 | 124 / 5.167s | 4 | Default content iteration |
| `final10` | 640x352 | 243 / 10.125s | 6 | Verified long render |

All use a 20 GiB MLX budget. Dimensions remain multiples of 32 and frames follow
`17n+5`.

## Status reporting

During sampling, report completed steps, observed seconds per step, active/peak/cache
memory, swap, and free-memory percentage. After sampling, state that Video VAE, Audio
VAE, and muxing remain. On completion, report output path, exact duration, codecs,
audio properties, elapsed time, prompt tokens, sequence length, and verification status.

## Safety

- Never delete or replace weights automatically.
- Never overwrite an output automatically.
- Never weaken the memory/swap guard.
- Never claim completion before the wrapper writes a verified MP4.
- Preserve the MiniMax H3 and Turbo LoRA license notices from their respective model
  packages. The operational code repository does not grant rights to the weights.
