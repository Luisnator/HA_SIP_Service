"""A scripted SIP phone used to call the integration in tests."""

from __future__ import annotations

import asyncio
import hashlib
import secrets

from custom_components.sip_assistant.rtp.packet import RtpPacket
from custom_components.sip_assistant.sip.auth import parse_digest
from custom_components.sip_assistant.sip.message import (
    SipRequest,
    SipResponse,
    generate_branch,
    parse_message,
)
from custom_components.sip_assistant.sip.sdp import parse_sdp

DIGIT_EVENTS = {**{str(index): index for index in range(10)}, "*": 10, "#": 11}


class _Collector(asyncio.DatagramProtocol):
    def __init__(self) -> None:
        self.queue: asyncio.Queue[tuple[bytes, tuple[str, int]]] = asyncio.Queue()
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = transport  # type: ignore[assignment]

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        self.queue.put_nowait((data, addr))


class FakePhone:
    """Places one call to the SIP server on 127.0.0.1."""

    def __init__(self, server_port: int, user: str = "1001", name: str = "Test Phone") -> None:
        self.server = ("127.0.0.1", server_port)
        self.user = user
        self.name = name
        self.sip = _Collector()
        self.rtp = _Collector()
        self.call_id = f"{secrets.token_hex(8)}@test"
        self.tag = secrets.token_hex(4)
        self.cseq = 0
        self.remote_tag: str | None = None
        self.remote_rtp: tuple[str, int] | None = None
        self._rtp_seq = 0
        self._rtp_ts = 0

    async def __aenter__(self) -> FakePhone:
        loop = asyncio.get_running_loop()
        await loop.create_datagram_endpoint(lambda: self.sip, local_addr=("127.0.0.1", 0))
        await loop.create_datagram_endpoint(lambda: self.rtp, local_addr=("127.0.0.1", 0))
        return self

    async def __aexit__(self, *args: object) -> None:
        for collector in (self.sip, self.rtp):
            if collector.transport is not None:
                collector.transport.close()

    @property
    def sip_port(self) -> int:
        assert self.sip.transport is not None
        return self.sip.transport.get_extra_info("sockname")[1]

    @property
    def rtp_port(self) -> int:
        assert self.rtp.transport is not None
        return self.rtp.transport.get_extra_info("sockname")[1]

    # SIP

    def request(self, method: str, *, in_dialog: bool = True, body: bytes = b"") -> SipRequest:
        if method not in ("ACK", "CANCEL"):
            self.cseq += 1
        request = SipRequest(method, f"sip:homeassistant@127.0.0.1:{self.server[1]}")
        request.add(
            "Via", f"SIP/2.0/UDP 127.0.0.1:{self.sip_port};branch={generate_branch()};rport"
        )
        request.add("Max-Forwards", "70")
        request.add("From", f'"{self.name}" <sip:{self.user}@127.0.0.1>;tag={self.tag}')
        to = f"<sip:homeassistant@127.0.0.1:{self.server[1]}>"
        if in_dialog and self.remote_tag:
            to += f";tag={self.remote_tag}"
        request.add("To", to)
        request.add("Call-ID", self.call_id)
        request.add("CSeq", f"{self.cseq} {method}")
        request.add("Contact", f"<sip:{self.user}@127.0.0.1:{self.sip_port}>")
        request.body = body
        return request

    def invite(self, authorization: str | None = None, *, codecs: str = "0 8 101") -> SipRequest:
        sdp = (
            "v=0\r\n"
            f"o=test 1 1 IN IP4 127.0.0.1\r\n"
            "s=-\r\n"
            "c=IN IP4 127.0.0.1\r\n"
            "t=0 0\r\n"
            f"m=audio {self.rtp_port} RTP/AVP {codecs}\r\n"
            "a=rtpmap:0 PCMU/8000\r\n"
            "a=rtpmap:8 PCMA/8000\r\n"
            "a=rtpmap:101 telephone-event/8000\r\n"
            "a=fmtp:101 0-16\r\n"
            "a=sendrecv\r\n"
        ).encode()
        request = self.request("INVITE", in_dialog=False, body=sdp)
        request.add("Content-Type", "application/sdp")
        if authorization:
            request.add("Authorization", authorization)
        self.send(request)
        return request

    def send(self, message: SipRequest | SipResponse) -> None:
        assert self.sip.transport is not None
        self.sip.transport.sendto(message.encode(), self.server)

    async def receive(self, timeout: float = 5) -> SipRequest | SipResponse:
        data, _ = await asyncio.wait_for(self.sip.queue.get(), timeout)
        return parse_message(data)

    async def expect_response(self, status: int, timeout: float = 5) -> SipResponse:
        """Wait for a final (or the given provisional) response, skipping others."""
        while True:
            message = await self.receive(timeout)
            if isinstance(message, SipResponse) and (
                message.status == status or message.status >= 200
            ):
                assert message.status == status, f"expected {status}, got {message!r}"
                if message.cseq.method == "INVITE" and message.status < 300:
                    self.remote_tag = message.to_header.tag
                return message

    async def expect_request(self, method: str, timeout: float = 5) -> SipRequest:
        while True:
            message = await self.receive(timeout)
            if isinstance(message, SipRequest) and message.method == method:
                return message

    async def call(self, authorization: str | None = None) -> SipResponse:
        """INVITE, wait for 200 OK and send ACK."""
        invite = self.invite(authorization)
        response = await self.expect_response(200)
        self.ack(invite, response)
        media = parse_sdp(response.body).media[0]
        self.remote_rtp = ("127.0.0.1", media.port)
        return response

    def ack(self, invite: SipRequest, response: SipResponse) -> None:
        ack = SipRequest("ACK", invite.uri)
        if response.status >= 300:
            ack.add("Via", invite.get("Via") or "")  # same transaction
        else:
            ack.add(
                "Via", f"SIP/2.0/UDP 127.0.0.1:{self.sip_port};branch={generate_branch()};rport"
            )
        ack.add("From", invite.get("From") or "")
        ack.add("To", response.get("To") or "")
        ack.add("Call-ID", self.call_id)
        ack.add("CSeq", f"{invite.cseq.number} ACK")
        self.send(ack)

    def reply(self, request: SipRequest, status: int) -> None:
        response = SipResponse(status)
        for via in request.get_all("Via"):
            response.add("Via", via)
        for header in ("From", "To", "Call-ID", "CSeq"):
            response.add(header, request.get(header) or "")
        self.send(response)

    async def hang_up(self) -> None:
        self.send(self.request("BYE"))
        await self.expect_response(200)

    @staticmethod
    def authorization(challenge: SipResponse, user: str, password: str, uri: str) -> str:
        params = parse_digest(challenge.get("WWW-Authenticate") or "")

        def md5(text: str) -> str:
            return hashlib.md5(text.encode()).hexdigest()

        ha1 = md5(f"{user}:{params['realm']}:{password}")
        ha2 = md5(f"INVITE:{uri}")
        response = md5(f"{ha1}:{params['nonce']}:00000001:0a4f113b:auth:{ha2}")
        return (
            f'Digest username="{user}", realm="{params["realm"]}", nonce="{params["nonce"]}", '
            f'uri="{uri}", response="{response}", algorithm=MD5, qop=auth, nc=00000001, '
            'cnonce="0a4f113b"'
        )

    # RTP

    def press(self, digits: str) -> None:
        """Send RFC 4733 telephone-events for each digit."""
        assert self.rtp.transport is not None and self.remote_rtp is not None
        for digit in digits:
            self._rtp_ts += 1600
            event = DIGIT_EVENTS[digit]
            packets = [bytes([event, 0x0A, 0x00, 0xA0]), bytes([event, 0x0A, 0x01, 0x40])]
            packets += [bytes([event, 0x8A, 0x03, 0x20])] * 3
            for index, payload in enumerate(packets):
                self._rtp_seq += 1
                packet = RtpPacket(
                    payload_type=101,
                    sequence=self._rtp_seq,
                    timestamp=self._rtp_ts,
                    ssrc=1234,
                    payload=payload,
                    marker=index == 0,
                )
                self.rtp.transport.sendto(packet.encode(), self.remote_rtp)

    def send_audio(self, frames: int = 1, payload: bytes = b"\xff" * 160) -> None:
        assert self.rtp.transport is not None and self.remote_rtp is not None
        for _ in range(frames):
            self._rtp_seq += 1
            self._rtp_ts += 160
            packet = RtpPacket(
                payload_type=0,
                sequence=self._rtp_seq,
                timestamp=self._rtp_ts,
                ssrc=1234,
                payload=payload,
            )
            self.rtp.transport.sendto(packet.encode(), self.remote_rtp)

    async def received_audio(self, payload: bytes, timeout: float = 5) -> None:
        """Wait until an RTP packet with the given payload arrives."""
        async with asyncio.timeout(timeout):
            while True:
                data, _ = await self.rtp.queue.get()
                if RtpPacket.decode(data).payload == payload:
                    return
