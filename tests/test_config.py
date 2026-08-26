from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from h3mlx.config import load_config


class ConfigTests(unittest.TestCase):
    def test_loads_relative_paths_and_presets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_file = root / "local.toml"
            config_file.write_text(
                """
[runtime]
repo = "runtime"
executable = "runtime/.venv/bin/mlx-h3"
python = "runtime/.venv/bin/python"
[models]
tokenizer = "models/tokenizer.json"
text_encoder = "models/text.safetensors"
dit = "models/dit.safetensors"
video_vae = "models/video.safetensors"
audio_vae = "models/audio.safetensors"
turbo_lora = "models/lora.safetensors"
[storage]
output_dir = "outputs"
run_dir = "runs"
[defaults]
preset = "preview"
[presets.preview]
width = 640
height = 352
frames = 124
steps = 4
seed = 42
budget = 20
""",
                encoding="utf-8",
            )
            config = load_config(config_file)
            self.assertEqual(config.runtime.repo, (root / "runtime").resolve())
            self.assertEqual(config.output_dir, (root / "outputs").resolve())
            self.assertEqual(config.preset().frames, 124)

    def test_rejects_unaligned_frame_preset(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_file = root / "local.toml"
            config_file.write_text(
                """
[runtime]
repo = "runtime"
executable = "runtime/mlx-h3"
python = "runtime/python"
[models]
tokenizer = "m/tokenizer.json"
text_encoder = "m/text.safetensors"
dit = "m/dit.safetensors"
video_vae = "m/video.safetensors"
audio_vae = "m/audio.safetensors"
turbo_lora = "m/lora.safetensors"
[storage]
output_dir = "outputs"
run_dir = "runs"
[defaults]
preset = "bad"
[presets.bad]
width = 640
height = 352
frames = 120
steps = 4
seed = 1
budget = 20
""",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "frames % 17"):
                load_config(config_file)


if __name__ == "__main__":
    unittest.main()
