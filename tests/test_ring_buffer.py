import numpy as np

from localscribe.audio.ring_buffer import RingBuffer


def test_write_read_roundtrip():
    rb = RingBuffer(8)
    data = np.arange(8, dtype=np.int16)
    rb.write(data)
    out = rb.read_available()
    assert np.array_equal(out, data)
    assert rb.pending == 0


def test_wraparound():
    rb = RingBuffer(4)
    rb.write(np.array([1, 2], dtype=np.int16))
    rb.write(np.array([3, 4], dtype=np.int16))
    out = rb.read_available()
    assert list(out) == [1, 2, 3, 4]
