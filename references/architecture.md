# Architecture

`h3mlx` is an orchestration layer, not a model implementation. It executes the external
`mlx-h3` console script as a subprocess and records everything around that boundary.

```text
h3mlx.local.toml
        |
        v
doctor ----> runtime/model/tool compatibility report
        |
        v
generate --> prompt.txt + manifest.json
        |
        v
external mlx-h3 process
        |
        +--> tokenizer
        +--> text encoder -------- release
        +--> joint audio/video DiT release
        +--> Video VAE ----------- release
        +--> Audio VAE ----------- release
        +--> FFmpeg mux
        |
        v
verify ----> ffprobe + checksum --> verification.json
```

## External runtime contract

The console entry point is `mlx_h3.cli:main`. For a text-only request it:

1. Encodes the prompt with the local Qwen byte-level BPE tokenizer.
2. Runs the text-only portion of the Qwen3-VL encoder and releases it.
3. Creates deterministic video and audio noise from the seed.
4. Packs text, audio, and video into one DiT sequence.
5. Runs one joint DiT evaluation per sampling step. With Turbo LoRA this uses
   first-order Euler while video and audio advance on separate sigma grids.
6. Releases the DiT, decodes RGB frames, releases Video VAE, decodes stereo audio,
   and releases Audio VAE.
7. Uses FFmpeg to produce H.264 CRF 18/yuv420p plus 192 kbps AAC with `faststart`.

There is no classifier-free-guidance branch or separate negative prompt. The joint DiT
allows sound and visible events to condition one another within the same sequence.

## Shape rules

- Canvas axes are multiples of 32.
- Canvas area may not exceed `768 * 1344` pixels.
- Frames are rounded upward until `frames % 17 == 5`.
- Output frame rate is 24 FPS.
- Audio is 32 kHz stereo.
- The released local limit is 15 seconds.

For the verified 243-frame case:

```text
duration       243 / 24 = 10.125 seconds
video latent   [1, 24, 72, 22, 40]
audio latent   [1, 32, 2, 405]
prompt rows    194
audio rows     810
video rows     15,840
total sequence 16,844
```

## Why this fits in 32 GB

The required files total more than physical memory, but they are not simultaneously
resident. The verified DiT phase used 11.2 GiB active MLX memory and peaked at 14.5 GiB.
The configured 20 GiB guard is below this machine's approximately 21.3 GiB recommended
MLX working-set limit. The guard fails on budget overflow, process-attributed swap growth,
or dangerous compressor growth rather than silently paging through inference. macOS
system swap counters cannot identify the owner of an evicted page, so `vmmap -summary`
tracks the `mlx-h3` PID separately. System swap growth attributed outside that PID
remains visible as telemetry but is not by itself a generation failure. Process swap is
measured cumulatively from the run baseline, but `vmmap` also counts compressed/evicted
private pages that have not reached disk. The guard treats paging as model-attributed only
when both the process counter and system disk-swap usage grow by more than 64 MiB. Growth
in either counter alone is telemetry rather than a hard failure.
