"""Read safetensors structure without loading tensor payloads."""

from __future__ import annotations

import json
import os
import struct
from pathlib import Path
from typing import Any


def read_header(path: str | Path) -> tuple[dict[str, Any], dict[str, str]]:
    source = Path(path)
    with source.open("rb") as handle:
        raw_size = handle.read(8)
        if len(raw_size) != 8:
            raise ValueError(f"invalid safetensors header: {source}")
        size = struct.unpack("<Q", raw_size)[0]
        header = json.loads(handle.read(size))
    metadata = header.pop("__metadata__", {})
    if not isinstance(metadata, dict):
        raise ValueError(f"invalid safetensors metadata: {source}")
    return header, metadata


def summarize(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    resolved = source.resolve()
    tensors, metadata = read_header(source)
    dtypes: dict[str, int] = {}
    for tensor in tensors.values():
        dtype = str(tensor.get("dtype", "unknown"))
        dtypes[dtype] = dtypes.get(dtype, 0) + 1
    return {
        "path": str(source),
        "resolved_path": str(resolved),
        "is_symlink": source.is_symlink(),
        "size_bytes": os.path.getsize(resolved),
        "tensor_count": len(tensors),
        "dtypes": dtypes,
        "metadata": metadata,
    }
