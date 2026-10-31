"""G.711 (mu-law / A-law) codecs implemented without native dependencies."""

from __future__ import annotations

from array import array
from enum import Enum
from functools import cache
import sys

SAMPLE_RATE = 8000
FRAME_MS = 20
SAMPLES_PER_FRAME = SAMPLE_RATE * FRAME_MS // 1000  # 160 bytes per G.711 frame

_ULAW_BIAS = 0x84
_ULAW_CLIP = 32635
_ALAW_SEGMENT_END = (0x1F, 0x3F, 0x7F, 0xFF, 0x1FF, 0x3FF, 0x7FF, 0xFFF)


def linear_to_ulaw(sample: int) -> int:
    """Encode one signed 16-bit sample as mu-law."""
    sign = 0x80 if sample < 0 else 0
    if sign:
        sample = -sample
    sample = min(sample, _ULAW_CLIP) + _ULAW_BIAS
    exponent = max((sample >> 7).bit_length() - 1, 0)
    mantissa = (sample >> (exponent + 3)) & 0x0F
    return ~(sign | (exponent << 4) | mantissa) & 0xFF


def ulaw_to_linear(value: int) -> int:
    """Decode one mu-law byte to a signed 16-bit sample."""
    value = ~value & 0xFF
    exponent = (value >> 4) & 0x07
    sample = ((((value & 0x0F) << 3) + _ULAW_BIAS) << exponent) - _ULAW_BIAS
    return -sample if value & 0x80 else sample


def linear_to_alaw(sample: int) -> int:
    """Encode one signed 16-bit sample as A-law."""
    pcm = sample >> 3
    if pcm >= 0:
        mask = 0xD5
    else:
        mask = 0x55
        pcm = -pcm - 1
    segment = next((index for index, end in enumerate(_ALAW_SEGMENT_END) if pcm <= end), None)
    if segment is None:
        return 0x7F ^ mask
    value = segment << 4
    value |= (pcm >> 1 if segment < 2 else pcm >> segment) & 0x0F
    return value ^ mask


def alaw_to_linear(value: int) -> int:
    """Decode one A-law byte to a signed 16-bit sample."""
    value ^= 0x55
    sample = (value & 0x0F) << 4
    segment = (value & 0x70) >> 4
    if segment == 0:
        sample += 8
    elif segment == 1:
        sample += 0x108
    else:
        sample = (sample + 0x108) << (segment - 1)
    return sample if value & 0x80 else -sample


@cache
def _encode_table(codec: Codec) -> bytes:
    """Map every unsigned 16-bit index (two's complement sample) to a byte."""
    encode = linear_to_ulaw if codec is Codec.PCMU else linear_to_alaw
    return bytes(encode(index - 0x10000 if index & 0x8000 else index) for index in range(0x10000))


@cache
def _decode_table(codec: Codec) -> tuple[int, ...]:
    decode = ulaw_to_linear if codec is Codec.PCMU else alaw_to_linear
    return tuple(decode(value) for value in range(256))


class Codec(Enum):
    """G.711 variants supported for calls."""

    PCMU = (0, "PCMU", 0xFF, "audio/pcmu")
    PCMA = (8, "PCMA", 0xD5, "audio/pcma")

    def __init__(
        self, payload_type: int, encoding_name: str, silence: int, openai_format: str
    ) -> None:
        """Initialize the codec."""
        self.payload_type = payload_type
        self.encoding_name = encoding_name
        self.silence_byte = silence
        self.openai_format = openai_format

    @classmethod
    def from_encoding_name(cls, name: str) -> Codec | None:
        """Return the codec for an rtpmap encoding name."""
        name = name.upper()
        return next((codec for codec in cls if codec.encoding_name == name), None)

    @classmethod
    def from_static_payload_type(cls, payload_type: int) -> Codec | None:
        """Return the codec for a static RTP payload type."""
        return next((codec for codec in cls if codec.payload_type == payload_type), None)

    def silence(self, samples: int = SAMPLES_PER_FRAME) -> bytes:
        """Return encoded silence."""
        return bytes([self.silence_byte]) * samples

    def encode(self, pcm: bytes) -> bytes:
        """Encode signed 16-bit little endian mono PCM."""
        samples = array("H")
        samples.frombytes(pcm[: len(pcm) - len(pcm) % 2])
        if sys.byteorder == "big":
            samples.byteswap()
        table = _encode_table(self)
        return bytes(map(table.__getitem__, samples))

    def decode(self, data: bytes) -> bytes:
        """Decode to signed 16-bit little endian mono PCM."""
        samples = array("h", map(_decode_table(self).__getitem__, data))
        if sys.byteorder == "big":
            samples.byteswap()
        return samples.tobytes()
