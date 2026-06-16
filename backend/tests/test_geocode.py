import httpx
import pytest

from trama.geocode import USER_AGENT, GeocodingResult, geocode


def _client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_geocode_success():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                {
                    "lat": "-34.6037",
                    "lon": "-58.3816",
                    "address": {"state": "Ciudad Autónoma de Buenos Aires"},
                }
            ],
        )

    async with _client(handler) as client:
        result = await geocode("Plaza de Mayo", client=client)
    assert result == GeocodingResult(-34.6037, -58.3816, "Ciudad Autónoma de Buenos Aires")


@pytest.mark.asyncio
async def test_geocode_empty_result_returns_none():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    async with _client(handler) as client:
        assert await geocode("nowhere", client=client) is None


@pytest.mark.asyncio
async def test_geocode_http_error_returns_none():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    async with _client(handler) as client:
        assert await geocode("boom", client=client) is None


@pytest.mark.asyncio
async def test_geocode_network_error_returns_none():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no network")

    async with _client(handler) as client:
        assert await geocode("no-net", client=client) is None


@pytest.mark.asyncio
async def test_geocode_timeout_returns_none():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("slow")

    async with _client(handler) as client:
        assert await geocode("slow", client=client) is None


@pytest.mark.asyncio
async def test_geocode_falls_back_to_city_then_county():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[{"lat": "0", "lon": "0", "address": {"city": "Rosario"}}],
        )

    async with _client(handler) as client:
        result = await geocode("x", client=client)
    assert result.zone_label == "Rosario"


@pytest.mark.asyncio
async def test_geocode_sets_user_agent():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["ua"] = request.headers.get("user-agent")
        return httpx.Response(200, json=[{"lat": "0", "lon": "0", "address": {}}])

    async with _client(handler) as client:
        await geocode("test", client=client)
    assert captured["ua"] == USER_AGENT
