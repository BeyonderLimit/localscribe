"""Typed events exchanged between audio, ASR, and TUI layers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class EventType(str, Enum):
    PARTIAL = "partial"
    FINAL = "final"
    ENGINE_WARNING = "engine_warning"
    BACKLOG_WARNING = "backlog_warning"
    RESOURCE_RECOMMENDATION = "resource_recommendation"
    STATUS = "status"


@dataclass
class TranscriptEvent:
    type: EventType
    text: str = ""
    confidence: float | None = None
    start_s: float | None = None
    end_s: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


def now_iso() -> str:
    return datetime.now(UTC).isoformat()
