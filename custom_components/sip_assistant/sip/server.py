"""SIP user agent server over UDP.

Implements what is needed for peer-to-peer calls from softphones, desk phones
and analog telephone adapters: INVITE/ACK/BYE/CANCEL with transaction
retransmissions, re-INVITE/UPDATE, INFO (DTMF), OPTIONS, digest authentication
and a minimal registrar so phones that insist on registering an account work.
"""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from dataclasses import dataclass, field
import ipaddress
import logging
import socket
from typing import Any, Protocol, cast

from ..rtp.dtmf import parse_info_body
from ..rtp.g711 import Codec
from ..rtp.session import NoFreePortError, RtpSession
from .auth import AuthResult, DigestAuthenticator
from .call import EndReason, SipCall
from .message import (
    BRANCH_MAGIC,
    NameAddress,
    SipParseError,
    SipRequest,
    SipResponse,
    SipUri,
    Via,
    generate_branch,
    generate_tag,
    parse_message,
)
from .sdp import MediaParameters, SdpError, SdpSession, negotiate, parse_sdp

_LOGGER = logging.getLogger(__name__)

T1 = 0.5
T2 = 4.0
TIMER_64T1 = 64 * T1
ALLOWED_METHODS = "INVITE, ACK, BYE, CANCEL, OPTIONS, INFO, UPDATE, REGISTER"
REGISTER_EXPIRES = 3600
DTMF_PAYLOAD_TYPE = 101

type IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network


@dataclass(slots=True, frozen=True)
class SipServerConfig:
    """Static configuration of the SIP server."""

    port: int
    user: str
    password: str | None = None
    bind_host: str = "0.0.0.0"
    realm: str = "homeassistant"
    external_host: str | None = None
    rtp_port_range: tuple[int, int] = (10000, 10100)
    allowed_networks: tuple[IPNetwork, ...] = ()
    max_calls: int = 2
    user_agent: str = "HomeAssistant-SIP-Assistant"
    preferred_codecs: tuple[Codec, ...] = ()


def _ensure_codec(media: MediaParameters, codec: Codec) -> None:
    if media.codec is not codec:
        raise SdpError("Changing the codec mid-call is not supported")


class CallListener(Protocol):
    """Receives call lifecycle notifications."""

    def call_established(self, call: SipCall) -> None:
        """A call was answered and acknowledged."""

    def call_ended(self, call: SipCall) -> None:
        """An established call ended."""

    def call_rejected(self, address: str, caller: str, reason: str) -> None:
        """An incoming call was rejected."""


@dataclass(slots=True)
class _ServerTransaction:
    """State kept to answer retransmitted requests."""

    destination: tuple[str, int]
    last_response: bytes | None = None
    final_status: int | None = None
    acked: asyncio.Event = field(default_factory=asyncio.Event)
    cancelled: bool = False
    expire: asyncio.TimerHandle | None = None


