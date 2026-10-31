"""SIP message model, parser and serializer (RFC 3261)."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
import re
import secrets

SIP_VERSION = "SIP/2.0"
BRANCH_MAGIC = "z9hG4bK"

# RFC 3261 section 7.3.3 compact header forms
_COMPACT_FORMS = {
    "i": "Call-ID",
    "m": "Contact",
    "e": "Content-Encoding",
    "l": "Content-Length",
    "c": "Content-Type",
    "f": "From",
    "s": "Subject",
    "k": "Supported",
    "t": "To",
    "v": "Via",
}
_CANONICAL_NAMES = {
    name.lower(): name
    for name in (
        "Accept",
        "Allow",
        "Authorization",
        "Call-ID",
        "Contact",
        "Content-Length",
        "Content-Type",
        "CSeq",
        "Expires",
        "From",
        "Max-Forwards",
        "Proxy-Authorization",
        "Record-Route",
        "Route",
        "Server",
        "Supported",
        "To",
        "User-Agent",
        "Via",
        "Warning",
        "WWW-Authenticate",
    )
}
# Headers whose values may be combined into one comma separated line.
_MULTI_VALUE_HEADERS = {"via", "route", "record-route", "contact", "allow", "supported"}

STATUS_REASONS = {
    100: "Trying",
    180: "Ringing",
    200: "OK",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    405: "Method Not Allowed",
    415: "Unsupported Media Type",
    481: "Call/Transaction Does Not Exist",
    486: "Busy Here",
    487: "Request Terminated",
    488: "Not Acceptable Here",
    500: "Server Internal Error",
    501: "Not Implemented",
    503: "Service Unavailable",
}


class SipParseError(ValueError):
    """Raised when a datagram is not a valid SIP message."""


def canonical_header_name(name: str) -> str:
    """Return the canonical spelling of a header name."""
    lower = name.strip().lower()
    if lower in _COMPACT_FORMS:
        return _COMPACT_FORMS[lower]
    if lower in _CANONICAL_NAMES:
        return _CANONICAL_NAMES[lower]
    return "-".join(part.capitalize() for part in lower.split("-"))


def split_header_values(value: str) -> list[str]:
    """Split a comma separated header value, honouring quotes and <...>."""
    parts: list[str] = []
    current: list[str] = []
    in_quotes = False
    in_angle = False
    escaped = False
    for char in value:
        if escaped:
            current.append(char)
            escaped = False
            continue
        if char == "\\" and in_quotes:
            escaped = True
        elif char == '"':
            in_quotes = not in_quotes
        elif char == "<" and not in_quotes:
            in_angle = True
        elif char == ">" and not in_quotes:
            in_angle = False
        elif char == "," and not in_quotes and not in_angle:
            if part := "".join(current).strip():
                parts.append(part)
            current = []
            continue
        current.append(char)
    if part := "".join(current).strip():
        parts.append(part)
    return parts


def parse_params(text: str) -> dict[str, str | None]:
    """Parse ``;key=value;flag`` style parameters."""
    params: dict[str, str | None] = {}
    for item in text.split(";"):
        raw = item.strip()
        if not raw:
            continue
        key, sep, value = raw.partition("=")
        params[key.strip().lower()] = value.strip().strip('"') if sep else None
    return params


def format_params(params: dict[str, str | None]) -> str:
    """Format parameters back into ``;key=value`` form."""
    return "".join(
        f";{key}" if value is None else f";{key}={value}" for key, value in params.items()
    )


def generate_tag() -> str:
    """Generate a From/To tag."""
    return secrets.token_hex(6)


def generate_branch() -> str:
    """Generate an RFC 3261 compliant Via branch."""
    return BRANCH_MAGIC + secrets.token_hex(10)


def generate_call_id(host: str) -> str:
    """Generate a Call-ID."""
    return f"{secrets.token_hex(12)}@{host}"


@dataclass(slots=True)
class SipUri:
    """A sip: or sips: URI."""

    host: str
    user: str | None = None
    port: int | None = None
    scheme: str = "sip"
    params: dict[str, str | None] = field(default_factory=dict)
    headers: str = ""

    _PATTERN = re.compile(
        r"^(?P<scheme>sips?|tel):(?:(?P<user>[^@]+)@)?"
        r"(?P<host>\[[0-9a-fA-F:.]+\]|[^:;?]+)(?::(?P<port>\d+))?"
        r"(?P<params>;[^?]*)?(?:\?(?P<headers>.*))?$",
        re.IGNORECASE,
    )

    @classmethod
    def parse(cls, text: str) -> SipUri:
        """Parse a URI."""
        match = cls._PATTERN.match(text.strip())
        if match is None:
            raise SipParseError(f"Invalid SIP URI: {text!r}")
        user = match["user"]
        if user is not None:
            # Drop a password if present (user:password@host)
            user = user.partition(":")[0]
        return cls(
            scheme=match["scheme"].lower(),
            user=user,
            host=match["host"],
            port=int(match["port"]) if match["port"] else None,
            params=parse_params(match["params"] or ""),
            headers=match["headers"] or "",
        )

    def __str__(self) -> str:
        """Format the URI."""
        text = f"{self.scheme}:"
        if self.user:
            text += f"{self.user}@"
        text += self.host
        if self.port is not None:
            text += f":{self.port}"
        text += format_params(self.params)
        if self.headers:
            text += f"?{self.headers}"
        return text


@dataclass(slots=True)
class NameAddress:
    """A name-addr / addr-spec header value (From, To, Contact, Route)."""

    uri: SipUri
    display_name: str | None = None
    params: dict[str, str | None] = field(default_factory=dict)

    @classmethod
    def parse(cls, text: str) -> NameAddress:
        """Parse a header value such as ``"Bob" <sip:bob@host>;tag=1``."""
        text = text.strip()
        if "<" in text:
            display, _, rest = text.partition("<")
            uri_text, _, param_text = rest.partition(">")
            display = display.strip()
            if display.startswith('"') and display.endswith('"') and len(display) > 1:
                display = display[1:-1].replace('\\"', '"')
            return cls(
                uri=SipUri.parse(uri_text),
                display_name=display or None,
                params=parse_params(param_text),
            )
        # addr-spec form: header parameters follow the URI directly
        uri_text, _, param_text = text.partition(";")
        return cls(uri=SipUri.parse(uri_text), params=parse_params(param_text))

    @property
    def tag(self) -> str | None:
        """Return the tag parameter."""
        return self.params.get("tag")

    def __str__(self) -> str:
        """Format the header value."""
        text = f"<{self.uri}>"
        if self.display_name:
            escaped = self.display_name.replace('"', '\\"')
            text = f'"{escaped}" {text}'
        return text + format_params(self.params)


@dataclass(slots=True)
class Via:
    """A single Via header value."""

    transport: str
    host: str
    port: int | None = None
    params: dict[str, str | None] = field(default_factory=dict)

    _PATTERN = re.compile(
        r"^SIP\s*/\s*2\.0\s*/\s*(?P<transport>[A-Za-z]+)\s+"
        r"(?P<host>\[[0-9a-fA-F:.]+\]|[^:;\s]+)(?:\s*:\s*(?P<port>\d+))?\s*(?P<params>;.*)?$"
    )

    @classmethod
    def parse(cls, text: str) -> Via:
        """Parse a Via value."""
        match = cls._PATTERN.match(text.strip())
        if match is None:
            raise SipParseError(f"Invalid Via header: {text!r}")
        return cls(
            transport=match["transport"].upper(),
            host=match["host"],
            port=int(match["port"]) if match["port"] else None,
            params=parse_params(match["params"] or ""),
        )

    @property
    def branch(self) -> str | None:
        """Return the branch parameter."""
        return self.params.get("branch")

    def __str__(self) -> str:
        """Format the Via value."""
        text = f"SIP/2.0/{self.transport} {self.host}"
        if self.port is not None:
            text += f":{self.port}"
        return text + format_params(self.params)


@dataclass(slots=True)
class CSeq:
    """A CSeq header value."""

    number: int
    method: str

    @classmethod
    def parse(cls, text: str) -> CSeq:
        """Parse a CSeq value."""
        number, _, method = text.strip().partition(" ")
        try:
            return cls(int(number), method.strip().upper())
        except ValueError as err:
            raise SipParseError(f"Invalid CSeq: {text!r}") from err

    def __str__(self) -> str:
        """Format the CSeq value."""
        return f"{self.number} {self.method}"


class SipMessage:
    """Common behaviour of SIP requests and responses."""

    def __init__(
        self,
        headers: Iterable[tuple[str, str]] = (),
        body: bytes = b"",
    ) -> None:
        """Initialize the message."""
        self.headers: list[tuple[str, str]] = [
            (canonical_header_name(name), value) for name, value in headers
        ]
        self.body = body

    def get(self, name: str) -> str | None:
        """Return the first value of a header."""
        values = self.get_all(name)
        return values[0] if values else None

    def get_all(self, name: str) -> list[str]:
        """Return all values of a header, splitting comma separated lists."""
        name = canonical_header_name(name)
        values: list[str] = []
        for header, value in self.headers:
            if header != name:
                continue
            if header.lower() in _MULTI_VALUE_HEADERS:
                values.extend(split_header_values(value))
            else:
                values.append(value)
        return values

    def add(self, name: str, value: str) -> None:
        """Append a header."""
        self.headers.append((canonical_header_name(name), value))

    def set(self, name: str, value: str) -> None:
        """Replace all values of a header with one value."""
        self.remove(name)
        self.add(name, value)

    def remove(self, name: str) -> None:
        """Remove a header."""
        name = canonical_header_name(name)
        self.headers = [(key, value) for key, value in self.headers if key != name]

    @property
    def call_id(self) -> str:
        """Return the Call-ID."""
        return self._required("Call-ID")

    @property
    def cseq(self) -> CSeq:
        """Return the CSeq."""
        return CSeq.parse(self._required("CSeq"))

    @property
    def from_header(self) -> NameAddress:
        """Return the parsed From header."""
        return NameAddress.parse(self._required("From"))

    @property
    def to_header(self) -> NameAddress:
        """Return the parsed To header."""
        return NameAddress.parse(self._required("To"))

    @property
    def vias(self) -> list[Via]:
        """Return the parsed Via headers, topmost first."""
        return [Via.parse(value) for value in self.get_all("Via")]

    @property
    def content_type(self) -> str | None:
        """Return the media type of the body without parameters."""
        if (value := self.get("Content-Type")) is None:
            return None
        return value.partition(";")[0].strip().lower()

    def _required(self, name: str) -> str:
        if (value := self.get(name)) is None:
            raise SipParseError(f"Missing {name} header")
        return value

    def _start_line(self) -> str:
        raise NotImplementedError

    def encode(self) -> bytes:
        """Serialize the message."""
        lines = [self._start_line()]
        lines.extend(f"{name}: {value}" for name, value in self.headers if name != "Content-Length")
        lines.append(f"Content-Length: {len(self.body)}")
        return ("\r\n".join(lines) + "\r\n\r\n").encode() + self.body

    def __iter__(self) -> Iterator[tuple[str, str]]:
        """Iterate over the headers."""
        return iter(self.headers)


class SipRequest(SipMessage):
    """A SIP request."""

    def __init__(
        self,
        method: str,
        uri: str,
        headers: Iterable[tuple[str, str]] = (),
        body: bytes = b"",
    ) -> None:
        """Initialize the request."""
        super().__init__(headers, body)
        self.method = method.upper()
        self.uri = uri

    def _start_line(self) -> str:
        return f"{self.method} {self.uri} {SIP_VERSION}"

    def __repr__(self) -> str:
        """Represent the request."""
        return f"<SipRequest {self.method} {self.uri}>"


class SipResponse(SipMessage):
    """A SIP response."""

    def __init__(
        self,
        status: int,
        reason: str | None = None,
        headers: Iterable[tuple[str, str]] = (),
        body: bytes = b"",
    ) -> None:
        """Initialize the response."""
        super().__init__(headers, body)
        self.status = status
        self.reason = reason or STATUS_REASONS.get(status, "Unknown")

    def _start_line(self) -> str:
        return f"{SIP_VERSION} {self.status} {self.reason}"

    def __repr__(self) -> str:
        """Represent the response."""
        return f"<SipResponse {self.status} {self.reason}>"


def parse_message(data: bytes) -> SipRequest | SipResponse:
    """Parse a datagram into a SIP request or response."""
    head, sep, body = data.partition(b"\r\n\r\n")
    if not sep:
        # Be lenient with peers that only use LF
        head, sep, body = data.partition(b"\n\n")
        if not sep:
            raise SipParseError("Missing header terminator")
    try:
        text = head.decode("utf-8")
    except UnicodeDecodeError as err:
        raise SipParseError("Header is not valid UTF-8") from err

    raw_lines = text.replace("\r\n", "\n").split("\n")
    if not raw_lines or not raw_lines[0].strip():
        raise SipParseError("Empty message")
    start_line = raw_lines[0].strip()

    # Unfold continuation lines (RFC 3261 section 7.3.1)
    lines: list[str] = []
    for line in raw_lines[1:]:
        if line[:1] in (" ", "\t") and lines:
            lines[-1] += " " + line.strip()
        elif line:
            lines.append(line)

    headers: list[tuple[str, str]] = []
    for line in lines:
        name, sep, value = line.partition(":")
        if not sep or not name.strip():
            raise SipParseError(f"Malformed header line: {line!r}")
        headers.append((name.strip(), value.strip()))

    message: SipRequest | SipResponse
    if start_line.startswith(SIP_VERSION):
        parts = start_line.split(" ", 2)
        if len(parts) < 2 or not parts[1].isdigit():
            raise SipParseError(f"Malformed status line: {start_line!r}")
        message = SipResponse(int(parts[1]), parts[2] if len(parts) > 2 else "", headers)
    else:
        parts = start_line.split(" ")
        if len(parts) != 3 or parts[2] != SIP_VERSION:
            raise SipParseError(f"Malformed request line: {start_line!r}")
        message = SipRequest(parts[0], parts[1], headers)

    if (length := message.get("Content-Length")) is not None:
        try:
            body = body[: int(length)]
        except ValueError as err:
            raise SipParseError("Invalid Content-Length") from err
    message.body = body
    return message
