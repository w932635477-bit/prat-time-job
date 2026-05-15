from __future__ import annotations

import json
import logging

import aiosqlite

from starting_point.models import CreatorExample

logger = logging.getLogger(__name__)


class CreatorRepo:
    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def find_by_category(
        self,
        category: str,
        exclude_ids: list[int] | None = None,
        limit: int = 3,
    ) -> list[CreatorExample]:
        exclude = exclude_ids or []
        exclude_clause = f"AND id NOT IN ({','.join(str(i) for i in exclude)})" if exclude else ""
        cursor = await self._conn.execute(
            f"""SELECT * FROM creator_examples
                WHERE category = ? AND is_active = 1 {exclude_clause}
                ORDER BY RANDOM() LIMIT ?""",
            (category, limit),
        )
        rows = await cursor.fetchall()
        return [self._row_to_model(row) for row in rows]

    async def find_by_tags(
        self,
        tags: list[str],
        exclude_ids: list[int] | None = None,
        limit: int = 3,
    ) -> list[CreatorExample]:
        if not tags:
            return []
        conditions = []
        params: list[str] = []
        for tag in tags:
            conditions.append("user_profile_tags LIKE ?")
            params.append(f"%{tag}%")
        where = " OR ".join(conditions)
        exclude = exclude_ids or []
        exclude_clause = f"AND id NOT IN ({','.join(str(i) for i in exclude)})" if exclude else ""
        params.append(limit)
        cursor = await self._conn.execute(
            f"""SELECT * FROM creator_examples
                WHERE ({where}) AND is_active = 1 {exclude_clause}
                ORDER BY RANDOM() LIMIT ?""",
            params,
        )
        rows = await cursor.fetchall()
        return [self._row_to_model(row) for row in rows]

    async def search(
        self,
        keyword: str,
        exclude_ids: list[int] | None = None,
        limit: int = 3,
    ) -> list[CreatorExample]:
        exclude = exclude_ids or []
        exclude_clause = f"AND id NOT IN ({','.join(str(i) for i in exclude)})" if exclude else ""
        cursor = await self._conn.execute(
            f"""SELECT * FROM creator_examples
                WHERE (category LIKE ? OR sub_category LIKE ?
                       OR user_profile_tags LIKE ?)
                      AND is_active = 1 {exclude_clause}
                ORDER BY RANDOM() LIMIT ?""",
            (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", limit),
        )
        rows = await cursor.fetchall()
        return [self._row_to_model(row) for row in rows]

    async def load_seed_data(self, sql_path: str) -> int:
        with open(sql_path) as f:
            sql = f.read()
        await self._conn.executescript(sql)
        await self._conn.commit()
        cursor = await self._conn.execute("SELECT COUNT(*) FROM creator_examples")
        row = await cursor.fetchone()
        return row[0] if row else 0

    def _row_to_model(self, row: aiosqlite.Row) -> CreatorExample:
        return CreatorExample(
            id=row["id"],
            account_name=row["account_name"],
            douyin_id=row["douyin_id"],
            category=row["category"],
            sub_category=row["sub_category"],
            follower_tier=row["follower_tier"],
            monetization_methods=json.loads(row["monetization_methods"]),
            origin_story=row["origin_story"],
            user_profile_tags=json.loads(row["user_profile_tags"]),
            content_style=row["content_style"],
            platform=row["platform"] if "platform" in row.keys() else "",
            revenue_estimate=row["revenue_estimate"] if "revenue_estimate" in row.keys() else "",
            is_active=bool(row["is_active"]),
        )
