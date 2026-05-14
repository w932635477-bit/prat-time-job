from __future__ import annotations

import json
from typing import Any

from starting_point.db.database import Database


class MessageRepo:
    """Repository for messages table operations."""

    def __init__(self, db: Database) -> None:
        self._db = db

    async def save(self, user_id: str, role: str, content: str, stage: int) -> None:
        conn = self._db.conn()
        await conn.execute(
            "INSERT INTO messages (user_id, role, content, stage) VALUES (?, ?, ?, ?)",
            (user_id, role, content, stage),
        )
        await conn.commit()

    async def load(self, user_id: str, stage: int) -> list[dict[str, str]]:
        conn = self._db.conn()
        cursor = await conn.execute(
            "SELECT role, content FROM messages WHERE user_id = ? AND stage = ? ORDER BY id",
            (user_id, stage),
        )
        rows = await cursor.fetchall()
        return [{"role": row["role"], "content": row["content"]} for row in rows]

    async def load_up_to_stage(self, user_id: str, max_stage: int) -> list[dict[str, str]]:
        conn = self._db.conn()
        cursor = await conn.execute(
            "SELECT role, content, stage FROM messages WHERE user_id = ? AND stage <= ? ORDER BY id",
            (user_id, max_stage),
        )
        rows = await cursor.fetchall()
        return [{"role": row["role"], "content": row["content"], "stage": row["stage"]} for row in rows]

    async def count_by_role(self, user_id: str, stage: int, role: str) -> int:
        conn = self._db.conn()
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM messages WHERE user_id = ? AND stage = ? AND role = ?",
            (user_id, stage, role),
        )
        row = await cursor.fetchone()
        return row[0]


class StateRepo:
    """Repository for conversation_states table operations."""

    def __init__(self, db: Database) -> None:
        self._db = db

    async def save(self, user_id: str, current_stage: int, stage_data: dict[str, Any]) -> None:
        data_json = json.dumps(stage_data, ensure_ascii=False)
        conn = self._db.conn()
        await conn.execute(
            """INSERT INTO conversation_states (user_id, current_stage, stage_data, updated_at)
               VALUES (?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(user_id) DO UPDATE SET
                 current_stage = excluded.current_stage,
                 stage_data = excluded.stage_data,
                 updated_at = CURRENT_TIMESTAMP""",
            (user_id, current_stage, data_json),
        )
        await conn.commit()

    async def load(self, user_id: str) -> dict[str, Any] | None:
        conn = self._db.conn()
        cursor = await conn.execute(
            "SELECT current_stage, stage_data FROM conversation_states WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return {"current_stage": row["current_stage"], "stage_data": json.loads(row["stage_data"])}


class KitRepo:
    """Repository for startup_kits table operations."""

    def __init__(self, db: Database) -> None:
        self._db = db

    async def create(self, user_id: str, knowledge_points: list[dict[str, Any]] | None = None) -> int:
        kp_json = json.dumps(knowledge_points or [], ensure_ascii=False)
        conn = self._db.conn()
        cursor = await conn.execute(
            "INSERT INTO startup_kits (user_id, knowledge_points) VALUES (?, ?)",
            (user_id, kp_json),
        )
        await conn.commit()
        return cursor.lastrowid

    async def load_by_user(self, user_id: str) -> dict[str, Any] | None:
        conn = self._db.conn()
        cursor = await conn.execute(
            "SELECT id, knowledge_points, product_package, content_direction, "
            "platform_recommendations, startup_materials, generation_status "
            "FROM startup_kits WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "knowledge_points": json.loads(row["knowledge_points"]),
            "product_package": json.loads(row["product_package"]) if row["product_package"] else None,
            "content_direction": row["content_direction"],
            "platform_recommendations": json.loads(row["platform_recommendations"]) if row["platform_recommendations"] else [],
            "startup_materials": json.loads(row["startup_materials"]) if row["startup_materials"] else {},
            "generation_status": row["generation_status"],
        }

    async def update_status(self, kit_id: int, status: str) -> None:
        conn = self._db.conn()
        await conn.execute(
            "UPDATE startup_kits SET generation_status = ? WHERE id = ?",
            (status, kit_id),
        )
        await conn.commit()

    ALLOWED_KIT_COLUMNS = frozenset({
        "product_package", "content_direction",
        "platform_recommendations", "startup_materials", "generation_status",
    })

    async def update_kit(self, kit_id: int, **fields: Any) -> None:
        invalid = set(fields) - self.ALLOWED_KIT_COLUMNS
        if invalid:
            raise ValueError(f"Invalid kit columns: {invalid}")
        sets: list[str] = []
        values: list[Any] = []
        for key, value in fields.items():
            sets.append(f"{key} = ?")
            values.append(
                json.dumps(value, ensure_ascii=False)
                if isinstance(value, (dict, list))
                else value
            )
        values.append(kit_id)
        conn = self._db.conn()
        await conn.execute(
            f"UPDATE startup_kits SET {', '.join(sets)} WHERE id = ?",
            values,
        )
        await conn.commit()
