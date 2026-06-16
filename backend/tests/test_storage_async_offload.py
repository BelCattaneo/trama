import asyncio
import time

import pytest

from trama.main import app
from trama.sessions import COOKIE_NAME

from .conftest import client

PDF_HEADER = b"%PDF-"


@pytest.mark.asyncio
async def test_upload_does_not_block_event_loop(node_user):
    """A slow blocking storage.save must not stall concurrent async tasks."""
    payload = PDF_HEADER + b"x" * (10 * 1024 * 1024 - len(PDF_HEADER))
    assert len(payload) == 10 * 1024 * 1024

    real_storage = app.state.storage
    save_block_seconds = 0.5

    class SlowStorage:
        def save(self, content: bytes, content_hash: str) -> str:
            time.sleep(save_block_seconds)
            return real_storage.save(content, content_hash)

        def get(self, ref: str) -> bytes:
            return real_storage.get(ref)

        def exists(self, ref: str) -> bool:
            return real_storage.exists(ref)

    app.state.storage = SlowStorage()
    try:
        async with client() as c:
            c.cookies.set(COOKIE_NAME, node_user["session_id"])

            sleep_done_at: list[float] = []

            async def concurrent_sleep() -> None:
                await asyncio.sleep(0.1)
                sleep_done_at.append(time.monotonic())

            start = time.monotonic()
            upload_task = asyncio.create_task(
                c.post(
                    "/api/documents",
                    files={
                        "file": (
                            "big.pdf",
                            payload,
                            "application/octet-stream",
                        )
                    },
                )
            )
            sleep_task = asyncio.create_task(concurrent_sleep())

            await sleep_task
            sleep_finished_at = sleep_done_at[0] - start

            response = await upload_task
            upload_finished_at = time.monotonic() - start

        assert response.status_code == 201
        # The 0.1s sleep must finish well before the 0.5s blocking save would
        # have completed if it were running on the event loop thread.
        assert sleep_finished_at < save_block_seconds, (
            f"event loop blocked: concurrent sleep finished at "
            f"{sleep_finished_at:.3f}s, save blocks for {save_block_seconds}s"
        )
        # Sanity: the upload itself still takes at least the blocking time.
        assert upload_finished_at >= save_block_seconds
    finally:
        app.state.storage = real_storage
