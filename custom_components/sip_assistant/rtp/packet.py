"""RTP packet encoding and decoding (RFC 3550)."""

from __future__ import annotations

from dataclasses import dataclass
import struct

RTP_VERSION = 2
_HEADER = struct.Struct("!BBHII")


class RtpError(ValueError):
    """Raised for malformed RTP packets."""


@dataclass(slots=True, frozen=True)
class RtpPacket:
    """A decoded RTP packet."""

    payload_type: int
    sequence: int
    timestamp: int
    ssrc: int
    payload: bytes
    marker: bool = False

    @classmethod
    def decode(cls, data: bytes) -> RtpPacket:
        """Decode a datagram."""
        if len(data) < _HEADER.size:
            raise RtpError("Packet too short")
        first, second, sequence, timestamp, ssrc = _HEADER.unpack_from(data)
        if first >> 6 != RTP_VERSION:
            raise RtpError("Unsupported RTP version")
        offset = _HEADER.size + (first & 0x0F) * 4  # skip CSRC list
        end = len(data)
        if first & 0x20:  # padding
            if end == 0 or data[-1] == 0:
                raise RtpError("Invalid padding")
            end -= data[-1]
        if first & 0x10:  # header extension
            if offset + 4 > end:
                raise RtpError("Truncated header extension")
            (length,) = struct.unpack_from("!H", data, offset + 2)
            offset += 4 + length * 4
        if offset > end:
            raise RtpError("Truncated packet")
        return cls(
            payload_type=second & 0x7F,
            marker=bool(second & 0x80),
            sequence=sequence,
            timestamp=timestamp,
            ssrc=ssrc,
            payload=data[offset:end],
        )

    def encode(self) -> bytes:
        """Encode the packet without CSRCs, extensions or padding."""
        return (
            _HEADER.pack(
                RTP_VERSION << 6,
                (0x80 if self.marker else 0) | (self.payload_type & 0x7F),
                self.sequence & 0xFFFF,
                self.timestamp & 0xFFFFFFFF,
                self.ssrc & 0xFFFFFFFF,
            )
            + self.payload
        )


def is_rtcp(data: bytes) -> bool:
    """Return True for RTCP packets multiplexed on the RTP port (RFC 5761)."""
    return len(data) >= 2 and 192 <= data[1] <= 223