class SipServer(asyncio.DatagramProtocol):
    """Answers incoming calls and hands them to a :class:`CallListener`."""

    def __init__(self, config: SipServerConfig, listener: CallListener) -> None:
        """Initialize the server."""
        self.config = config
        self._listener = listener
        self._auth = (
            DigestAuthenticator(config.realm, config.user, config.password)
            if config.password
            else None
        )
        self._transport: asyncio.DatagramTransport | None = None
        self._transactions: dict[tuple[str, str], _ServerTransaction] = {}
        self._client_transactions: dict[str, asyncio.Future[SipResponse]] = {}
        self._calls: dict[tuple[str, str], SipCall] = {}
        self._tasks: set[asyncio.Task[None]] = set()
        self._closed = asyncio.Event()

    # Lifecycle

    async def start(self) -> None:
        """Bind the UDP socket."""
        loop = asyncio.get_running_loop()
        await loop.create_datagram_endpoint(
            lambda: self, local_addr=(self.config.bind_host, self.config.port)
        )
        _LOGGER.info("SIP server listening on %s:%s", self.config.bind_host, self.config.port)

    async def stop(self) -> None:
        """Hang up all calls and close the socket."""
        calls = self.calls
        for call in calls:
            call.finish(EndReason.SHUTDOWN)
        if calls:
            await asyncio.gather(
                *(self.send_bye(call, wait=1.0) for call in calls),
                return_exceptions=True,
            )
        tasks = list(self._tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        for transaction in self._transactions.values():
            if transaction.expire is not None:
                transaction.expire.cancel()
        self._transactions.clear()
        if self._transport is not None:
            self._transport.close()
            # The socket is only released once connection_lost has run; wait so
            # a reload can bind the same port again right away.
            try:
                async with asyncio.timeout(2):
                    await self._closed.wait()
            except TimeoutError:
                _LOGGER.debug("SIP socket did not close in time")

    @property
    def calls(self) -> list[SipCall]:
        """Return the active calls."""
        return [call for call in self._calls.values() if call.is_active]

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        """Store the transport."""
        self._transport = cast("asyncio.DatagramTransport", transport)

    def connection_lost(self, exc: Exception | None) -> None:
        """Forget the transport."""
        self._transport = None
        self._closed.set()

    def error_received(self, exc: Exception) -> None:
        """Log socket errors."""
        _LOGGER.debug("SIP socket error: %s", exc)

    # Datagram dispatch

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        """Handle a datagram."""
        if not data.strip(b"\r\n"):
            return  # CRLF keep-alive (RFC 5626)
        try:
            message = parse_message(data)
        except SipParseError as err:
            _LOGGER.debug("Ignoring malformed SIP datagram from %s: %s", addr, err)
            return
        addr = (addr[0], addr[1])
        _LOGGER.debug("Received %r from %s", message, addr)
        try:
            if isinstance(message, SipResponse):
                self._handle_response(message)
            else:
                self._handle_request(message, addr)
        except SipParseError as err:
            _LOGGER.debug("Rejecting malformed SIP request from %s: %s", addr, err)
            if isinstance(message, SipRequest) and message.method != "ACK":
                self._send_bad_request(message, addr, str(err))

    def _spawn(self, coro: Coroutine[Any, Any, None], name: str) -> asyncio.Task[None]:
        task = asyncio.get_running_loop().create_task(coro, name=name)
        self._tasks.add(task)
        task.add_done_callback(self._task_done)
        return task

    def schedule_bye(self, call: SipCall) -> asyncio.Task[None]:
        """Send BYE for a call in a server owned task."""
        return self._spawn(self.send_bye(call), "sip_assistant BYE")

    def _task_done(self, task: asyncio.Task[None]) -> None:
        self._tasks.discard(task)
        if not task.cancelled() and (err := task.exception()) is not None:
            _LOGGER.error("Error in %s", task.get_name(), exc_info=err)

    def _send(self, data: bytes, addr: tuple[str, int]) -> None:
        if self._transport is not None:
            self._transport.sendto(data, addr)

    # Incoming requests

    @staticmethod
    def _transaction_key(request: SipRequest, via: Via) -> str:
        branch = via.branch
        if branch and branch.startswith(BRANCH_MAGIC):
            return f"{branch}|{via.host}:{via.port}"
        # RFC 2543 peers: fall back to dialog identifiers
        return f"{request.call_id}|{request.cseq.number}|{request.from_header.tag}"

    def _new_transaction(
        self, key: str, method: str, request: SipRequest, addr: tuple[str, int]
    ) -> _ServerTransaction:
        transaction = _ServerTransaction(self._response_address(request, addr))
        self._transactions[(key, method)] = transaction
        transaction.expire = asyncio.get_running_loop().call_later(
            TIMER_64T1, self._transactions.pop, (key, method), None
        )
        return transaction

    def _handle_request(self, request: SipRequest, addr: tuple[str, int]) -> None:
        vias = request.vias
        if not vias:
            raise SipParseError("Missing Via header")
        # Parse required headers up front so malformed requests are rejected.
        cseq = request.cseq
        caller = request.from_header.uri.user or addr[0]
        to_tag = request.to_header.tag
        key = self._transaction_key(request, vias[0])

        if request.method == "ACK":
            self._handle_ack(request, key)
            return
        if cseq.method != request.method:
            raise SipParseError("CSeq method does not match request method")

        if (transaction := self._transactions.get((key, request.method))) is not None:
            if transaction.last_response is not None:
                self._send(transaction.last_response, transaction.destination)
            return
        transaction = self._new_transaction(key, request.method, request, addr)

        if request.method == "CANCEL":
            self._handle_cancel(request, key, transaction, caller)
            return
        if to_tag:
            self._handle_in_dialog(request, transaction, to_tag)
            return

        if not self._is_allowed(addr[0]):
            _LOGGER.warning(
                "Rejected SIP %s from %s (not in allowed networks)",
                request.method,
                addr[0],
            )
            if request.method == "INVITE":
                self._listener.call_rejected(addr[0], caller, "forbidden")
            self._reply(request, transaction, 403, to_tag=generate_tag())
            return

        match request.method:
            case "INVITE":
                self._spawn(
                    self._handle_invite(request, transaction, addr, caller),
                    "sip_assistant INVITE",
                )
            case "REGISTER":
                self._handle_register(request, transaction)
            case "OPTIONS":
                self._reply(
                    request,
                    transaction,
                    200,
                    to_tag=generate_tag(),
                    headers=[("Allow", ALLOWED_METHODS), ("Accept", "application/sdp")],
                )
            case "BYE" | "INFO" | "UPDATE":
                self._reply(request, transaction, 481)
            case _:
                self._reply(
                    request,
                    transaction,
                    405,
                    to_tag=generate_tag(),
                    headers=[("Allow", ALLOWED_METHODS)],
                )

    def _is_allowed(self, host: str) -> bool:
        if not self.config.allowed_networks:
            return True
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            return False
        return any(address in network for network in self.config.allowed_networks)

    def _check_auth(
        self, request: SipRequest, transaction: _ServerTransaction, to_tag: str
    ) -> bool:
        """Challenge the request unless it carries valid credentials."""
        if self._auth is None:
            return True
        result = self._auth.verify(
            request.method,
            request.get("Authorization") or request.get("Proxy-Authorization"),
        )
        if result is AuthResult.OK:
            return True
        if result is AuthResult.INVALID:
            _LOGGER.warning(
                "SIP authentication failed for %s from %s",
                request.method,
                transaction.destination[0],
            )
        self._reply(
            request,
            transaction,
            401,
            to_tag=to_tag,
            headers=[("WWW-Authenticate", self._auth.challenge(stale=result is AuthResult.STALE))],
        )
        return False

    def _handle_register(self, request: SipRequest, transaction: _ServerTransaction) -> None:
        to_tag = generate_tag()
        if not self._check_auth(request, transaction, to_tag):
            return
        expires = request.get("Expires") or str(REGISTER_EXPIRES)
        headers = [
            (
                "Contact",
                contact if ";expires=" in contact.lower() else f"{contact};expires={expires}",
            )
            for contact in request.get_all("Contact")
            if contact.strip() != "*"
        ]
        headers.append(("Expires", expires))
        _LOGGER.debug("Accepted registration from %s", transaction.destination[0])
        self._reply(request, transaction, 200, to_tag=to_tag, headers=headers)

    async def _handle_invite(
        self,
        request: SipRequest,
        transaction: _ServerTransaction,
        addr: tuple[str, int],
        caller: str,
    ) -> None:
        to_tag = generate_tag()
        if not self._check_auth(request, transaction, to_tag):
            return
        self._reply(request, transaction, 100)
        if len(self.calls) >= self.config.max_calls:
            self._listener.call_rejected(addr[0], caller, "busy")
            self._reply(request, transaction, 486, to_tag=to_tag)
            return

        media: MediaParameters | None = None
        if request.body and request.content_type == "application/sdp":
            try:
                media = negotiate(parse_sdp(request.body), self.config.preferred_codecs)
            except SdpError as err:
                _LOGGER.warning("Rejecting call from %s: %s", caller, err)
                self._listener.call_rejected(addr[0], caller, "unsupported_media")
                self._reply(
                    request,
                    transaction,
                    488,
                    to_tag=to_tag,
                    headers=[("Warning", f'304 {self.config.user_agent} "{err}"')],
                )
                return

        codec = media.codec if media else self._offer_codecs()[0]
        call: SipCall | None = None

        def on_dtmf(digit: str) -> None:
            if call is not None:
                call.handle_dtmf(digit)

        try:
            rtp = await RtpSession.open(
                bind_host=self.config.bind_host,
                port_range=self.config.rtp_port_range,
                codec=codec,
                payload_type=media.payload_type if media else codec.payload_type,
                dtmf_payload_type=media.dtmf_payload_type if media else DTMF_PAYLOAD_TYPE,
                remote_addr=(media.remote_host, media.remote_port) if media else (addr[0], 0),
                allowed_hosts={addr[0]},
                on_dtmf=on_dtmf,
            )
        except NoFreePortError:
            _LOGGER.error("No free RTP port available in %s", self.config.rtp_port_range)
            self._listener.call_rejected(addr[0], caller, "no_media_port")
            self._reply(request, transaction, 503, to_tag=to_tag)
            return

        if transaction.cancelled:
            rtp.close()
            return

        local_ip = self._local_ip_for(addr[0])
        sdp = SdpSession(self._advertised_host(local_ip), rtp.local_port)
        call = SipCall(
            server=self,
            invite=request,
            source=addr,
            local_tag=to_tag,
            local_ip=local_ip,
            rtp=rtp,
            sdp=sdp,
            media=media,
        )
        self._calls[(call.call_id, to_tag)] = call
        body = sdp.answer(media) if media else sdp.offer(self._offer_codecs())
        self._reply(
            request,
            transaction,
            200,
            to_tag=to_tag,
            headers=[*self._dialog_headers(call), ("Content-Type", "application/sdp")],
            body=body,
        )
        _LOGGER.info("Answered call %s from %s", call.call_id, call.caller.display)
        await self._retransmit_until_ack(call, transaction)

    def _offer_codecs(self) -> tuple[Codec, ...]:
        preferred = self.config.preferred_codecs or (Codec.PCMA, Codec.PCMU)
        return (*preferred, *(codec for codec in Codec if codec not in preferred))

    async def _retransmit_until_ack(self, call: SipCall, transaction: _ServerTransaction) -> None:
        """Retransmit a 2xx response until the ACK arrives (RFC 3261 13.3.1.4)."""
        ack = call.ack_event
        ack.clear()
        interval = T1
        loop = asyncio.get_running_loop()
        deadline = loop.time() + TIMER_64T1
        while not ack.is_set():
            try:
                await asyncio.wait_for(ack.wait(), interval)
            except TimeoutError:
                if loop.time() >= deadline:
                    _LOGGER.warning("No ACK received for call %s", call.call_id)
                    call.finish(EndReason.ACK_TIMEOUT)
                    await self.send_bye(call, wait=1.0)
                    return
                if transaction.last_response is not None:
                    self._send(transaction.last_response, transaction.destination)
                interval = min(interval * 2, T2)

    def _handle_ack(self, request: SipRequest, key: str) -> None:
        transaction = self._transactions.get((key, "INVITE"))
        if (
            transaction is not None
            and transaction.final_status is not None
            and transaction.final_status >= 300
        ):
            transaction.acked.set()  # ACK for a rejected INVITE
            return
        call = self._calls.get((request.call_id, request.to_header.tag or ""))
        if call is None:
            return
        if call.media is None and request.body:
            # Delayed offer: the answer arrives in the ACK.
            try:
                call.media = negotiate(parse_sdp(request.body), (call.rtp.codec,))
            except SdpError as err:
                _LOGGER.warning("Unusable SDP answer in ACK: %s", err)
            else:
                call.rtp.update_remote(
                    (call.media.remote_host, call.media.remote_port), {call.source[0]}
                )
        call.ack_event.set()
        if call.established or not call.is_active:
            return
        if call.media is None or call.media.codec is not call.rtp.codec:
            _LOGGER.warning("Call %s has no usable media description", call.call_id)
            self._spawn(call.hangup(), "sip_assistant hangup")
            return
        call.established = True
        self._listener.call_established(call)

    def _handle_cancel(
        self,
        request: SipRequest,
        key: str,
        transaction: _ServerTransaction,
        caller: str,
    ) -> None:
        invite_tx = self._transactions.get((key, "INVITE"))
        if invite_tx is None:
            self._reply(request, transaction, 481)
            return
        self._reply(request, transaction, 200)
        if invite_tx.final_status is not None:
            return  # already answered; the caller follows up with BYE
        invite_tx.cancelled = True
        for call in list(self._calls.values()):
            if call.call_id == request.call_id and not call.established:
                call.finish(EndReason.CANCELLED)
        self._listener.call_rejected(transaction.destination[0], caller, "cancelled")
        response = self._build_response(
            request, 487, destination=invite_tx.destination, to_tag=generate_tag()
        )
        response.set("CSeq", f"{request.cseq.number} INVITE")
        invite_tx.last_response = response.encode()
        invite_tx.final_status = 487
        self._send(invite_tx.last_response, invite_tx.destination)
        self._spawn(self._retransmit_final(invite_tx), "sip_assistant final response")

    def _handle_in_dialog(
        self, request: SipRequest, transaction: _ServerTransaction, to_tag: str
    ) -> None:
        call = self._calls.get((request.call_id, to_tag))
        if call is None or not call.is_active:
            self._reply(request, transaction, 481)
            return
        match request.method:
            case "BYE":
                self._reply(request, transaction, 200)
                _LOGGER.info("Call %s ended by caller", call.call_id)
                call.finish(EndReason.REMOTE_HANGUP)
            case "INFO":
                if (digit := parse_info_body(request.content_type, request.body)) is not None:
                    call.handle_dtmf(digit)
                self._reply(request, transaction, 200)
            case "INVITE" | "UPDATE":
                self._handle_reinvite(request, transaction, call)
            case "OPTIONS":
                self._reply(request, transaction, 200, headers=[("Allow", ALLOWED_METHODS)])
            case _:
                self._reply(request, transaction, 405, headers=[("Allow", ALLOWED_METHODS)])

    def _handle_reinvite(
        self, request: SipRequest, transaction: _ServerTransaction, call: SipCall
    ) -> None:
        headers = self._dialog_headers(call)
        body = b""
        if request.body and request.content_type == "application/sdp":
            try:
                media = negotiate(parse_sdp(request.body), (call.rtp.codec,))
                _ensure_codec(media, call.rtp.codec)
            except SdpError as err:
                self._reply(
                    request,
                    transaction,
                    488,
                    headers=[("Warning", f'304 {self.config.user_agent} "{err}"')],
                )
                return
            call.media = media
            call.rtp.update_remote((media.remote_host, media.remote_port), {call.source[0]})
            body = call.sdp.answer(media)
        elif request.method == "INVITE":
            body = call.sdp.offer((call.rtp.codec,))
        if body:
            headers.append(("Content-Type", "application/sdp"))
        self._reply(request, transaction, 200, headers=headers, body=body)
        if request.method == "INVITE":
            self._spawn(self._retransmit_until_ack(call, transaction), "sip_assistant re-INVITE")

    # Incoming responses (to our BYE)

    def _handle_response(self, response: SipResponse) -> None:
        vias = response.vias
        if not vias or (branch := vias[0].branch) is None:
            return
        future = self._client_transactions.get(branch)
        if future is not None and not future.done() and response.status >= 200:
            future.set_result(response)

    # Sending responses

    @staticmethod
    def _response_address(request: SipRequest, addr: tuple[str, int]) -> tuple[str, int]:
        """Where to send responses (RFC 3261 18.2.2 with RFC 3581 rport)."""
        via = request.vias[0]
        if "rport" in via.params:
            return addr
        return (addr[0], via.port or 5060)

    def _build_response(
        self,
        request: SipRequest,
        status: int,
        *,
        destination: tuple[str, int],
        to_tag: str | None = None,
        headers: list[tuple[str, str]] | None = None,
        body: bytes = b"",
    ) -> SipResponse:
        response = SipResponse(status)
        for index, value in enumerate(request.get_all("Via")):
            if index:
                response.add("Via", value)
                continue
            via = Via.parse(value)
            if via.host != destination[0]:
                via.params["received"] = destination[0]
            if "rport" in via.params:
                via.params["rport"] = str(destination[1])
            response.add("Via", str(via))
        response.add("From", request.get("From") or "")
        to_value = request.get("To") or ""
        if to_tag and request.to_header.tag is None:
            to_value += f";tag={to_tag}"
        response.add("To", to_value)
        response.add("Call-ID", request.call_id)
        response.add("CSeq", str(request.cseq))
        response.add("Server", self.config.user_agent)
        for name, value in headers or []:
            response.add(name, value)
        response.body = body
        return response

    def _reply(
        self,
        request: SipRequest,
        transaction: _ServerTransaction,
        status: int,
        *,
        to_tag: str | None = None,
        headers: list[tuple[str, str]] | None = None,
        body: bytes = b"",
    ) -> None:
        response = self._build_response(
            request,
            status,
            destination=transaction.destination,
            to_tag=to_tag,
            headers=headers,
            body=body,
        )
        transaction.last_response = response.encode()
        if status >= 200:
            transaction.final_status = status
        _LOGGER.debug("Sending %r to %s", response, transaction.destination)
        self._send(transaction.last_response, transaction.destination)
        if request.method == "INVITE" and status >= 300:
            self._spawn(self._retransmit_final(transaction), "sip_assistant final response")

    async def _retransmit_final(self, transaction: _ServerTransaction) -> None:
        """Retransmit a non-2xx final INVITE response until ACKed (timers G/H)."""
        interval = T1
        loop = asyncio.get_running_loop()
        deadline = loop.time() + TIMER_64T1
        while not transaction.acked.is_set() and loop.time() < deadline:
            try:
                await asyncio.wait_for(transaction.acked.wait(), interval)
            except TimeoutError:
                if transaction.last_response is not None:
                    self._send(transaction.last_response, transaction.destination)
                interval = min(interval * 2, T2)

    def _send_bad_request(self, request: SipRequest, addr: tuple[str, int], reason: str) -> None:
        try:
            response = self._build_response(request, 400, destination=addr)
        except SipParseError:
            return
        response.reason = f"Bad Request ({reason})"[:80]
        self._send(response.encode(), addr)

    # Requests we send

    async def send_bye(self, call: SipCall, wait: float = 4.0) -> None:
        """Send BYE for a call and wait briefly for the response."""
        call.local_cseq += 1
        branch = generate_branch()
        host = self._advertised_host(call.local_ip)
        request = SipRequest("BYE", call.remote_target)
        request.add("Via", f"SIP/2.0/UDP {host}:{self.config.port};branch={branch};rport")
        request.add("Max-Forwards", "70")
        request.add("From", call.local_to)
        request.add("To", call.remote_from)
        request.add("Call-ID", call.call_id)
        request.add("CSeq", f"{call.local_cseq} BYE")
        for route in call.route_set:
            request.add("Route", route)
        request.add("User-Agent", self.config.user_agent)
        destination = self._request_destination(call)
        data = request.encode()

        loop = asyncio.get_running_loop()
        future: asyncio.Future[SipResponse] = loop.create_future()
        self._client_transactions[branch] = future
        interval = T1
        deadline = loop.time() + min(wait, TIMER_64T1)
        try:
            self._send(data, destination)
            while not future.done() and loop.time() < deadline:
                try:
                    await asyncio.wait_for(
                        asyncio.shield(future), min(interval, deadline - loop.time())
                    )
                except TimeoutError:
                    self._send(data, destination)
                    interval = min(interval * 2, T2)
        finally:
            self._client_transactions.pop(branch, None)
        if future.done():
            _LOGGER.debug("BYE for %s answered with %s", call.call_id, future.result().status)
        else:
            future.cancel()
            _LOGGER.debug("BYE for %s was not answered", call.call_id)

    @staticmethod
    def _request_destination(call: SipCall) -> tuple[str, int]:
        """Pick where in-dialog requests go.

        Without a route set, requests follow the signalling path the INVITE
        came from, which keeps working behind NAT where the Contact header
        advertises an unreachable private address.
        """
        if call.route_set:
            uri = NameAddress.parse(call.route_set[0]).uri
            return (uri.host.strip("[]"), uri.port or 5060)
        return call.source

    def call_finished(self, call: SipCall) -> None:
        """Forget a finished call and notify the listener."""
        self._calls.pop((call.call_id, call.local_tag), None)
        if call.established:
            self._listener.call_ended(call)

    # Helpers

    def _dialog_headers(self, call: SipCall) -> list[tuple[str, str]]:
        contact = SipUri(
            host=self._advertised_host(call.local_ip),
            user=self.config.user,
            port=self.config.port,
        )
        return [
            ("Contact", f"<{contact}>"),
            ("Allow", ALLOWED_METHODS),
            *(("Record-Route", route) for route in call.route_set),
        ]

    def _advertised_host(self, local_ip: str) -> str:
        return self.config.external_host or local_ip

    def _local_ip_for(self, remote_ip: str) -> str:
        """Return the local address the OS uses to reach ``remote_ip``."""
        if self.config.bind_host not in ("0.0.0.0", "::", ""):
            return self.config.bind_host
        family = socket.AF_INET6 if ":" in remote_ip else socket.AF_INET
        try:
            with socket.socket(family, socket.SOCK_DGRAM) as sock:
                sock.connect((remote_ip, 9))
                return str(sock.getsockname()[0])
        except OSError:
            return "127.0.0.1"
