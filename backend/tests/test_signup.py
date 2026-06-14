from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport

from trama import db
from trama.config import settings
from trama.geocode import GeocodingResult
from trama.main import app
from trama.sessions import COOKIE_NAME

# Synthetic CUITs with valid AFIP checksums. Not registered to any real entity.
VALID_CUIT_A = "20-00000002-8"
VALID_CUIT_B = "20-00000003-6"
VALID_CUIT_C = "20-00000004-4"
VALID_CUIT_D = "20-00000005-2"


@pytest_asyncio.fixture
async def signup_db():
    await db.open_pool(settings.database_url, settings.pool_min, settings.pool_max)
    created_node_ids: list[str] = []
    yield created_node_ids
    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            for nid in created_node_ids:
                await cur.execute("DELETE FROM app_user WHERE node_id = %s", (nid,))
                await cur.execute("DELETE FROM node WHERE id = %s", (nid,))
    await db.close_pool()


def _client():
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _email() -> str:
    return f"test-{uuid4().hex[:8]}@example.com"


@pytest.mark.asyncio
async def test_signup_with_address_geocodes(signup_db, monkeypatch):
    fake = GeocodingResult(latitude=-34.61, longitude=-58.38, zone_label="CABA")
    monkeypatch.setattr("trama.auth_routes.geocode", lambda _addr: fake)

    async with _client() as client:
        response = await client.post(
            "/api/auth/signup",
            json={
                "cuit": VALID_CUIT_A,
                "display_name": "Cooperativa A",
                "role": "consumer",
                "email": _email(),
                "password": "secret",
                "address": "Av. de Mayo 760, CABA",
            },
        )
    assert response.status_code == 201
    body = response.json()
    assert "node_id" in body and "user_id" in body
    assert COOKIE_NAME in response.cookies
    signup_db.append(body["node_id"])

    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT latitude, longitude, zone_label FROM node WHERE id = %s",
                (body["node_id"],),
            )
            row = await cur.fetchone()
    assert row == (-34.61, -58.38, "CABA")


@pytest.mark.asyncio
async def test_signup_with_manual_coords_skips_geocoding(signup_db, monkeypatch):
    calls: list[str] = []

    def should_not_be_called(_addr):
        calls.append(_addr)
        return None

    monkeypatch.setattr("trama.auth_routes.geocode", should_not_be_called)

    async with _client() as client:
        response = await client.post(
            "/api/auth/signup",
            json={
                "cuit": VALID_CUIT_B,
                "display_name": "Cooperativa B",
                "role": "producer",
                "email": _email(),
                "password": "secret",
                "latitude": -34.6,
                "longitude": -58.4,
            },
        )
    assert response.status_code == 201
    assert calls == []
    signup_db.append(response.json()["node_id"])


@pytest.mark.asyncio
async def test_signup_invalid_cuit(signup_db):
    async with _client() as client:
        response = await client.post(
            "/api/auth/signup",
            json={
                "cuit": "20-12345678-9",
                "display_name": "Bad",
                "role": "consumer",
                "email": _email(),
                "password": "secret",
                "latitude": 0,
                "longitude": 0,
            },
        )
    assert response.status_code == 400
    assert response.json() == {"error": "CUIT inválido"}


@pytest.mark.asyncio
async def test_signup_duplicate_cuit(signup_db, monkeypatch):
    monkeypatch.setattr(
        "trama.auth_routes.geocode",
        lambda _: GeocodingResult(latitude=0, longitude=0, zone_label=None),
    )
    payload = {
        "cuit": VALID_CUIT_C,
        "display_name": "First",
        "role": "consumer",
        "email": _email(),
        "password": "secret",
        "latitude": 0,
        "longitude": 0,
    }
    async with _client() as client:
        first = await client.post("/api/auth/signup", json=payload)
        assert first.status_code == 201
        signup_db.append(first.json()["node_id"])

        second_payload = {**payload, "email": _email()}
        second = await client.post("/api/auth/signup", json=second_payload)
    assert second.status_code == 409
    assert second.json() == {"error": "CUIT ya registrado"}


@pytest.mark.asyncio
async def test_signup_duplicate_email(signup_db):
    shared_email = _email()
    payload = {
        "cuit": VALID_CUIT_C,
        "display_name": "First",
        "role": "consumer",
        "email": shared_email,
        "password": "secret",
        "latitude": 0,
        "longitude": 0,
    }
    async with _client() as client:
        first = await client.post("/api/auth/signup", json=payload)
        assert first.status_code == 201
        signup_db.append(first.json()["node_id"])

        second_payload = {**payload, "cuit": VALID_CUIT_D}
        second = await client.post("/api/auth/signup", json=second_payload)
    assert second.status_code == 409
    assert second.json() == {"error": "email ya registrado"}


@pytest.mark.asyncio
async def test_signup_geocoding_fails(signup_db, monkeypatch):
    monkeypatch.setattr("trama.auth_routes.geocode", lambda _: None)

    async with _client() as client:
        response = await client.post(
            "/api/auth/signup",
            json={
                "cuit": VALID_CUIT_A,
                "display_name": "Unfound",
                "role": "consumer",
                "email": _email(),
                "password": "secret",
                "address": "this address does not exist anywhere",
            },
        )
    assert response.status_code == 400
    assert response.json() == {
        "error": "no se pudo ubicar la dirección, ingresá coordenadas manualmente"
    }


@pytest.mark.asyncio
async def test_signup_hashes_password(signup_db):
    plaintext = "do-not-store-me-raw"
    async with _client() as client:
        response = await client.post(
            "/api/auth/signup",
            json={
                "cuit": VALID_CUIT_A,
                "display_name": "Coop",
                "role": "consumer",
                "email": _email(),
                "password": plaintext,
                "latitude": 0,
                "longitude": 0,
            },
        )
    assert response.status_code == 201
    user_id = response.json()["user_id"]
    signup_db.append(response.json()["node_id"])

    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT password_hash FROM app_user WHERE id = %s", (user_id,)
            )
            (stored,) = await cur.fetchone()
    assert stored != plaintext
    assert stored.startswith("$2b$")


@pytest.mark.asyncio
async def test_signup_rolls_back_on_email_conflict(signup_db):
    shared_email = _email()
    first_payload = {
        "cuit": VALID_CUIT_A,
        "display_name": "First",
        "role": "consumer",
        "email": shared_email,
        "password": "secret",
        "latitude": 0,
        "longitude": 0,
    }
    async with _client() as client:
        first = await client.post("/api/auth/signup", json=first_payload)
        assert first.status_code == 201
        signup_db.append(first.json()["node_id"])

        second_payload = {**first_payload, "cuit": VALID_CUIT_B}
        second = await client.post("/api/auth/signup", json=second_payload)
        assert second.status_code == 409

    async with db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id FROM node WHERE cuit = %s", (VALID_CUIT_B,))
            row = await cur.fetchone()
    assert row is None
