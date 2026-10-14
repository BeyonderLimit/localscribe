"""Export helpers for TXT/SRT/JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def to_txt(records: list[Any], out: Path) -> None:
    texts: list[str] = [str(getattr(r, "text", r.get("text") if isinstance(r, dict) else "")) for r in records]
    out.write_text("\n".join(texts) + "\n", encoding="utf-8")


def to_json(records: list[Any], out: Path) -> None:
    payload = [r.__dict__ if hasattr(r, "__dict__") else r for r in records]
    out.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _srt_time(seconds: float) -> str:
    if seconds is None:
        seconds = 0.0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def to_srt(records: list[Any], out: Path) -> None:
    lines: list[str] = []
    idx = 1
    for r in records:
        text = getattr(r, "text", r.get("text") if isinstance(r, dict) else "")
        start = getattr(r, "start_s", None)
        if start is None and isinstance(r, dict):
            start = r.get("start_s")
        end = getattr(r, "end_s", None)
        if end is None and isinstance(r, dict):
            end = r.get("end_s")
        if start is None:
            start = 0.0
        if end is None:
            end = start + 2.0
        lines.append(str(idx))
        lines.append(f"{_srt_time(float(start))} --> {_srt_time(float(end))}")
        lines.append(str(text))
        lines.append("")
        idx += 1
    out.write_text("\n".join(lines), encoding="utf-8")
