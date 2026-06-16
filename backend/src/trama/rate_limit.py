import asyncio
import time
from dataclasses import dataclass, field
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException

from trama.sessions import AuthUser, require_user

UPLOAD_PER_MINUTE = 5
REPARSE_PER_MINUTE = 10

_TOO_MANY = "demasiadas solicitudes, esperá un momento"


@dataclass
class _Bucket:
    tokens: float
    last_refill: float
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


def _now() -> float:
    return time.monotonic()


class TokenBucketLimiter:
    """Per-user token bucket. Single-process, in-memory."""

    def __init__(self, capacity: int, per_seconds: float) -> None:
        self.capacity = capacity
        self.per_seconds = per_seconds
        self._buckets: dict[UUID, _Bucket] = {}
        self._buckets_lock = asyncio.Lock()

    async def _get_bucket(self, user_id: UUID) -> _Bucket:
        bucket = self._buckets.get(user_id)
        if bucket is not None:
            return bucket
        async with self._buckets_lock:
            bucket = self._buckets.get(user_id)
            if bucket is None:
                bucket = _Bucket(tokens=float(self.capacity), last_refill=_now())
                self._buckets[user_id] = bucket
            return bucket

    async def consume(self, user_id: UUID) -> bool:
        bucket = await self._get_bucket(user_id)
        async with bucket.lock:
            now = _now()
            elapsed = now - bucket.last_refill
            refill = elapsed * (self.capacity / self.per_seconds)
            bucket.tokens = min(float(self.capacity), bucket.tokens + refill)
            bucket.last_refill = now
            if bucket.tokens < 1.0:
                return False
            bucket.tokens -= 1.0
            return True

    def reset(self) -> None:
        self._buckets.clear()


_upload_limiter = TokenBucketLimiter(UPLOAD_PER_MINUTE, 60.0)
_reparse_limiter = TokenBucketLimiter(REPARSE_PER_MINUTE, 60.0)


def _get_upload_limiter() -> TokenBucketLimiter:
    return _upload_limiter


def _get_reparse_limiter() -> TokenBucketLimiter:
    return _reparse_limiter


async def rate_limit_upload(
    user: Annotated[AuthUser, Depends(require_user)],
) -> AuthUser:
    if not await _get_upload_limiter().consume(user.id):
        raise HTTPException(status_code=429, detail=_TOO_MANY)
    return user


async def rate_limit_reparse(
    user: Annotated[AuthUser, Depends(require_user)],
) -> AuthUser:
    if not await _get_reparse_limiter().consume(user.id):
        raise HTTPException(status_code=429, detail=_TOO_MANY)
    return user
