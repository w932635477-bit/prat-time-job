from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_initialize_creates_tables(db):
    """All tables should exist after initialization."""
    conn = db.conn()
    cursor = await conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = {row[0] for row in await cursor.fetchall()}
    assert "messages" in tables
    assert "conversation_states" in tables
    assert "startup_kits" in tables


@pytest.mark.asyncio
async def test_schema_version_in_conversation_states(db):
    """conversation_states should have schema_version column."""
    conn = db.conn()
    cursor = await conn.execute("PRAGMA table_info(conversation_states)")
    columns = {row[1] for row in await cursor.fetchall()}
    assert "schema_version" in columns
