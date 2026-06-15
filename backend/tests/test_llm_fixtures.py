import json
from pathlib import Path

import pytest
import pytest_asyncio

from trama.sessions import COOKIE_NAME

from .conftest import client

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "llm"
SCENARIOS = ["clean_table", "unreadable_markers", "illegible_image"]


@pytest_asyncio.fixture
async def setup(node_user):
    yield node_user


def _load_fixture(name: str) -> tuple[bytes, dict, dict]:
    base = FIXTURES_DIR / name
    image_bytes = (base / "input.jpg").read_bytes()
    llm_response = json.loads((base / "llm_response.json").read_text())
    expected_payload = json.loads((base / "expected_payload.json").read_text())
    return image_bytes, llm_response, expected_payload


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", SCENARIOS)
async def test_llm_fixture_matches_expected_payload(setup, monkeypatch, scenario):
    image_bytes, llm_response, expected_payload = _load_fixture(scenario)

    class _FixedClient:
        async def parse_image(self, image_bytes: bytes, prompt: str) -> dict:
            return llm_response

    monkeypatch.setattr(
        "trama.parsing.orchestrator.get_llm_client", lambda: _FixedClient()
    )

    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.post(
            "/api/documents",
            files={
                "file": (
                    f"{scenario}.jpg",
                    image_bytes,
                    "application/octet-stream",
                )
            },
        )

    assert response.status_code == 201
    attempt = response.json()["parse_attempt"]
    assert attempt["strategy"] == "llm"
    assert attempt["payload"] == expected_payload
