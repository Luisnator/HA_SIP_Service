"""Tests for SIP message parsing, SDP negotiation and digest authentication."""

from __future__ import annotations

import hashlib
import time
from unittest.mock import patch

import pytest

from custom_components.sip_assistant.rtp.g711 import Codec
from custom_components.sip_assistant.sip.auth import AuthResult, DigestAuthenticator, parse_digest
from custom_components.sip_assistant.sip.message import (
    NameAddress,
    SipParseError,
    SipRequest,
    SipResponse,
    SipUri,
    Via,
    parse_message,
    split_header_values,
)
from custom_components.sip_assistant.sip.sdp import SdpError, SdpSession, negotiate, parse_sdp

INVITE = (
    b"INVITE sip:homeassistant@192.168.1.10 SIP/2.0\r\n"
    b"Via: SIP/2.0/UDP 192.168.1.20:5062;branch=z9hG4bK776asdhds;rport\r\n"
    b"Max-Forwards: 70\r\n"
    b'f: "Alice, Home" <sip:alice@192.168.1.20>;tag=1928301774\r\n'
    b"To: <sip:homeassistant@192.168.1.10>\r\n"
    b"i: a84b4c76e66710@pc33\r\n"
    b"CSeq: 314159 INVITE\r\n"
    b"Contact: <sip:alice@192.168.1.20:5062;transport=udp>\r\n"
    b"Record-Route: <sip:p1.example.com;lr>, <sip:p2.example.com;lr>\r\n"
    b"Content-Type: application/sdp\r\n"
    b"Subject: folded\r\n"
    b" header\r\n"
    b"Content-Length: 4\r\n"
    b"\r\n"
    b"v=0\r\nIGNORED"
)

SDP_OFFER = (
    "v=0\r\n"
    "o=alice 2890844526 2890844526 IN IP4 192.168.1.20\r\n"
    "s=-\r\n"
    "c=IN IP4 192.168.1.20\r\n"
    "t=0 0\r\n"
    "m=audio 49170 RTP/AVP 9 0 8 101\r\n"
    "a=rtpmap:9 G722/8000\r\n"
    "a=rtpmap:0 PCMU/8000\r\n"
    "a=rtpmap:101 telephone-event/8000\r\n"
    "a=fmtp:101 0-16\r\n"
    "a=ptime:20\r\n"
    "a=sendrecv\r\n"
)


def test_parse_request() -> None:
    """Requests are parsed including compact and folded headers."""
    message = parse_message(INVITE)
    assert isinstance(message, SipRequest)
    assert message.method == "INVITE"
    assert message.call_id == "a84b4c76e66710@pc33"
    assert message.cseq.number == 314159
    assert message.cseq.method == "INVITE"
    assert message.from_header.display_name == "Alice, Home"
    assert message.from_header.tag == "1928301774"
    assert message.from_header.uri.user == "alice"
    assert message.to_header.tag is None
    assert message.get("Subject") == "folded header"
    assert message.get_all("Record-Route") == [
        "<sip:p1.example.com;lr>",
        "<sip:p2.example.com;lr>",
    ]
    assert message.body == b"v=0\r"
    assert message.content_type == "application/sdp"
    via = message.vias[0]
    assert via.host == "192.168.1.20"
    assert via.port == 5062
    assert via.branch == "z9hG4bK776asdhds"
    assert "rport" in via.params


def test_parse_response_and_roundtrip() -> None:
    """Responses serialize and parse back."""
    response = SipResponse(486, headers=[("Via", "SIP/2.0/UDP host;branch=z9hG4bKx")])
    response.add("Call-ID", "abc")
    data = response.encode()
    assert data.startswith(b"SIP/2.0 486 Busy Here\r\n")
    assert b"Content-Length: 0\r\n\r\n" in data
    parsed = parse_message(data)
    assert isinstance(parsed, SipResponse)
    assert parsed.status == 486
    assert parsed.call_id == "abc"


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"garbage without terminator",
        b"INVITE sip:x SIP/1.0\r\n\r\n",
        b"SIP/2.0 abc OK\r\n\r\n",
        b"INVITE sip:x SIP/2.0\r\nbroken header\r\n\r\n",
    ],
)
def test_parse_invalid(data: bytes) -> None:
    """Malformed messages raise SipParseError."""
    with pytest.raises(SipParseError):
        parse_message(data)


def test_uri_and_name_address() -> None:
    """URIs and name-addr values parse and format."""
    uri = SipUri.parse("sip:bob:secret@[2001:db8::1]:5070;transport=udp?subject=x")
    assert uri.user == "bob"
    assert uri.host == "[2001:db8::1]"
    assert uri.port == 5070
    assert uri.params == {"transport": "udp"}
    address = NameAddress.parse("sip:carol@example.com;tag=abc")
    assert address.tag == "abc"
    assert str(address) == "<sip:carol@example.com>;tag=abc"
    named = NameAddress.parse('"Quote \\" Me" <sip:x@y>')
    assert named.display_name == 'Quote " Me'
    with pytest.raises(SipParseError):
        SipUri.parse("http://example.com")


