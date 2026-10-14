import tempfile
from pathlib import Path

from localscribe.storage.transcript import TranscriptRecord, TranscriptStore


def test_append_and_recover():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.jsonl"
        store = TranscriptStore(p)
        store.append(TranscriptRecord(type="final", text="hello", start_s=0.0, end_s=1.0))
        records = TranscriptStore(p).read_all()
        assert len(records) == 1
        assert records[0].text == "hello"
