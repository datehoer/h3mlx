#!/usr/bin/env python3
"""Fail when publishable files contain local state, credentials, or heavy artifacts."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SELF = Path(__file__).resolve()
MAX_FILE_BYTES = 2 * 1024 * 1024
FORBIDDEN_SUFFIXES = {
    ".safetensors",
    ".ckpt",
    ".pt",
    ".pth",
    ".gguf",
    ".mp4",
    ".mov",
    ".mkv",
    ".wav",
}


def candidates() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    return [ROOT / item.decode() for item in result.stdout.split(b"\0") if item]


def main() -> int:
    problems: list[str] = []
    local_path = re.compile(r"(?:/Volumes/|/Users/|(?<![A-Za-z])[A-Za-z]:[\\/])")
    credential = re.compile(
        r"(?:BEGIN [A-Z ]*PRIVATE KEY|github_pat_[A-Za-z0-9_]+|ghp_[A-Za-z0-9]+|"
        r"sk-[A-Za-z0-9_-]{20,}|Authorization:\s*Bearer\s+\S+|"
        r"(?:api[_-]?key|access[_-]?token|password|secret)\s*[:=]\s*['\"]?\S+)",
        re.IGNORECASE,
    )
    for path in candidates():
        relative = path.relative_to(ROOT)
        if path.is_symlink():
            problems.append(f"symlink is not publishable: {relative}")
            continue
        if not path.is_file():
            continue
        size = path.stat().st_size
        if size > MAX_FILE_BYTES:
            problems.append(f"file exceeds 2 MiB: {relative} ({size} bytes)")
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            problems.append(f"model/media artifact is not publishable: {relative}")
        if path.resolve() == SELF:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            problems.append(f"unexpected binary file: {relative}")
            continue
        if local_path.search(text):
            problems.append(f"local absolute path found: {relative}")
        if credential.search(text):
            problems.append(f"possible credential found: {relative}")
    if problems:
        print("public-tree check failed:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print(f"public-tree check passed: {len(candidates())} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
