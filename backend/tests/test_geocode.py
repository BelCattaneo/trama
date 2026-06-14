import httpx

from trama.geocode import USER_AGENT, GeocodingResult, geocode


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_geocode_success():
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

    result = geocode("Plaza de Mayo", client=_client(handler))
    assert result == GeocodingResult(-34.6037, -58.3816, "Ciudad Autónoma de Buenos Aires")


def test_geocode_empty_result_returns_none():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    assert geocode("nowhere", client=_client(handler)) is None


def test_geocode_http_error_returns_none():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    assert geocode("boom", client=_client(handler)) is None


def test_geocode_network_error_returns_none():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no network")

    assert geocode("no-net", client=_client(handler)) is None


def test_geocode_timeout_returns_none():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("slow")

    assert geocode("slow", client=_client(handler)) is None


def test_geocode_falls_back_to_city_then_county():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[{"lat": "0", "lon": "0", "address": {"city": "Rosario"}}],
        )

    assert geocode("x", client=_client(handler)).zone_label == "Rosario"


def test_geocode_sets_user_agent():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["ua"] = request.headers.get("user-agent")
        return httpx.Response(200, json=[{"lat": "0", "lon": "0", "address": {}}])

    geocode("test", client=_client(handler))
    assert captured["ua"] == USER_AGENT
