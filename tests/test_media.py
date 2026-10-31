"""Tests for G.711, RTP packets, DTMF detection, tones and the RTP session."""

from __future__ import annotations

from array import array
import asyncio
import io
import socket
import struct
import wave

import pytest

from custom_components.sip_assistant.commands import CodeMatch, match_code
from custom_components.sip_assistant.rtp.dtmf import TelephoneEventDetector, parse_info_body
from custom_components.sip_assistant.rtp.g711 import (
    SAMPLES_PER_FRAME,
    Codec,
    alaw_to_linear,
    linear_to_alaw,
    linear_to_ulaw,
    ulaw_to_linear,
)
from custom_components.sip_assistant.rtp.packet import RtpError, RtpPacket, is_rtcp
from custom_components.sip_assistant.rtp.session import RtpSession
from custom_components.sip_assistant.rtp.tones import Tone, render_tone
from custom_components.sip_assistant.speech import wav_to_g711


@pytest.mark.parametrize(
    ("encode", "decode"),
    [(linear_to_ulaw, ulaw_to_linear), (linear_to_alaw, alaw_to_linear)],
)
def test_g711_roundtrip(encode, decode) -> None:
    """Every code word decodes and re-encodes to itself; errors stay small."""
    for value in range(256):
        sample = decode(value)
        assert encode(sample) == value or decode(encode(sample)) == sample
    for sample in range(-32768, 32768, 97):
        error = abs(decode(encode(sample)) - sample)
        assert error <= max(16, abs(sample) // 16)


def test_codec_helpers() -> None:
    """Codec enum lookups, silence and buffer conversion."""
    assert Codec.from_encoding_name("pcma") is Codec.PCMA
    assert Codec.from_static_payload_type(0) is Codec.PCMU
    assert Codec.from_static_payload_type(9) is None
    assert Codec.PCMU.silence(2) == b"\xff\xff"
    assert Codec.PCMA.silence(1) == b"\xd5"
    pcm = array("h", [0, 4000, -4000, 30000]).tobytes()
    for codec in Codec:
        decoded = array("h")
        decoded.frombytes(codec.decode(codec.encode(pcm)))
        assert len(decoded) == 4
        assert abs(decoded[1] - 4000) < 200


def test_rtp_packet_roundtrip() -> None:
    """Packets encode/decode, including CSRC, extension and padding."""
    packet = RtpPacket(
        payload_type=8, sequence=65535, timestamp=2**32 - 1, ssrc=7, payload=b"ab", marker=True
    )
    assert RtpPacket.decode(packet.encode()) == packet

    header = struct.pack("!BBHII", 0x80 | 0x20 | 0x10 | 1, 0, 1, 2, 3)
    data = (
        header
        + b"\x00\x00\x00\x09"
        + b"\xbe\xde\x00\x01"
        + b"\x00\x00\x00\x00"
        + b"xy"
        + b"\x00\x02"
    )
    decoded = RtpPacket.decode(data)
    assert decoded.payload == b"xy"
    with pytest.raises(RtpError):
        RtpPacket.decode(b"\x40" + bytes(11))
    with pytest.raises(RtpError):
        RtpPacket.decode(b"\x80")
    assert is_rtcp(b"\x80\xc8")
    assert not is_rtcp(packet.encode())


def test_telephone_event_detector() -> None:
    """A key press is reported once, repeated presses are detected."""
    detector = TelephoneEventDetector()
    start = bytes([5, 0x0A, 0, 160])
    end = bytes([5, 0x8A, 0x03, 0x20])
    assert detector.feed(start, 1000) == "5"
    assert detector.feed(start, 1000) is None
    assert detector.feed(end, 1000) is None
    assert detector.feed(end, 1000) is None
    assert detector.feed(bytes([5, 0x0A, 0, 160]), 3000) == "5"
    assert detector.feed(bytes([11, 0x0A, 0, 160]), 5000) == "#"
    assert detector.feed(bytes([200, 0, 0, 0]), 7000) is None
    assert detector.feed(b"\x01", 9000) is None


def test_sip_info_dtmf() -> None:
    """DTMF in SIP INFO bodies."""
    assert parse_info_body("application/dtmf-relay", b"Signal=7\r\nDuration=160\r\n") == "7"
    assert parse_info_body("application/dtmf-relay", b"Signal=11\r\n") == "#"
    assert parse_info_body("application/dtmf", b"*") == "*"
    assert parse_info_body("application/dtmf", b"x") is None
    assert parse_info_body("text/plain", b"5") is None


def test_match_code() -> None:
    """Codes complete as soon as they are unambiguous."""
    codes = ["1", "12", "3", "0"]
    assert match_code("1", codes) is CodeMatch.PARTIAL
    assert match_code("12", codes) is CodeMatch.COMPLETE
    assert match_code("3", codes) is CodeMatch.COMPLETE
    assert match_code("9", codes) is CodeMatch.NONE
    assert match_code("13", codes) is CodeMatch.NONE


def test_tones_and_wav_conversion() -> None:
    """Tones render to G.711 and WAV files are converted to 8 kHz."""
    tone = render_tone(Tone.CONFIRM, Codec.PCMA)
    assert len(tone) == 8 * (120 + 60 + 180)

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(array("h", [1000, 1000] * 1600).tobytes())
    converted = wav_to_g711(buffer.getvalue(), Codec.PCMU)
    assert len(converted) == 800
    assert set(converted) == {Codec.PCMU.encode(array("h", [1000]).tobytes())[0]}


async def test_rtp_session_send_and_receive(socket_enabled) -> None:
    """Audio is paced in frames, DTMF and audio are received from the latched peer."""
    loop = asyncio.get_running_loop()
    received: list[bytes] = []
    peer = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    peer.bind(("127.0.0.1", 0))
    peer.setblocking(False)
    digits: list[str] = []
    session = await RtpSession.open(
        bind_host="127.0.0.1",
        port_range=(42000, 42100),
        codec=Codec.PCMU,
        payload_type=0,
        dtmf_payload_type=101,
        remote_addr=peer.getsockname(),
        allowed_hosts={"127.0.0.1"},
        on_dtmf=digits.append,
    )
    session.audio_sink = received.append
    try:
        assert session.local_port % 2 == 0
        session.enqueue(b"\x01" * (SAMPLES_PER_FRAME * 2 + 10), "item")
        assert session.queued_ms == 41
        await asyncio.wait_for(session.wait_drained(), 2)
        assert session.played_ms("item") == 60

        packets = []
        while True:
            try:
                packets.append(RtpPacket.decode(await loop.sock_recv(peer, 2048)))
            except BlockingIOError:
                break
            if len(packets) >= 3:
                break
        assert all(len(packet.payload) == SAMPLES_PER_FRAME for packet in packets)

        target = ("127.0.0.1", session.local_port)
        audio = RtpPacket(payload_type=0, sequence=1, timestamp=160, ssrc=9, payload=b"\x7f" * 160)
        event = RtpPacket(
            payload_type=101, sequence=2, timestamp=320, ssrc=9, payload=bytes([9, 10, 0, 160])
        )
        peer.sendto(audio.encode(), target)
        peer.sendto(event.encode(), target)
        for _ in range(50):
            if digits and received:
                break
            await asyncio.sleep(0.01)
        assert received == [b"\x7f" * 160]
        assert digits == ["9"]

        session.enqueue(b"\x02" * SAMPLES_PER_FRAME * 10)
        session.clear()
        assert not session.is_playing
    finally:
        session.close()
        peer.close()
