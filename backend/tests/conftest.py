import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport

from trama import db
from trama.config import settings
from trama.main import app
from trama.storage import LocalStorage


@pytest.fixture(autouse=True, scope="session")
def _isolated_storage(tmp_path_factory):
    app.state.storage = LocalStorage(tmp_path_factory.mktemp("storage"))


@pytest_asyncio.fixture
async def pool_lifecycle():
    await db.open_pool(settings.database_url, settings.pool_min, settings.pool_max)
    yield
    await db.close_pool()


def client():
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
