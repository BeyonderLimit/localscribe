"""Recommendation logic (CPU-only)."""

from __future__ import annotations

from .benchmark import CandidateResult
from .probe import HardwareProfile


def recommend(profile: HardwareProfile, candidates: list[CandidateResult] | None = None) -> dict:
    candidates = candidates or []
    eligible = [c for c in candidates if c.rtf <= 0.6 and c.backlog_growth <= 0.05]
    ram_gb = profile.ram_bytes / (1024**3) if profile.ram_bytes else 0
    # Prefer Vosk when eligible.
    vosk_candidates = [c for c in eligible if c.engine == "vosk"]
    if vosk_candidates:
        best = min(vosk_candidates, key=lambda c: (c.rtf, c.p95_partial_latency))
        return {"engine": best.engine, "model": best.model, "threads": best.threads, "reason": "Vosk meets RTF target"}
    whisper_candidates = [c for c in eligible if c.engine == "whisper"]
    if whisper_candidates:
        best = min(whisper_candidates, key=lambda c: (c.rtf, c.p95_partial_latency))
        return {"engine": best.engine, "model": best.model, "threads": best.threads, "reason": "Whisper meets RTF target"}
    # Fallbacks by RAM.
    if ram_gb < 8:
        return {"engine": "vosk", "model": "vosk-small", "threads": 2, "reason": "low RAM fallback"}
    if ram_gb < 16:
        return {"engine": "vosk", "model": "vosk-small", "threads": 2, "reason": "default; benchmark whisper tiny/base optionally"}
    if ram_gb < 32:
        return {"engine": "vosk", "model": "vosk-medium", "threads": 4, "reason": "benchmark vs whisper base/small"}
    return {"engine": "vosk", "model": "vosk-medium", "threads": 4, "reason": "benchmark whisper small/medium"}
