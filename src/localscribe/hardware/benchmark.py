"""Benchmark metrics and eligibility."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CandidateResult:
    engine: str
    model: str
    threads: int
    segment_length: int
    rtf: float
    p95_partial_latency: float
    peak_rss_mb: float
    backlog_growth: float


def compute_rtf(inference_seconds: float, audio_seconds: float) -> float:
    if audio_seconds <= 0:
        return float("inf")
    return inference_seconds / audio_seconds


def eligible(candidate: CandidateResult) -> bool:
    if candidate.rtf > 0.6:
        return False
    if candidate.backlog_growth > 0.05:
        return False
    if candidate.peak_rss_mb <= 0:
        return False
    return True
