import pytest
import pytest_asyncio

from trama.sessions import COOKIE_NAME

from .conftest import cleanup_node, client, make_node_with_user


@pytest_asyncio.fixture
async def setup(pool_lifecycle):
    data = await make_node_with_user(
        zone_label="CABA", address_text="Some street 123"
    )
    yield data
    await cleanup_node(data["node_id"], data["user_id"])


@pytest.mark.asyncio
async def test_me_authenticated(setup):
    async with client() as c:
        c.cookies.set(COOKIE_NAME, setup["session_id"])
        response = await c.get("/api/me")
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == setup["email"]
    assert body["user"]["full_name"] == "Test User"
    assert body["node"]["cuit"] == setup["cuit"]
    assert body["node"]["display_name"] == "Test Node"
    assert body["node"]["role"] == "consumer"
    assert body["node"]["zone_label"] == "CABA"
    assert "password_hash" not in response.text
    assert "never-exposed-hash" not in response.text


@pytest.mark.asyncio
async def test_me_unauthenticated_no_cookie():
    async with client() as c:
        response = await c.get("/api/me")
    assert response.status_code == 401
    assert response.json() == {"error": "no autenticado"}


@pytest.mark.asyncio
async def test_me_unauthenticated_invalid_cookie(setup):
    async with client() as c:
        c.cookies.set(COOKIE_NAME, "completely-invalid-session-id")
        response = await c.get("/api/me")
    assert response.status_code == 401
    assert response.json() == {"error": "no autenticado"}
