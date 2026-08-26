# Troubleshooting

## Doctor reports compact quantization metadata is unsupported

The MLX-Serve checkpoints store a compact string such as `affine 2-bit g64`, while the
upstream alpha runtime originally expected separate metadata keys and otherwise defaulted
to 8-bit/g32. Restore the reviewed local parser change in `src/mlx_h3/loading.py` and its
tests. Do not rename metadata or repack weights just to bypass the check.

## Process looks idle at 0% CPU

Long Metal kernels often leave the Python thread sleeping while the GPU works. Check
elapsed time, resident memory, step logs, swap, and the process state before concluding
that it is stuck. On the verified 243-frame run, each DiT step took about five minutes.

## Step 6 finished but no MP4 exists

This is normal. The runtime still has to release the DiT, decode Video VAE, decode Audio
VAE, and mux the result. The verified 243-frame Video VAE alone took 136 seconds. The
destination appears only after FFmpeg succeeds and atomically renames its temporary file.

## Memory free percentage is low

During the verified DiT phase it fell to 28–29% with zero swap. Use the telemetry as a
set: active memory, peak, cache, swap, and free percentage. Never weaken the guard. A
swap increase is a hard failure even if generation continues.

## Output exists but content is wrong

Technical verification only checks container and stream health. Compare first, middle,
and final frames; listen for requested action sounds and unintended speech/music; then
simplify timing, reduce the number of actions, or split the scene. More steps may improve
texture without restoring omitted actions.

## Reusing a path fails

The wrapper intentionally refuses to overwrite an existing output. Choose a new `--name`
or a new explicit `--output`. Keep the old artifact and its matching run record.
