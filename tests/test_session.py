import asyncio
import tempfile
from pathlib import Path

import numpy as np

from localscribe.audio.capture import AudioCapture, AudioLevel
from localscribe.config import Config
from localscribe.events import EventType, TranscriptEvent
from localscribe.session import SessionController, build_engine
from localscribe.storage.transcript import TranscriptRecord


class FakeCapture:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def has_data(self) -> bool:
        return False

    def read(self) -> np.ndarray:
        return np.zeros(0, dtype=np.int16)

    def level(self) -> AudioLevel:
        return AudioLevel()


class FakeEngine:
    def __init__(self) -> None:
        self.queue: asyncio.Queue = asyncio.Queue()

    async def start(self, config) -> None:
        pass

    async def feed(self, chunk) -> None:
        pass

    async def flush(self) -> None:
        await self.queue.put(TranscriptEvent(type=EventType.FINAL, text="bye"))

    def events(self):
        async def gen():
            while True:
                item = await self.queue.get()
                if item is None:
                    break
                yield item

        return gen()

    async def stop(self) -> None:
        await self.queue.put(None)


def test_callback_only_buffers_and_read_computes_level():
    cap = AudioCapture(sample_rate=16000, channels=1, ring_seconds=1)
    frame = np.full(320, 4000, dtype=np.int16)
    # Callback must not compute the level meter itself.
    cap._callback(frame.reshape(-1, 1), len(frame), 0, None)
    assert cap.level().rms == 0.0
    assert cap.has_data() is True
    out = cap.read()
    assert out.size == 320
    assert cap.level().rms > 0.0
    assert cap.has_data() is False


def test_build_engine_by_name():
    cfg = Config(engine="vosk")
    assert build_engine(cfg).__class__.__name__ == "VoskEngine"
    cfg.engine = "whisper"
    assert build_engine(cfg).__class__.__name__ == "WhisperCppEngine"


def test_export_writes_txt_json_srt():
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "session.txt"
        controller = SessionController(Config(), output=Path(td) / "t.jsonl")
        controller.store.append(TranscriptRecord(type="final", text="hello", start_s=0.0, end_s=1.0))
        controller.export(out)
        assert out.read_text().strip() == "hello"
        assert out.with_suffix(".json").exists()
        assert "hello" in out.with_suffix(".srt").read_text()


def test_add_marker_persists():
    with tempfile.TemporaryDirectory() as td:
        controller = SessionController(Config(), output=Path(td) / "t.jsonl")
        controller.add_marker("note")
        records = controller.store.read_all()
        assert records[-1].type == "marker"
        assert records[-1].text == "note"


def test_stop_persists_flushed_final():
    with tempfile.TemporaryDirectory() as td:
        capture = FakeCapture()
        engine = FakeEngine()
        controller = SessionController(
            Config(engine="vosk"),
            output=Path(td) / "t.jsonl",
            capture=capture,
            engine=engine,
        )

        async def main():
            await controller.start()
            await asyncio.sleep(0)
            await controller.stop()

        asyncio.run(main())
        assert capture.started and capture.stopped
        texts = [r.text for r in controller.store.read_all()]
        assert "bye" in texts


def test_export_honors_export_dir():
    with tempfile.TemporaryDirectory() as td:
        export_dir = Path(td) / "exports"
        controller = SessionController(Config(export_dir=str(export_dir)), output=Path(td) / "t.jsonl")
        controller.store.append(TranscriptRecord(type="final", text="hi"))
        out = controller.export()
        assert out.parent == export_dir
        assert out.exists()
