from __future__ import annotations

import json
from pathlib import Path

import aiosqlite

SCHEMA_VERSION = 1

_MIGRATIONS = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    stage INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_messages_user_stage ON messages(user_id, stage);

CREATE TABLE IF NOT EXISTS conversation_states (
    user_id TEXT PRIMARY KEY,
    current_stage INTEGER NOT NULL DEFAULT 0,
    stage_data TEXT NOT NULL DEFAULT '{{}}',
    schema_version INTEGER NOT NULL DEFAULT {version},
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS startup_kits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    knowledge_points TEXT NOT NULL DEFAULT '[]',
    product_package TEXT NOT NULL DEFAULT '{{}}',
    content_direction TEXT NOT NULL DEFAULT '',
    platform_recommendations TEXT NOT NULL DEFAULT '[]',
    startup_materials TEXT NOT NULL DEFAULT '{{}}',
    generation_status TEXT NOT NULL DEFAULT 'pending',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_kits_user ON startup_kits(user_id);
""".format(version=SCHEMA_VERSION)


class Database:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA busy_timeout=5000")
        await self._conn.executescript(_MIGRATIONS)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database not initialized")
        return self._conn
