"""Textual live session screen wired to audio capture and ASR."""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, Static

from ..config import Config
from ..events import EventType, TranscriptEvent
from ..session import SessionController


def _meter(rms: float, width: int = 20) -> str:
    # rms is int16 amplitude; map to a rough 0..width bar.
    level = min(1.0, max(0.0, rms / 8000.0))
    filled = int(level * width)
    return "█" * filled + "·" * (width - filled)


class LocalScribeApp(App):
    CSS = """
    #transcript { height: 1fr; border: solid green; padding: 1; }
    #status { height: 3; }
    """
    BINDINGS = [
        Binding("space", "toggle_pause", "Pause/Resume"),
        Binding("ctrl+s", "force_save", "Save"),
        Binding("ctrl+m", "marker", "Marker"),
        Binding("ctrl+e", "export", "Export"),
        Binding("ctrl+comma", "settings", "Settings"),
        Binding("escape", "stop_session", "Stop"),
    ]

    def __init__(self, cfg: Config | None = None, output: str | None = None):
        super().__init__()
        self.cfg = cfg or Config.load()
        self.output = output
        self.controller: SessionController | None = None
        self.transcript_text = ""
        self._live = ""
        self._pending: list[TranscriptEvent] = []
        self._status = "Starting…"
        self.export_path: Path | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(self._status, id="status")
        yield Static(self.transcript_text, id="transcript")
        yield Footer()

    async def on_mount(self) -> None:
        self.controller = SessionController(self.cfg, on_event=self._on_event, output=self.output)
        try:
            await self.controller.start()
            self._status = "Recording — space to pause, ctrl+e to export, esc to stop"
        except Exception as e:
            self._status = f"Error: {e}"
        self._render()
        self.set_interval(max(0.05, self.cfg.ui_refresh_ms / 1000.0), self._drain)

    def _on_event(self, ev: TranscriptEvent) -> None:
        # Called from the controller task on the app's event loop.
        self._pending.append(ev)

    async def on_unmount(self) -> None:
        if self.controller is None:
            return
        await self.controller.stop()
        try:
            self.export_path = self.controller.export()
        except Exception:
            self.export_path = None

    def _drain(self) -> None:
        while self._pending:
            ev = self._pending.pop(0)
            if ev.type == EventType.PARTIAL:
                self._live = ev.text
            elif ev.type == EventType.FINAL:
                self.transcript_text = (self.transcript_text + "\n" + ev.text).strip()
                self._live = ""
            elif ev.type.value.endswith("warning"):
                self._status = f"! {ev.text}"
        self._render()

    def _render(self) -> None:
        level = self.controller.capture.level() if self.controller else None
        bar = _meter(level.rms) if level else "·" * 20
        paused = " [paused]" if self.controller and self.controller.paused else ""
        status = f"{self._status}{paused}\n[{bar}] rms={int(level.rms) if level else 0}"
        body = self.transcript_text
        if self._live:
            body = (body + "\n… " + self._live).strip()
        try:
            self.query_one("#status", Static).update(status)
            self.query_one("#transcript", Static).update(body)
        except Exception:
            pass

    def action_toggle_pause(self) -> None:
        if self.controller is not None:
            paused = self.controller.toggle_pause()
            self._status = "Paused" if paused else "Recording"

    async def action_force_save(self) -> None:
        if self.controller is None:
            return
        try:
            await self.controller.flush()
            self._status = "Saved final utterance (JSONL autosaved)"
        except Exception as e:
            self._status = f"Save failed: {e}"

    def action_marker(self) -> None:
        if self.controller is not None:
            self.controller.add_marker()
            self._status = "Marker inserted"

    def action_export(self) -> None:
        if self.controller is None:
            return
        try:
            out = self.controller.export()
            self._status = f"Exported to {out}"
        except Exception as e:
            self._status = f"Export failed: {e}"

    def action_settings(self) -> None:
        self._status = f"Config: {self.cfg.path()}"

    def action_stop_session(self) -> None:
        self.exit()
