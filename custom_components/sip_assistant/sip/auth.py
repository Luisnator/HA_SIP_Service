"""HTTP digest authentication for incoming SIP requests (RFC 3261 / RFC 8760)."""

from __future__ import annotations

from enum import Enum
import hashlib
import hmac
import secrets
import time

NONCE_LIFETIME = 300  # seconds

_HASHES = {
    "MD5": hashlib.md5,
    "MD5-SESS": hashlib.md5,
    "SHA-256": hashlib.sha256,
    "SHA-256-SESS": hashlib.sha256,
}


class AuthResult(Enum):
    """Outcome of a credential check."""

    OK = "ok"
    MISSING = "missing"
    STALE = "stale"
    INVALID = "invalid"


def parse_digest(value: str) -> dict[str, str]:
    """Parse a ``Digest k=v, k="v"`` credentials header."""
    scheme, _, rest = value.strip().partition(" ")
    if scheme.lower() != "digest":
        return {}
    params: dict[str, str] = {}
    key: list[str] = []
    val: list[str] = []
    in_value = in_quotes = False
    for char in rest + ",":
        if in_value:
            if char == '"':
                in_quotes = not in_quotes
            elif char == "," and not in_quotes:
                params["".join(key).strip().lower()] = "".join(val).strip().strip('"')
                key, val, in_value = [], [], False
            else:
                val.append(char)
        elif char == "=":
            in_value = True
        elif char != ",":
            key.append(char)
    return params


class DigestAuthenticator:
    """Issue challenges and verify digest responses with stateless nonces."""

    def __init__(self, realm: str, username: str, password: str) -> None:
        """Initialize the authenticator."""
        self.realm = realm
        self._username = username
        self._password = password
        self._secret = secrets.token_bytes(32)

    def _sign(self, timestamp: str) -> str:
        return hmac.new(self._secret, timestamp.encode(), hashlib.sha256).hexdigest()[:32]

    def _new_nonce(self) -> str:
        timestamp = f"{int(time.time()):x}"
        return f"{timestamp}{self._sign(timestamp)}"

    def _nonce_state(self, nonce: str) -> AuthResult:
        timestamp, signature = nonce[:-32], nonce[-32:]
        if not timestamp or not hmac.compare_digest(signature, self._sign(timestamp)):
            return AuthResult.INVALID
        try:
            issued = int(timestamp, 16)
        except ValueError:
            return AuthResult.INVALID
        if time.time() - issued > NONCE_LIFETIME:
            return AuthResult.STALE
        return AuthResult.OK

    def challenge(self, *, stale: bool = False) -> str:
        """Return a WWW-Authenticate header value."""
        value = (
            f'Digest realm="{self.realm}", nonce="{self._new_nonce()}", algorithm=MD5, qop="auth"'
        )
        return value + (", stale=true" if stale else "")

    def verify(self, method: str, header: str | None) -> AuthResult:
        """Verify an Authorization header for a request method."""
        if not header:
            return AuthResult.MISSING
        params = parse_digest(header)
        required = ("username", "realm", "nonce", "uri", "response")
        if any(key not in params for key in required):
            return AuthResult.INVALID
        if params["realm"] != self.realm or not hmac.compare_digest(
            params["username"].encode(), self._username.encode()
        ):
            return AuthResult.INVALID
        algorithm = params.get("algorithm", "MD5").upper()
        if (hash_func := _HASHES.get(algorithm)) is None:
            return AuthResult.INVALID

        def digest(text: str) -> str:
            return hash_func(text.encode()).hexdigest()

        ha1 = digest(f"{params['username']}:{self.realm}:{self._password}")
        if algorithm.endswith("-SESS"):
            ha1 = digest(f"{ha1}:{params['nonce']}:{params.get('cnonce', '')}")
        ha2 = digest(f"{method}:{params['uri']}")
        if (qop := params.get("qop")) is not None:
            if qop.lower() != "auth" or "nc" not in params or "cnonce" not in params:
                return AuthResult.INVALID
            expected = digest(
                f"{ha1}:{params['nonce']}:{params['nc']}:{params['cnonce']}:{qop}:{ha2}"
            )
        else:
            expected = digest(f"{ha1}:{params['nonce']}:{ha2}")
        if not hmac.compare_digest(expected, params["response"].lower()):
            return AuthResult.INVALID
        # Only report a stale nonce once the password is known to be right, so
        # the client retries transparently instead of prompting the user.
        return self._nonce_state(params["nonce"])
