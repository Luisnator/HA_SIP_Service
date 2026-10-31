"""DTMF detection for RFC 4733 telephone-events and SIP INFO bodies."""

from __future__ import annotations

EVENT_TO_DIGIT = {
    **{event: str(event) for event in range(10)},
    10: "*",
    11: "#",
    12: "A",
    13: "B",
    14: "C",
    15: "D",
}
VALID_DIGITS = frozenset(EVENT_TO_DIGIT.values())


class TelephoneEventDetector:
    """Turn RFC 4733 telephone-event packets into key presses.

    Every packet of one key press shares the RTP timestamp of its start, and the
    final packet is usually sent three times. A digit is reported once, on the
    first packet seen for a new timestamp, so a key press triggers immediately.
    """

    def __init__(self) -> None:
        """Initialize the detector."""
        self._last_timestamp: int | None = None

    def feed(self, payload: bytes, timestamp: int) -> str | None:
        """Process a telephone-event payload, returning a new digit if any."""
        if len(payload) < 4:
            return None
        digit = EVENT_TO_DIGIT.get(payload[0])
        if digit is None or timestamp == self._last_timestamp:
            return None
        self._last_timestamp = timestamp
        return digit


def parse_info_body(content_type: str | None, body: bytes) -> str | None:
    """Extract a digit from a SIP INFO request (dtmf-relay or dtmf bodies)."""
    text = body.decode("utf-8", "replace").strip()
    if content_type == "application/dtmf-relay":
        for line in text.splitlines():
            key, _, value = line.partition("=")
            if key.strip().lower() == "signal":
                return _normalize(value.strip())
        return None
    if content_type == "application/dtmf":
        return _normalize(text)
    return None


def _normalize(value: str) -> str | None:
    if value.isdigit() and 10 <= int(value) <= 15:
        return EVENT_TO_DIGIT[int(value)]
    value = value.upper()
    return value if value in VALID_DIGITS else None
