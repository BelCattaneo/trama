import os
import re
from pathlib import Path
from typing import Protocol

from fastapi import Request

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


class Storage(Protocol):
    def save(self, content: bytes, content_hash: str) -> str: ...
    def get(self, ref: str) -> bytes: ...
    def exists(self, ref: str) -> bool: ...


class LocalStorage:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def save(self, content: bytes, content_hash: str) -> str:
        if not _HASH_RE.match(content_hash):
            raise ValueError("content_hash must be 64 lowercase hex chars")
        prefix = content_hash[:2]
        prefix_dir = self.root / prefix
        prefix_dir.mkdir(parents=True, exist_ok=True)
        final = prefix_dir / content_hash
        ref = f"{prefix}/{content_hash}"
        if final.exists():
            return ref
        tmp = prefix_dir / f"{content_hash}.tmp"
        tmp.write_bytes(content)
        with tmp.open("rb") as f:
            os.fsync(f.fileno())
        tmp.rename(final)
        return ref

    def get(self, ref: str) -> bytes:
        return (self.root / _safe_ref(ref)).read_bytes()

    def exists(self, ref: str) -> bool:
        return (self.root / _safe_ref(ref)).is_file()


def _safe_ref(ref: str) -> Path:
    p = Path(ref)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError("invalid ref")
    return p


def get_storage(request: Request) -> Storage:
    return request.app.state.storage
