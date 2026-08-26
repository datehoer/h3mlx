from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from h3mlx.config import load_config
from h3mlx.runner import build_command, run_generation


class RunnerTests(unittest.TestCase):
    def _config(self, root: Path):
        path = root / "local.toml"
        path.write_text(
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
        return load_config(path)

    def test_command_contains_all_explicit_model_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            config = self._config(Path(directory))
            command = build_command(config, "prompt", config.preset(), Path("out.mp4"))
            self.assertEqual(command[1], "prompt")
            self.assertIn("--turbo-lora", command)
            self.assertIn("--budget", command)

    def test_dry_run_writes_nothing_and_hides_prompt_in_manifest_command(self):
        with tempfile.TemporaryDirectory() as directory:
            config = self._config(Path(directory))
            manifest = run_generation(
                config, prompt="private prompt", name="test", dry_run=True
            )
            self.assertEqual(manifest["status"], "dry_run")
            self.assertNotIn("private prompt", manifest["command"])
            self.assertFalse(config.run_dir.exists())


if __name__ == "__main__":
    unittest.main()
