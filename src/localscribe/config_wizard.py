"""Interactive configuration wizard."""

from __future__ import annotations

from .config import Config


def _ask(prompt: str, default: str) -> str:
    try:
        raw = input(f"{prompt} [{default}]: ").strip()
    except EOFError:
        return default
    return raw if raw else default


def _ask_int(prompt: str, default: int) -> int:
    while True:
        raw = _ask(prompt, str(default))
        try:
            return int(raw)
        except ValueError:
            print("Please enter an integer.")


def _ask_bool(prompt: str, default: bool) -> bool:
    raw = _ask(prompt, "y" if default else "n").lower()
    if raw in {"y", "yes", "true", "1"}:
        return True
    if raw in {"n", "no", "false", "0"}:
        return False
    return default


def run_wizard(cfg: Config | None = None) -> Config:
    cfg = cfg or Config.load()
    print("LocalScribe configuration wizard. Press Enter to keep the current value.")
    engine = _ask("Speech engine (vosk/whisper)", cfg.engine)
    while engine not in {"vosk", "whisper"}:
        print("Invalid engine; choose vosk or whisper.")
        engine = _ask("Speech engine (vosk/whisper)", cfg.engine)
    cfg.engine = engine

    model = _ask("Vosk/Whisper model path (blank for auto)", cfg.model or "")
    cfg.model = model or None

    cfg.whisper_threads = _ask_int("Inference threads", cfg.whisper_threads)
    cfg.frame_ms = _ask_int("VAD frame length ms (20-30)", cfg.frame_ms)
    cfg.pre_roll_ms = _ask_int("Pre-roll ms", cfg.pre_roll_ms)
    cfg.post_roll_ms = _ask_int("Post-roll ms", cfg.post_roll_ms)
    cfg.max_segment_s = _ask_int("Max segment seconds", cfg.max_segment_s)
    cfg.ring_buffer_seconds = _ask_int("Ring buffer seconds", cfg.ring_buffer_seconds)
    cfg.ui_refresh_ms = _ask_int("UI refresh ms", cfg.ui_refresh_ms)
    cfg.retention = _ask("Audio retention (keep/hours:N/delete)", cfg.retention)
    cfg.export_dir = _ask("Export directory (blank for cwd)", cfg.export_dir or "") or None
    cfg.verbose = _ask_bool("Verbose logging", cfg.verbose)

    cfg.save()
    print(f"Saved configuration to {cfg.path()}")
    return cfg
