"""Textual live session screen."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, Static


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

    def __init__(self):
        super().__init__()
        self.transcript_text = ""
        self.status_text = "Ready"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(self.status_text, id="status")
        yield Static(self.transcript_text, id="transcript")
        yield Footer()

    def set_status(self, text: str) -> None:
        self.status_text = text
        try:
            self.query_one("#status", Static).update(text)
        except Exception:
            pass

    def append_transcript(self, text: str) -> None:
        self.transcript_text = (self.transcript_text + "\n" + text).strip()
        try:
            self.query_one("#transcript", Static).update(self.transcript_text)
        except Exception:
            pass

    def action_toggle_pause(self) -> None:
        self.set_status("Paused/Resumed")

    def action_force_save(self) -> None:
        self.set_status("Saved")

    def action_marker(self) -> None:
        self.set_status("Marker inserted")

    def action_export(self) -> None:
        self.set_status("Export requested")

    def action_settings(self) -> None:
        self.set_status("Settings")

    def action_stop_session(self) -> None:
        self.exit()
