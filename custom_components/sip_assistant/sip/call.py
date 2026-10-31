"""A SIP call (dialog plus media) as seen by the application."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
import logging
from typing import TYPE_CHECKING

from ..rtp.session import RtpSession
from .message import NameAddress, SipRequest
from .sdp import MediaParameters, SdpSession

if TYPE_CHECKING:
    from .server import SipServer

_LOGGER = logging.getLogger(__name__)


class EndReason(StrEnum):
    """Why a call ended."""

    REMOTE_HANGUP = "remote_hangup"
    LOCAL_HANGUP = "local_hangup"
    CANCELLED = "cancelled"
    ACK_TIMEOUT = "ack_timeout"
    SHUTDOWN = "shutdown"


@dataclass(slots=True, frozen=True)
class CallerId:
    """Who is calling."""

    number: str
    name: str | None
    uri: str
    address: str

    @property
    def display(self) -> str:
        """Return a human friendly representation."""
        return f"{self.name} ({self.number})" if self.name else self.number


class SipCall:
    """An established (or establishing) call on the SIP server."""

    def __init__(
        self,
        *,
        server: SipServer,
        invite: SipRequest,
        source: tuple[str, int],
        local_tag: str,
        local_ip: str,
        rtp: RtpSession,
        sdp: SdpSession,
        media: MediaParameters | None,
    ) -> None:
        """Initialize the call."""
        self._server = server
        self.call_id = invite.call_id
        self.local_tag = local_tag
        self.local_ip = local_ip
        self.source = source
        self.rtp = rtp
        self.sdp = sdp
        self.media = media

        from_header = invite.from_header
        self.remote_tag = from_header.tag or ""
        self.remote_from = invite.get("From") or ""
        to_header = invite.to_header
        to_header.params["tag"] = local_tag
        self.local_to = str(to_header)
        contacts = invite.get_all("Contact")
        self.remote_target = (
            str(NameAddress.parse(contacts[0]).uri) if contacts else str(from_header.uri)
        )
        self.route_set = invite.get_all("Record-Route")
        self.local_cseq = 0

        self.caller = CallerId(
            number=from_header.uri.user or from_header.uri.host,
            name=from_header.display_name,
            uri=str(from_header.uri),
            address=source[0],
        )
        self.dtmf_handler: Callable[[str], None] | None = None
        self.established = False
        self.terminated = asyncio.Event()
        self.end_reason: EndReason | None = None
        self.ack_event = asyncio.Event()

    @property
    def is_active(self) -> bool:
        """Return True until the call has ended."""
        return not self.terminated.is_set()

    def handle_dtmf(self, digit: str) -> None:
        """Forward a key press to the application."""
        _LOGGER.debug("Call %s: DTMF %s", self.call_id, digit)
        if self.dtmf_handler is not None and self.is_active:
            self.dtmf_handler(digit)

    async def hangup(self) -> None:
        """End the call from our side.

        The BYE transaction runs as a server task so it completes even when the
        task calling this method is cancelled.
        """
        if not self.is_active:
            return
        self.finish(EndReason.LOCAL_HANGUP)
        await asyncio.shield(self._server.schedule_bye(self))

    def finish(self, reason: EndReason) -> None:
        """Release resources and notify the server (idempotent)."""
        if not self.is_active:
            return
        self.end_reason = reason
        self.terminated.set()
        self.ack_event.set()
        self.rtp.close()
        self._server.call_finished(self)

    def __repr__(self) -> str:
        """Represent the call."""
        return f"<SipCall {self.call_id} from {self.caller.display}>"
