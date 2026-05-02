from __future__ import annotations

import pytest
from pathlib import Path


@pytest.fixture
async def db(tmp_path):
    """Create a fresh test database with migrations applied."""
    from starting_point.db.database import Database

    db_path = tmp_path / "test.db"
    database = Database(db_path)
    await database.initialize()
    yield database
    await database.close()
