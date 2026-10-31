"""Render spoken prompts with Home Assistant text-to-speech."""

from __future__ import annotations

from array import array
import asyncio
from collections import OrderedDict
import io
import sys
import wave

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import LOGGER
from .rtp.g711 import SAMPLE_RATE, Codec

TTS_TIMEOUT = 20
_CACHE_SIZE = 64
# Ask the TTS manager to convert to 8 kHz mono WAV (it uses ffmpeg for that).
_TTS_OPTIONS = {
    "preferred_format": "wav",
    "preferred_sample_rate": SAMPLE_RATE,
    "preferred_sample_channels": 1,
    "preferred_sample_bytes": 2,
}


def wav_to_g711(data: bytes, codec: Codec) -> bytes:
    """Convert a WAV file to 8 kHz mono G.711, resampling if necessary."""
    with wave.open(io.BytesIO(data), "rb") as wav:
        channels = wav.getnchannels()
        width = wav.getsampwidth()
        rate = wav.getframerate()
        frames = wav.readframes(wav.getnframes())
    if width != 2:
        raise ValueError(f"Unsupported sample width {width}")
    samples = array("h")
    samples.frombytes(frames[: len(frames) - len(frames) % 2])
    if sys.byteorder == "big":
        samples.byteswap()
    if channels > 1:
        samples = array(
            "h",
            (
                sum(samples[index : index + channels]) // channels
                for index in range(0, len(samples) - channels + 1, channels)
            ),
        )
    if rate != SAMPLE_RATE:
        samples = _resample(samples, rate, SAMPLE_RATE)
    if sys.byteorder == "big":
        samples.byteswap()
    return codec.encode(samples.tobytes())


def _resample(samples: array[int], source_rate: int, target_rate: int) -> array[int]:
    """Linear interpolation resampler (only used when TTS ignores our format)."""
    if not samples:
        return samples
    count = int(len(samples) * target_rate / source_rate)
    step = source_rate / target_rate
    last = len(samples) - 1
    result = array("h")
    for index in range(count):
        position = index * step
        left = int(position)
        right = min(left + 1, last)
        fraction = position - left
        result.append(int(samples[left] * (1 - fraction) + samples[right] * fraction))
    return result


class SpeechRenderer:
    """Turn text into G.711 audio using a TTS engine, with an in-memory cache."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the renderer."""
        self._hass = hass
        self._cache: OrderedDict[tuple[str, str | None, str, Codec], bytes] = OrderedDict()

    def resolve_engine(self, engine: str | None) -> str | None:
        """Return the TTS engine to use, or None when TTS is unavailable."""
        if "tts" not in self._hass.config.components:
            return None
        from homeassistant.components import tts  # noqa: PLC0415

        return tts.async_resolve_engine(self._hass, engine)

    async def render(
        self, text: str, *, engine: str | None, language: str | None, codec: Codec
    ) -> bytes | None:
        """Render text, returning None when no TTS engine can be used."""
        if (resolved := self.resolve_engine(engine)) is None:
            return None
        key = (resolved, language, text, codec)
        if (cached := self._cache.get(key)) is not None:
            self._cache.move_to_end(key)
            return cached
        try:
            async with asyncio.timeout(TTS_TIMEOUT):
                audio = await self._synthesize(resolved, language, text, codec)
        except (HomeAssistantError, TimeoutError, ValueError, EOFError, wave.Error) as err:
            LOGGER.warning("Text-to-speech with %s failed: %s", resolved, err)
            return None
        self._cache[key] = audio
        if len(self._cache) > _CACHE_SIZE:
            self._cache.popitem(last=False)
        return audio

    async def _synthesize(
        self, engine: str, language: str | None, text: str, codec: Codec
    ) -> bytes:
        # Imported lazily: the tts component is an optional (after) dependency.
        from homeassistant.components import tts  # noqa: PLC0415

        try:
            stream = tts.async_create_stream(
                self._hass, engine, language=language, options=dict(_TTS_OPTIONS)
            )
        except HomeAssistantError:
            # The engine may not support the requested language; use its default.
            stream = tts.async_create_stream(self._hass, engine, options=dict(_TTS_OPTIONS))
        stream.async_set_message(text)
        data = b"".join([chunk async for chunk in stream.async_stream_result()])
        return await self._hass.async_add_executor_job(wav_to_g711, data, codec)
