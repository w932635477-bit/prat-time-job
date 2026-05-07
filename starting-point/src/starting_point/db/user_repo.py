from __future__ import annotations

import aiosqlite

from starting_point.models import User


def _conn(db: object) -> aiosqlite.Connection:
    if hasattr(db, 'conn') and callable(db.conn):
        return db.conn()
    return db


class UserRepo:
    def __init__(self, db: object) -> None:
        self._db = db

    async def save_user(self, user: User) -> None:
        conn = _conn(self._db)
        await conn.execute(
            """INSERT INTO users
            (id, wx_openid, wx_unionid, nickname, avatar_url, phone, tier, tier_expires_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            ON CONFLICT(id) DO UPDATE SET
                wx_openid = excluded.wx_openid,
                wx_unionid = excluded.wx_unionid,
                nickname = excluded.nickname,
                avatar_url = excluded.avatar_url,
                phone = excluded.phone,
                tier = excluded.tier,
                tier_expires_at = excluded.tier_expires_at,
                updated_at = datetime('now')""",
            (user.id, user.wx_openid, user.wx_unionid, user.nickname,
             user.avatar_url, user.phone, user.tier, user.tier_expires_at),
        )
        await conn.commit()

    async def get_user(self, user_id: str) -> User | None:
        conn = _conn(self._db)
        cursor = await conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in cursor.description]
        return User(**dict(zip(cols, row)))

    async def get_user_by_openid(self, wx_openid: str) -> User | None:
        conn = _conn(self._db)
        cursor = await conn.execute("SELECT * FROM users WHERE wx_openid = ?", (wx_openid,))
        row = await cursor.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in cursor.description]
        return User(**dict(zip(cols, row)))

    async def delete_user(self, user_id: str) -> None:
        conn = _conn(self._db)
        await conn.execute("DELETE FROM user_profiles WHERE user_id = ?", (user_id,))
        await conn.execute("DELETE FROM orders WHERE user_id = ?", (user_id,))
        await conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        await conn.commit()

    async def count_users(self) -> int:
        conn = _conn(self._db)
        cursor = await conn.execute("SELECT COUNT(*) FROM users")
        row = await cursor.fetchone()
        return row[0]

    async def list_users(self, page: int = 1, size: int = 20, search: str = "") -> list[User]:
        conn = _conn(self._db)
        offset = (page - 1) * size
        if search:
            cursor = await conn.execute(
                "SELECT * FROM users WHERE nickname LIKE ? OR phone LIKE ? "
                "ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (f"%{search}%", f"%{search}%", size, offset),
            )
        else:
            cursor = await conn.execute(
                "SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (size, offset),
            )
        rows = await cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        return [User(**dict(zip(cols, row))) for row in rows]

    async def count_today_new(self) -> int:
        conn = _conn(self._db)
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM users WHERE created_at >= date('now')"
        )
        row = await cursor.fetchone()
        return row[0]

    async def count_paid_users(self) -> int:
        conn = _conn(self._db)
        cursor = await conn.execute(
            "SELECT COUNT(DISTINCT user_id) FROM orders WHERE status = 'paid'"
        )
        row = await cursor.fetchone()
        return row[0]
