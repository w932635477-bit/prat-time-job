from __future__ import annotations

import aiosqlite

from starting_point.models import User


class UserRepo:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def save_user(self, user: User) -> None:
        await self._db.execute(
            """INSERT OR REPLACE INTO users
            (id, wx_openid, wx_unionid, nickname, avatar_url, phone, tier, tier_expires_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
            (user.id, user.wx_openid, user.wx_unionid, user.nickname,
             user.avatar_url, user.phone, user.tier, user.tier_expires_at),
        )
        await self._db.commit()

    async def get_user(self, user_id: str) -> User | None:
        cursor = await self._db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in cursor.description]
        data = dict(zip(cols, row))
        return User(**data)

    async def get_user_by_openid(self, wx_openid: str) -> User | None:
        cursor = await self._db.execute("SELECT * FROM users WHERE wx_openid = ?", (wx_openid,))
        row = await cursor.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in cursor.description]
        data = dict(zip(cols, row))
        return User(**data)

    async def delete_user(self, user_id: str) -> None:
        await self._db.execute("DELETE FROM user_profiles WHERE user_id = ?", (user_id,))
        await self._db.execute("DELETE FROM orders WHERE user_id = ?", (user_id,))
        await self._db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        await self._db.commit()
