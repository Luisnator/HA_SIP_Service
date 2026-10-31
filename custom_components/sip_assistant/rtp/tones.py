"""Generated signalling tones (used when no text-to-speech is available)."""

from __future__ import annotations

from array import array
from enum import Enum
from functools import cache
import math
import sys

from .g711 import SAMPLE_RATE, Codec

_AMPLITUDE = 0.3 * 32767


class Tone(Enum):
    """Tone sequences as (frequency in Hz or 0 for a pause, duration in ms)."""

    BEEP = ((1000, 150),)
    CONFIRM = ((880, 120), (0, 60), (1320, 180))
    ERROR = ((420, 250), (0, 80), (330, 400))
    PROMPT = ((660, 100), (0, 80), (660, 100))
    GOODBYE = ((660, 150), (0, 50), (440, 300))


def _pcm(frequency: int, duration_ms: int) -> array[int]:
    count = SAMPLE_RATE * duration_ms // 1000
    if frequency == 0:
        return array("h", bytes(count * 2))
    ramp = min(80, count // 4)  # short fade in/out avoids clicks
    samples = array("h")
    for index in range(count):
        envelope = min(1.0, index / ramp, (count - index) / ramp) if ramp else 1.0
        samples.append(
            int(_AMPLITUDE * envelope * math.sin(2 * math.pi * frequency * index / SAMPLE_RATE))
        )
    return samples


@cache
def render_tone(tone: Tone, codec: Codec) -> bytes:
    """Render a tone sequence in the given codec."""
    pcm = array("h")
    for frequency, duration in tone.value:
        pcm.extend(_pcm(frequency, duration))
    if sys.byteorder == "big":
        pcm.byteswap()
    return codec.encode(pcm.tobytes())


def prewarm() -> None:
    """Build codec tables and render all tones (run in an executor)."""
    for codec in Codec:
        for tone in Tone:
            render_tone(tone, codec)
