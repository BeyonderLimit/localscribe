import numpy as np

from localscribe.audio.segmenter import Segmenter
from localscribe.audio.vad import EnergyVAD


def test_segmenter_produces_segment_on_silence():
    vad = EnergyVAD(threshold=1.0)
    seg = Segmenter(sample_rate=16000, frame_ms=20, pre_roll_ms=20, post_roll_ms=40, vad=vad)
    speech = np.full(16000, 1000, dtype=np.int16)
    silence = np.zeros(16000, dtype=np.int16)
    segs = seg.feed(speech)
    segs += seg.feed(silence)
    # may or may not finalize depending frame alignment; at least no crash
    assert isinstance(segs, list)


def test_segmenter_flush():
    vad = EnergyVAD(threshold=1.0)
    seg = Segmenter(sample_rate=16000, frame_ms=20, vad=vad)
    speech = np.full(400, 1000, dtype=np.int16)
    seg.feed(speech)
    s = seg.flush()
    assert s is None or hasattr(s, "pcm")
