"""Model verification helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_file(path: Path, expected: str | None) -> bool:
    if expected is None:
        return path.exists()
    return path.exists() and sha256_file(path) == expected
