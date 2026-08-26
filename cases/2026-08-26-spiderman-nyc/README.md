# Spider-Man NYC — verified 10-second run

This case records the first verified 10.125-second render made with the local
2-bit-text / 4-bit-DiT profile.

## Result

- Output: `<OUTPUT_DIR>/h3-final-spiderman-nyc-640x352-243f-s6.mp4`
- Container health: passed
- Video: H.264, 640x352, 24 FPS
- Audio: AAC, 32 kHz stereo, non-silent, finite samples
- Duration: 10.125 seconds
- Size: 6,434,460 bytes
- SHA-256: `4041a6a70dea30cc173dcf45634e4046b6e355806285997b1b5e083861baa0ad`
- Runtime: 33.4 minutes
- Swap: zero

First, middle, and final frame samples show the subject remaining in an urban golden-hour
swinging scene with forward spatial progression. This sample-based visual check does not
prove every requested action, anatomical constraint, landmark, or sound cue; final semantic
QA still requires watching and listening to the complete clip.

The exact prompt is in `prompt.txt`, raw console telemetry in `run.log`, the environment and
model record in `manifest.json`, and stream/audio checks in `verification.json`.
