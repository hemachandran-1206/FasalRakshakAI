"""Password hashing (argon2id), JWT access tokens and a small login-failure throttle."""
import time
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from ..config import settings

_ph = PasswordHasher()
ALGORITHM = "HS256"
MIN_PASSWORD_LENGTH = 10


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def create_token(user_id: uuid.UUID) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
    return jwt.encode({"sub": str(user_id), "exp": exp}, settings.jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str) -> uuid.UUID | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        return uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


# --- login throttle: 5 failures per email per 15 minutes (in-memory, per process) ---
MAX_FAILURES, WINDOW_S = 5, 15 * 60
_failures: dict[str, list[float]] = {}


def too_many_failures(key: str) -> bool:
    now = time.monotonic()
    recent = [t for t in _failures.get(key, []) if now - t < WINDOW_S]
    _failures[key] = recent
    return len(recent) >= MAX_FAILURES


def record_failure(key: str) -> None:
    _failures.setdefault(key, []).append(time.monotonic())


def clear_failures(key: str | None = None) -> None:
    if key is None:
        _failures.clear()
    else:
        _failures.pop(key, None)


class SlidingLimiter:
    """Allow at most `max_events` per `window_s` seconds per key (in memory, per process)."""
    def __init__(self, max_events: int, window_s: int):
        self.max_events, self.window_s, self._events = max_events, window_s, {}

    def hit(self, key: str) -> bool:
        now = time.monotonic()
        recent = [t for t in self._events.get(key, []) if now - t < self.window_s]
        allowed = len(recent) < self.max_events
        if allowed:
            recent.append(now)
        self._events[key] = recent
        return allowed

    def clear(self) -> None:
        self._events.clear()


lookup_limiter = SlidingLimiter(max_events=30, window_s=600)     # case-code lookups per client per 10 min
