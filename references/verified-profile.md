# Verified M1 Max profile

## Host

| Field | Verified value |
| --- | --- |
| Machine | Mac Studio `Mac13,1` |
| SoC | Apple M1 Max |
| CPU | 10 cores |
| GPU | 24 cores, Metal 3 |
| Unified memory | 32 GB |
| OS | macOS 15.7.2, build 24G325 |
| Python | 3.13.12 |
| MLX | 0.32.0 |
| mlx-h3 | 0.0.1a3, Git `762b280` |
| FFmpeg | 9.0.1 |

The external runtime checkout had two intentional uncommitted changes during the
verified run: `src/mlx_h3/loading.py` and `tests/test_loading.py`. They add and test
parsing of compact MLX-Serve metadata such as `affine 2-bit g64`. Preserve or upstream
that change before expecting this model pack to load.

The current operational profile additionally carries a reviewed `vmmap` process-swap
attribution change in `src/mlx_h3/memory.py` and `tests/test_memory.py`. It was added
after the recorded baseline run to correlate system disk-swap movement with pages
compressed or evicted from the `mlx-h3` process. Because `vmmap` process totals are not
disk-swap proof alone, the guard requires material growth in both counters. This changes
the guard decision and telemetry, not model numerics or the staged-residency order.

## Models

| Role | Precision | Bytes | Notes |
| --- | --- | ---: | --- |
| Tokenizer | unchanged JSON | 7,032,403 | MiniMax H3 FL2VA processor |
| Qwen3-VL text encoder | affine 2-bit, g64 | 9,595,816,442 | 439 packed modules; dense embeddings/norms retained |
| MiniMax-H3 FL2VA DiT | affine 4-bit, g64 | 18,698,813,290 | 260 packed modules; dense FP32/BF16 islands retained |
| Video VAE | dense FP16 | 5,207,808,496 | 562 tensors |
| Audio VAE | dense FP32 | 605,254,808 | 917 tensors; BigVGAN decoder |
| Turbo LoRA | BF16 | 779,849,816 | 518 tensors; community ckpt850 EMA |

Only the text encoder is physically stored in the `H3-2bitTE-4bitDiT` directory. The
other assets are symlinks into `MiniMax-H3-FL2VA-MLX-Serve-4bit`.

## Preset guidance

Use `preview` by default. It halves the temporal workload relative to `final10` and
keeps iterations easier to inspect. Use `final10` after the content is plausible.

The installed LoRA resolves to the older community
`minimax_h3_turbo_4step_ema_ckpt850` adapter. The runtime permits 4–8 steps and the
recorded 6-step run completed successfully. The current `mlx-h3` documentation prefers
the newer v4-step600 adapter for general 6–8 step work and describes ckpt850 as a
fast/heavy-motion fallback, especially at four steps. Treat a LoRA replacement as a new
profile requiring a same-prompt/seed A/B check; never silently change it.

## Observed 10-second performance

| Phase | Load | Run | Release |
| --- | ---: | ---: | ---: |
| Text encoder | 10.3 s | 3.5 s | 0.1 s |
| DiT | 22.3 s | 1,822.6 s | 0.1 s |
| Video VAE | 5.5 s | 136.0 s | 0.1 s |
| Audio VAE | 0.3 s | 3.5 s | 0.1 s |

Total reported wall time was 33.4 minutes. The first DiT step took 340.6 seconds due to
cold execution; steps 2–6 took 301.9–304.9 seconds. DiT memory stayed at 11.2 GiB active,
14.5 GiB peak, 7.2 GiB cache, with zero swap.
