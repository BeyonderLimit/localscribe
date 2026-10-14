"""Voice activity detection (energy fallback; WebRTC if available)."""

from __future__ import annotations

import numpy as np


class VAD:
    def is_speech(self, frame: np.ndarray) -> bool:
        raise NotImplementedError


class EnergyVAD(VAD):
    def __init__(self, threshold: float = 500.0):
        self.threshold = threshold

    def is_speech(self, frame: np.ndarray) -> bool:
        arr = np.asarray(frame).reshape(-1)
        if arr.size == 0:
            return False
        rms = float(np.sqrt(np.mean(arr.astype(np.float64) ** 2)))
        return rms >= self.threshold


def _webrtc_available() -> bool:
    try:
        import webrtcvad  # noqa: F401

        return True
    except Exception:
        return False


def create_vad(mode: str = "energy", aggressiveness: int = 2) -> VAD:
    if mode == "webrtc" and _webrtc_available():
        import webrtcvad

        class WebRTCVAD(VAD):
            def __init__(self):
                self._v = webrtcvad.Vad(aggressiveness)

            def is_speech(self, frame: np.ndarray) -> bool:
                # Expects 16-bit PCM, 10/20/30 ms frame.
                pcm = np.asarray(frame).astype(np.int16).tobytes()
                try:
                    return bool(self._v.is_speech(pcm, 16000))
                except Exception:
                    return False

        return WebRTCVAD()
    return EnergyVAD()
