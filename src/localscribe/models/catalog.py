"""Versioned model catalog."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CatalogEntry:
    name: str
    engine: str
    language: str
    license: str
    url: str
    sha256: str | None
    size_bytes: int
    min_ram_bytes: int
    backend: str  # cpu
    installed: bool = False


def default_catalog() -> list[CatalogEntry]:
    # Minimal catalog; real URLs/checksums supplied by bundled catalog.
    return [
        CatalogEntry(
            name="vosk-small-en-us",
            engine="vosk",
            language="en",
            license="Apache-2.0",
            url="https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip",
            sha256=None,
            size_bytes=40_000_000,
            min_ram_bytes=512 * 1024 * 1024,
            backend="cpu",
        )
    ]


def load_catalog(path: Path) -> list[CatalogEntry]:
    if not path.exists():
        return default_catalog()
    data = json.loads(path.read_text())
    return [CatalogEntry(**e) for e in data]
