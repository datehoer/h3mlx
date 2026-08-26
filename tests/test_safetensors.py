from __future__ import annotations

import json
import struct
import tempfile
import unittest
from pathlib import Path

from h3mlx.safetensors import summarize


class SafetensorsTests(unittest.TestCase):
    def test_summarizes_header_without_payload(self):
        header = {
            "weight": {"dtype": "BF16", "shape": [2, 2], "data_offsets": [0, 8]},
            "__metadata__": {"quantization": "affine 2-bit g64"},
        }
        raw = json.dumps(header).encode("utf-8")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tiny.safetensors"
            path.write_bytes(struct.pack("<Q", len(raw)) + raw + b"\0" * 8)
            report = summarize(path)
            self.assertEqual(report["tensor_count"], 1)
            self.assertEqual(report["dtypes"], {"BF16": 1})
            self.assertEqual(report["metadata"]["quantization"], "affine 2-bit g64")


if __name__ == "__main__":
    unittest.main()