def test_via_and_header_splitting() -> None:
    """Via values and comma separated headers are handled."""
    via = Via.parse("SIP / 2.0 / UDP 10.0.0.1 ; branch=z9hG4bKabc ; rport")
    assert via.transport == "UDP"
    assert via.port is None
    via.params["rport"] = "5060"
    assert str(via) == "SIP/2.0/UDP 10.0.0.1;branch=z9hG4bKabc;rport=5060"
    assert split_header_values('"a, b" <sip:x>, <sip:y;p=1,2>') == [
        '"a, b" <sip:x>',
        "<sip:y;p=1,2>",
    ]


def test_sdp_negotiation_prefers_offer_order() -> None:
    """The first supported codec in the offer wins, DTMF is detected."""
    media = negotiate(parse_sdp(SDP_OFFER))
    assert media.codec is Codec.PCMU
    assert media.payload_type == 0
    assert media.dtmf_payload_type == 101
    assert media.remote_host == "192.168.1.20"
    assert media.remote_port == 49170

    preferred = negotiate(parse_sdp(SDP_OFFER.replace("101\r\n", "8 101\r\n", 1)), (Codec.PCMA,))
    assert preferred.codec is Codec.PCMA


def test_sdp_rejects_unsupported() -> None:
    """Offers without G.711 over RTP/AVP are rejected."""
    with pytest.raises(SdpError):
        negotiate(parse_sdp(SDP_OFFER.replace("RTP/AVP 9 0 8 101", "RTP/AVP 9")))
    with pytest.raises(SdpError):
        negotiate(parse_sdp(SDP_OFFER.replace("RTP/AVP", "RTP/SAVP")))


def test_sdp_answer_and_offer() -> None:
    """Answers mirror the negotiated media and flip hold directions."""
    media = negotiate(parse_sdp(SDP_OFFER.replace("a=sendrecv", "a=sendonly")))
    session = SdpSession("192.168.1.10", 10002)
    answer = session.answer(media).decode()
    assert "m=audio 10002 RTP/AVP 0 101" in answer
    assert "a=rtpmap:101 telephone-event/8000" in answer
    assert "a=recvonly" in answer
    assert "c=IN IP4 192.168.1.10" in answer
    second = session.answer(media).decode()
    assert f"o=HomeAssistant {session.session_id} 2 IN IP4" in second

    offer = parse_sdp(session.offer((Codec.PCMA, Codec.PCMU)))
    assert offer.media[0].formats == [8, 0, 101]
    assert negotiate(offer).codec is Codec.PCMA


def _digest_response(nonce: str, method: str, uri: str, password: str, *, qop: bool = True) -> str:
    def md5(text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

    ha1 = md5(f"phone:homeassistant:{password}")
    ha2 = md5(f"{method}:{uri}")
    if qop:
        response = md5(f"{ha1}:{nonce}:00000001:abcdef:auth:{ha2}")
        extra = ', qop=auth, nc=00000001, cnonce="abcdef"'
    else:
        response = md5(f"{ha1}:{nonce}:{ha2}")
        extra = ""
    return (
        f'Digest username="phone", realm="homeassistant", nonce="{nonce}", '
        f'uri="{uri}", response="{response}", algorithm=MD5{extra}'
    )


def test_digest_authentication() -> None:
    """Digest credentials are verified with stateless nonces."""
    auth = DigestAuthenticator("homeassistant", "phone", "secret")
    challenge = parse_digest(auth.challenge())
    nonce = challenge["nonce"]
    assert challenge["realm"] == "homeassistant"
    assert challenge["qop"] == "auth"

    uri = "sip:homeassistant@192.168.1.10"
    assert auth.verify("INVITE", None) is AuthResult.MISSING
    assert auth.verify("INVITE", _digest_response(nonce, "INVITE", uri, "secret")) is AuthResult.OK
    assert (
        auth.verify("INVITE", _digest_response(nonce, "INVITE", uri, "secret", qop=False))
        is AuthResult.OK
    )
    assert (
        auth.verify("INVITE", _digest_response(nonce, "INVITE", uri, "wrong")) is AuthResult.INVALID
    )
    assert (
        auth.verify("BYE", _digest_response(nonce, "INVITE", uri, "secret")) is AuthResult.INVALID
    )
    forged = nonce[:-1] + ("0" if nonce[-1] != "0" else "1")
    assert (
        auth.verify("INVITE", _digest_response(forged, "INVITE", uri, "secret"))
        is AuthResult.INVALID
    )
    with patch(
        "custom_components.sip_assistant.sip.auth.time.time", return_value=time.time() + 3600
    ):
        assert (
            auth.verify("INVITE", _digest_response(nonce, "INVITE", uri, "secret"))
            is AuthResult.STALE
        )
