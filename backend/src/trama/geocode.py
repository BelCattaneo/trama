import time
from dataclasses import dataclass

import httpx

USER_AGENT = "trama/0.1 (academic project)"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
TIMEOUT_SECONDS = 5.0
MIN_INTERVAL = 1.0

_last_call: float = 0.0


@dataclass
class GeocodingResult:
    latitude: float
    longitude: float
    zone_label: str | None


def _throttle() -> None:
    global _last_call
    elapsed = time.monotonic() - _last_call
    if elapsed < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - elapsed)
    _last_call = time.monotonic()


def geocode(address: str, client: httpx.Client | None = None) -> GeocodingResult | None:
    own_client = client is None
    if own_client:
        _throttle()
        client = httpx.Client(timeout=TIMEOUT_SECONDS)
    try:
        response = client.get(
            NOMINATIM_URL,
            params={
                "q": address,
                "format": "json",
                "addressdetails": 1,
                "limit": 1,
            },
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        results = response.json()
    except (httpx.RequestError, httpx.HTTPStatusError):
        return None
    finally:
        if own_client:
            client.close()

    if not results:
        return None
    address_data = results[0].get("address", {})
    zone = (
        address_data.get("state")
        or address_data.get("city")
        or address_data.get("county")
    )
    return GeocodingResult(
        latitude=float(results[0]["lat"]),
        longitude=float(results[0]["lon"]),
        zone_label=zone,
    )
