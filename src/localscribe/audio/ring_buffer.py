"""Preallocated ring buffer for audio capture callback."""

from __future__ import annotations

import threading
from typing import Any

import numpy as np


class RingBuffer:
    def __init__(self, capacity_samples: int, dtype: Any = np.int16):
        if capacity_samples <= 0:
            raise ValueError("capacity_samples must be > 0")
        self.capacity = int(capacity_samples)
        self.dtype = np.dtype(dtype)
        self._buf = np.zeros(self.capacity, dtype=self.dtype)
        self._write_pos = 0
        self._read_pos = 0
        self._count = 0
        self._lock = threading.Lock()

    def _as_samples(self, data: Any) -> np.ndarray:
        arr = np.asarray(data)
        if arr.size == 0:
            return np.zeros(0, dtype=self.dtype)
        return arr.reshape(-1).astype(self.dtype, copy=False)

    def write(self, data: Any) -> int:
        arr = self._as_samples(data)
        n = int(arr.shape[0])
        if n == 0:
            return 0
        with self._lock:
            if n >= self.capacity:
                self._buf[:] = arr[-self.capacity:]
                self._write_pos = 0
                self._read_pos = 0
                self._count = self.capacity
                return self.capacity
            first = min(n, self.capacity - self._write_pos)
            self._buf[self._write_pos : self._write_pos + first] = arr[:first]
            remainder = n - first
            if remainder:
                self._buf[:remainder] = arr[first:]
            self._write_pos = (self._write_pos + n) % self.capacity
            if self._count + n <= self.capacity:
                self._count += n
            else:
                # overwrite oldest unread samples
                self._count = self.capacity
                self._read_pos = self._write_pos
            return n

    def read_available(self) -> np.ndarray:
        with self._lock:
            if self._count == 0:
                return np.zeros(0, dtype=self.dtype)
            to_read = self._count
            if self._read_pos + to_read <= self.capacity:
                out = self._buf[self._read_pos : self._read_pos + to_read].copy()
            else:
                tail = self.capacity - self._read_pos
                out = np.concatenate(
                    (self._buf[self._read_pos :].copy(), self._buf[: to_read - tail].copy())
                )
            self._read_pos = (self._read_pos + to_read) % self.capacity
            self._count = 0
            return out

    @property
    def pending(self) -> int:
        with self._lock:
            return int(self._count)

    @property
    def capacity_samples(self) -> int:
        return self.capacity
