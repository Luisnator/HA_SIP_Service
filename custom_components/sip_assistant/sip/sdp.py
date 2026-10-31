"""Minimal SDP offer/answer handling for G.711 audio (RFC 4566 / RFC 3264)."""

from __future__ import annotations

from dataclasses import dataclass, field
import secrets

from ..rtp.g711 import Codec

TELEPHONE_EVENT = "telephone-event"
DEFAULT_DTMF_PAYLOAD_TYPE = 101
_SUPPORTED_PROFILES = {"RTP/AVP", "RTP/AVPF"}
_DIRECTIONS = {"sendrecv", "sendonly", "recvonly", "inactive"}
_ANSWER_DIRECTION = {
    "sendrecv": "sendrecv",
    "sendonly": "recvonly",
    "recvonly": "sendonly",
    "inactive": "inactive",
}


class SdpError(ValueError):
    """Raised when an SDP body cannot be parsed or negotiated."""


@dataclass(slots=True)
class MediaDescription:
    """An ``m=`` section."""

    media: str
    port: int
    protocol: str
    formats: list[int]
    connection: str | None = None
    rtpmap: dict[int, tuple[str, int]] = field(default_factory=dict)
    fmtp: dict[int, str] = field(default_factory=dict)
    direction: str = "sendrecv"
    ptime: int | None = None


@dataclass(slots=True)
class SessionDescription:
    """A parsed SDP body."""

    connection: str | None
    media: list[MediaDescription]
    direction: str = "sendrecv"


@dataclass(slots=True, frozen=True)
class MediaParameters:
    """The negotiated media parameters of a call."""

    codec: Codec
    payload_type: int
    dtmf_payload_type: int | None
    remote_host: str
    remote_port: int
    direction: str = "sendrecv"
    ptime: int = 20


def _connection_address(value: str) -> str:
    parts = value.split()
    if len(parts) < 3 or parts[0] != "IN" or parts[1] not in ("IP4", "IP6"):
        raise SdpError(f"Unsupported connection line: {value!r}")
    return parts[2].split("/")[0]


def parse_sdp(body: bytes | str) -> SessionDescription:
    """Parse an SDP body."""
    text = body.decode("utf-8", "replace") if isinstance(body, bytes) else body
    session = SessionDescription(connection=None, media=[])
    current: MediaDescription | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if len(line) < 2 or line[1] != "=":
            continue
        kind, value = line[0], line[2:].strip()
        if kind == "m":
            parts = value.split()
            if len(parts) < 4:
                raise SdpError(f"Malformed media line: {value!r}")
            try:
                port = int(parts[1].split("/")[0])
                formats = [int(fmt) for fmt in parts[3:] if fmt.isdigit()]
            except ValueError as err:
                raise SdpError(f"Malformed media line: {value!r}") from err
            current = MediaDescription(
                media=parts[0],
                port=port,
                protocol=parts[2],
                formats=formats,
                direction=session.direction,
            )
            session.media.append(current)
        elif kind == "c":
            address = _connection_address(value)
            if current is None:
                session.connection = address
            else:
                current.connection = address
        elif kind == "a":
            name, _, attr = value.partition(":")
            if name in _DIRECTIONS:
                if current is None:
                    session.direction = name
                else:
                    current.direction = name
            elif current is None:
                continue
            elif name == "rtpmap":
                payload, _, encoding = attr.partition(" ")
                enc_name, _, rate = encoding.partition("/")
                if payload.isdigit() and rate.split("/")[0].isdigit():
                    current.rtpmap[int(payload)] = (
                        enc_name.strip(),
                        int(rate.split("/")[0]),
                    )
            elif name == "fmtp":
                payload, _, params = attr.partition(" ")
                if payload.isdigit():
                    current.fmtp[int(payload)] = params.strip()
            elif name == "ptime" and attr.strip().isdigit():
                current.ptime = int(attr.strip())
    return session


def _codec_for(media: MediaDescription, payload_type: int) -> Codec | None:
    if payload_type in media.rtpmap:
        name, rate = media.rtpmap[payload_type]
        if rate != 8000:
            return None
        return Codec.from_encoding_name(name)
    return Codec.from_static_payload_type(payload_type)


