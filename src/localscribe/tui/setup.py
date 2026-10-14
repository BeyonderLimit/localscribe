"""Setup wizard placeholder."""

from __future__ import annotations

from rich.console import Console


def run_setup(console: Console | None = None) -> None:
    c = console or Console()
    c.print("LocalScribe setup: download models via `localscribe models download` (not yet configured).")
