"""Disk-backed spool for completed speech segments."""

from __future__ import annotations

import json
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class SpoolEntry:
    path: Path
    start_s: float
    end_s: float
    transcribed: bool = False


class Spool:
    def __init__(self, directory: Path):
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self.manifest = self.directory / "manifest.jsonl"

    def write_wav(self, pcm: np.ndarray, sample_rate: int, start_s: float, end_s: float) -> SpoolEntry:
        idx = len(list(self.directory.glob("segment-*.wav")))
        path = self.directory / f"segment-{idx:06d}.wav"
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sample_rate)
            w.writeframes(pcm.astype(np.int16).tobytes())
        entry = SpoolEntry(path=path, start_s=start_s, end_s=end_s)
        with self.manifest.open("a") as f:
            f.write(json.dumps({"path": str(path), "start_s": start_s, "end_s": end_s, "transcribed": False}) + "\n")
        return entry

    def pending(self) -> list[SpoolEntry]:
        if not self.manifest.exists():
            return []
        out: list[SpoolEntry] = []
        for line in self.manifest.read_text().splitlines():
            if not line.strip():
                continue
            data = json.loads(line)
            if data.get("transcribed"):
                continue
            out.append(SpoolEntry(Path(data["path"]), data["start_s"], data["end_s"], False))
        return out

    def mark_transcribed(self, path: Path) -> None:
        if not self.manifest.exists():
            return
        lines = self.manifest.read_text().splitlines()
        updated = []
        for line in lines:
            if not line.strip():
                updated.append(line)
                continue
            data = json.loads(line)
            if data.get("path") == str(path):
                data["transcribed"] = True
            updated.append(json.dumps(data))
        self.manifest.write_text("\n".join(updated) + ("\n" if updated else ""))