def negotiate(offer: SessionDescription, preferred: tuple[Codec, ...] = ()) -> MediaParameters:
    """Pick audio parameters from a remote offer (or answer).

    The first codec in the remote's preference order that we support wins
    unless ``preferred`` lists codecs to favour.
    """
    for media in offer.media:
        if media.media != "audio" or media.port == 0:
            continue
        if media.protocol.upper() not in _SUPPORTED_PROFILES:
            continue
        host = media.connection or offer.connection
        if host is None:
            raise SdpError("Offer has no connection address")

        candidates: list[tuple[Codec, int]] = []
        dtmf_payload_type: int | None = None
        for payload_type in media.formats:
            if (codec := _codec_for(media, payload_type)) is not None:
                candidates.append((codec, payload_type))
            elif (
                payload_type in media.rtpmap
                and media.rtpmap[payload_type][0].lower() == TELEPHONE_EVENT
                and media.rtpmap[payload_type][1] == 8000
                and dtmf_payload_type is None
            ):
                dtmf_payload_type = payload_type
        if not candidates:
            continue
        for wanted in preferred:
            match = next((item for item in candidates if item[0] is wanted), None)
            if match is not None:
                break
        else:
            match = candidates[0]
        return MediaParameters(
            codec=match[0],
            payload_type=match[1],
            dtmf_payload_type=dtmf_payload_type,
            remote_host=host,
            remote_port=media.port,
            direction=media.direction,
            ptime=media.ptime or 20,
        )
    raise SdpError("No supported audio stream (PCMU/PCMA over RTP/AVP) offered")


@dataclass(slots=True)
class SdpSession:
    """Our side of an SDP session (keeps origin version across re-INVITEs)."""

    local_host: str
    local_port: int
    session_id: int = field(default_factory=lambda: secrets.randbelow(2**31))
    version: int = 0

    def _header(self) -> list[str]:
        self.version += 1
        family = "IP6" if ":" in self.local_host else "IP4"
        return [
            "v=0",
            f"o=HomeAssistant {self.session_id} {self.version} IN {family} {self.local_host}",
            "s=SIP Assistant",
            f"c=IN {family} {self.local_host}",
            "t=0 0",
        ]

    def answer(self, media: MediaParameters) -> bytes:
        """Build an answer for negotiated media parameters."""
        formats = [media.payload_type]
        if media.dtmf_payload_type is not None:
            formats.append(media.dtmf_payload_type)
        lines = self._header()
        lines.append(f"m=audio {self.local_port} RTP/AVP {' '.join(map(str, formats))}")
        lines.append(f"a=rtpmap:{media.payload_type} {media.codec.encoding_name}/8000")
        if media.dtmf_payload_type is not None:
            lines.append(f"a=rtpmap:{media.dtmf_payload_type} {TELEPHONE_EVENT}/8000")
            lines.append(f"a=fmtp:{media.dtmf_payload_type} 0-16")
        lines.append("a=ptime:20")
        lines.append(f"a={_ANSWER_DIRECTION.get(media.direction, 'sendrecv')}")
        return ("\r\n".join(lines) + "\r\n").encode()

    def offer(self, codecs: tuple[Codec, ...]) -> bytes:
        """Build an offer (used when the INVITE carried no SDP)."""
        formats = [codec.payload_type for codec in codecs]
        formats.append(DEFAULT_DTMF_PAYLOAD_TYPE)
        lines = self._header()
        lines.append(f"m=audio {self.local_port} RTP/AVP {' '.join(map(str, formats))}")
        lines.extend(
            f"a=rtpmap:{codec.payload_type} {codec.encoding_name}/8000" for codec in codecs
        )
        lines.append(f"a=rtpmap:{DEFAULT_DTMF_PAYLOAD_TYPE} {TELEPHONE_EVENT}/8000")
        lines.append(f"a=fmtp:{DEFAULT_DTMF_PAYLOAD_TYPE} 0-16")
        lines.append("a=ptime:20")
        lines.append("a=sendrecv")
        return ("\r\n".join(lines) + "\r\n").encode()
