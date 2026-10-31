"""Bidirectional RTP audio session for one call."""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Callable
import errno
import logging
import random
import secrets
from typing import cast

from .dtmf import TelephoneEventDetector
from .g711 import FRAME_MS, SAMPLES_PER_FRAME, Codec
from .packet import RtpError, RtpPacket, is_rtcp

_LOGGER = logging.getLogger(__name__)

FRAME_SECONDS = FRAME_MS / 1000
# When the sender falls this far behind schedule it resynchronises instead of
# bursting packets to catch up.
_MAX_LAG = 0.1
_MAX_TRACKED_TAGS = 32


class NoFreePortError(OSError):
    """Raised when no RTP port in the configured range is available."""


class RtpSession(asyncio.DatagramProtocol):
    """Send and receive G.711 audio and telephone-events on one UDP port.

    Outgoing audio is queued in 20 ms frames and paced in real time; silence is
    sent while nothing is queued so NAT bindings stay open and the remote jitter
    buffer keeps running. Incoming audio is handed to ``audio_sink``.
    """

    def __init__(
        self,
        *,
        codec: Codec,
        payload_type: int,
        dtmf_payload_type: int | None,
        remote_addr: tuple[str, int],
        allowed_hosts: set[str],
        on_dtmf: Callable[[str], None],
    ) -> None:
        """Initialize the session."""
        self.codec = codec
        self._payload_type = payload_type
        self._dtmf_payload_type = dtmf_payload_type
        self._remote_addr = remote_addr
        self._allowed_hosts = set(allowed_hosts) | {remote_addr[0]}
        self._latched = False
        self._on_dtmf = on_dtmf
        self._detector = TelephoneEventDetector()
        self.audio_sink: Callable[[bytes], None] | None = None

        self._transport: asyncio.DatagramTransport | None = None
        self._sender: asyncio.Task[None] | None = None
        self._ssrc = secrets.randbits(32)
        self._sequence = secrets.randbits(16)
        self._timestamp = secrets.randbits(32)
        self._silence = codec.silence()

        self._queue: deque[tuple[bytes, str | None]] = deque()
        self._pending = bytearray()
        self._pending_tag: str | None = None
        self._played: dict[str | None, int] = {}
        self._drained = asyncio.Event()
        self._drained.set()
        self._talking = False
        self.local_port = 0

    @classmethod
    async def open(
        cls,
        *,
        bind_host: str,
        port_range: tuple[int, int],
        codec: Codec,
        payload_type: int,
        dtmf_payload_type: int | None,
        remote_addr: tuple[str, int],
        allowed_hosts: set[str],
        on_dtmf: Callable[[str], None],
    ) -> RtpSession:
        """Bind a session to a free even port in ``port_range``."""
        loop = asyncio.get_running_loop()
        session = cls(
            codec=codec,
            payload_type=payload_type,
            dtmf_payload_type=dtmf_payload_type,
            remote_addr=remote_addr,
            allowed_hosts=allowed_hosts,
            on_dtmf=on_dtmf,
        )
        start, end = port_range
        ports = list(range(start + start % 2, end + 1, 2))
        offset = random.randrange(len(ports)) if ports else 0
        for port in ports[offset:] + ports[:offset]:
            try:
                await loop.create_datagram_endpoint(lambda: session, local_addr=(bind_host, port))
            except OSError as err:
                if err.errno in (errno.EADDRINUSE, errno.EACCES):
                    continue
                raise
            session.local_port = port
            return session
        raise NoFreePortError(f"No free RTP port in range {start}-{end}")

    # asyncio protocol callbacks

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        """Store the transport and start sending."""
        self._transport = cast("asyncio.DatagramTransport", transport)
        self._sender = asyncio.get_running_loop().create_task(
            self._send_loop(), name="sip_assistant RTP sender"
        )

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        """Handle an incoming packet."""
        if is_rtcp(data):
            return
        if self._latched:
            if addr[:2] != self._remote_addr:
                return
        elif addr[0] in self._allowed_hosts:
            # Symmetric RTP: answer to wherever the media actually comes from,
            # which also makes calls work through NAT.
            self._remote_addr = (addr[0], addr[1])
            self._latched = True
        else:
            return
        try:
            packet = RtpPacket.decode(data)
        except RtpError:
            return
        if packet.payload_type == self._payload_type:
            if self.audio_sink is not None:
                self.audio_sink(packet.payload)
        elif packet.payload_type == self._dtmf_payload_type and (
            digit := self._detector.feed(packet.payload, packet.timestamp)
        ):
            self._on_dtmf(digit)

    def error_received(self, exc: Exception) -> None:
        """Log socket errors (e.g. ICMP port unreachable)."""
        _LOGGER.debug("RTP socket error: %s", exc)

    def connection_lost(self, exc: Exception | None) -> None:
        """Stop sending when the socket closes."""
        if self._sender is not None:
            self._sender.cancel()

    # Media control

    def update_remote(self, remote_addr: tuple[str, int], allowed_hosts: set[str]) -> None:
        """Apply a new remote address from a re-INVITE."""
        if remote_addr != self._remote_addr:
            self._remote_addr = remote_addr
            self._allowed_hosts = set(allowed_hosts) | {remote_addr[0]}
            self._latched = False

    @property
    def is_playing(self) -> bool:
        """Return True while queued audio is being sent."""
        return bool(self._queue or self._pending)

    @property
    def queued_ms(self) -> int:
        """Return the amount of queued audio in milliseconds."""
        return (len(self._queue) * SAMPLES_PER_FRAME + len(self._pending)) // 8

    def enqueue(self, data: bytes, tag: str | None = None) -> None:
        """Queue encoded audio for playback; ``tag`` groups it for tracking."""
        if not data:
            return
        if tag != self._pending_tag:
            self._flush_pending()
            self._pending_tag = tag
        self._pending += data
        while len(self._pending) >= SAMPLES_PER_FRAME:
            self._queue.append((bytes(self._pending[:SAMPLES_PER_FRAME]), tag))
            del self._pending[:SAMPLES_PER_FRAME]
        self._drained.clear()

    def clear(self) -> None:
        """Drop all queued audio immediately (barge-in)."""
        self._queue.clear()
        self._pending.clear()
        self._drained.set()

    def played_ms(self, tag: str | None) -> int:
        """Return how much audio of ``tag`` has been sent."""
        return self._played.get(tag, 0)

    async def wait_drained(self) -> None:
        """Wait until all queued audio has been sent."""
        await self._drained.wait()

    def close(self) -> None:
        """Close the session."""
        self.clear()
        if self._sender is not None:
            self._sender.cancel()
        if self._transport is not None:
            self._transport.close()
            self._transport = None

    # Sending

    def _flush_pending(self) -> None:
        if self._pending:
            padding = self._silence[: SAMPLES_PER_FRAME - len(self._pending)]
            self._queue.append((bytes(self._pending) + padding, self._pending_tag))
            self._pending.clear()

    def _next_frame(self) -> tuple[bytes, bool]:
        if not self._queue and self._pending:
            self._flush_pending()
        if not self._queue:
            self._talking = False
            self._drained.set()
            return self._silence, False
        frame, tag = self._queue.popleft()
        if tag not in self._played and len(self._played) >= _MAX_TRACKED_TAGS:
            self._played.pop(next(iter(self._played)))
        self._played[tag] = self._played.get(tag, 0) + FRAME_MS
        marker = not self._talking
        self._talking = True
        return frame, marker

    async def _send_loop(self) -> None:
        loop = asyncio.get_running_loop()
        next_time = loop.time()
        while self._transport is not None:
            frame, marker = self._next_frame()
            packet = RtpPacket(
                payload_type=self._payload_type,
                sequence=self._sequence,
                timestamp=self._timestamp,
                ssrc=self._ssrc,
                payload=frame,
                marker=marker,
            )
            self._transport.sendto(packet.encode(), self._remote_addr)
            self._sequence = (self._sequence + 1) & 0xFFFF
            self._timestamp = (self._timestamp + SAMPLES_PER_FRAME) & 0xFFFFFFFF
            if not self._queue and not self._pending:
                self._drained.set()

            next_time += FRAME_SECONDS
            delay = next_time - loop.time()
            if delay < -_MAX_LAG:
                next_time = loop.time()
                delay = 0
            await asyncio.sleep(max(delay, 0))
