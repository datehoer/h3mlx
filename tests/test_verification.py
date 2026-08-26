from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from h3mlx.verification import verify


class VerificationTests(unittest.TestCase):
    def test_expected_streams_pass(self):
        payload = {
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 640,
                    "height": 352,
                    "r_frame_rate": "24/1",
                    "nb_frames": "243",
                },
                {
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "sample_rate": "32000",
                    "channels": 2,
                },
            ],
            "format": {"duration": "10.125"},
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.mp4"
            path.write_bytes(b"media")
            with patch("h3mlx.verification.probe", return_value=payload):
                report = verify(path, width=640, height=352, frames=243, checksum=False)
        self.assertTrue(report["ok"])


if __name__ == "__main__":
    unittest.main()
