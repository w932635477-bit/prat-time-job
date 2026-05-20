from __future__ import annotations

import asyncio
import urllib.request

import pytest
from pathlib import Path


def pytest_collection_modifyitems(config, items):
    """Skip e2e browser tests if dev server isn't running."""
    e2e_names = {i.nodeid for i in items if "test_e2e_browser" in i.nodeid}
    if not e2e_names:
        return
    try:
        urllib.request.urlopen("http://127.0.0.1:8000", timeout=2)
    except Exception:
        skip = pytest.mark.skip(reason="dev server not running at http://127.0.0.1:8000")
        for item in items:
            if "test_e2e_browser" in item.nodeid:
                item.add_marker(skip)


# Provide a `browser` fixture for e2e browser tests.
try:
    from playwright.async_api import async_playwright as _pw

    @pytest.fixture
    async def browser():
        pw = await _pw().start()
        try:
            b = await pw.chromium.launch(headless=True)
        except Exception:
            await pw.stop()
            pytest.skip("playwright browser binary not installed")
        yield b
        await b.close()
        await pw.stop()

except ModuleNotFoundError:

    @pytest.fixture
    def browser():  # type: ignore[misc]
        pytest.skip("playwright not installed")


@pytest.fixture
async def db(tmp_path):
    """Create a fresh test database with migrations applied."""
    from starting_point.db.database import Database

    db_path = tmp_path / "test.db"
    database = Database(db_path)
    await database.initialize()
    yield database
    await database.close()
