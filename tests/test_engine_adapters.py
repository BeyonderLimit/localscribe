import asyncio

from localscribe.engines.base import AudioChunk, EngineConfig
from localscribe.engines.vosk_engine import VoskEngine
from localscribe.engines.whisper_cpp import WhisperCppEngine


def test_vosk_requires_model():
    async def main():
        e = VoskEngine()
        try:
            await e.start(EngineConfig(model_path=None))
            return False
        except Exception:
            return True

    assert asyncio.run(main()) is True


def test_whisper_requires_binary_or_model():
    async def main():
        e = WhisperCppEngine()
        try:
            await e.start(EngineConfig(model_path="/nope"))
            return False
        except Exception:
            return True

    assert asyncio.run(main()) is True


def test_audio_chunk_defaults():
    c = AudioChunk(pcm=b"\x00\x00")
    assert c.sample_rate == 16000
