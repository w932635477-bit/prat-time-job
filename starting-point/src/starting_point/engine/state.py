from __future__ import annotations

from pathlib import Path

import aiosqlite

from starting_point.db.migrations import run_migrations
from starting_point.models import UserState


class StateManager:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    async def initialize(self) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await run_migrations(db)

    async def save_state(self, state: UserState) -> None:
        data = state.model_dump_json()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO user_states (user_id, data) VALUES (?, ?)",
                (state.user_id, data),
            )
            await db.commit()

    async def load_state(self, user_id: str) -> UserState | None:
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                "SELECT data FROM user_states WHERE user_id = ?",
                (user_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return UserState.model_validate_json(row[0])
