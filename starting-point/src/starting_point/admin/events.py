from __future__ import annotations

import json

from starting_point.db.database import Database


def _c(db: Database):
    return db.conn()


async def track_event(db: Database, user_id: str, event_type: str, data: dict | None = None) -> None:
    conn = _c(db)
    await conn.execute(
        "INSERT INTO events (user_id, event_type, event_data) VALUES (?, ?, ?)",
        (user_id, event_type, json.dumps(data or {}, ensure_ascii=False)),
    )
    await conn.commit()


async def get_event_counts(db: Database, event_type: str, days: int = 30) -> list[dict]:
    conn = _c(db)
    cursor = await conn.execute(
        """SELECT date(created_at) as day, COUNT(*) as count
        FROM events WHERE event_type = ?
        AND created_at >= datetime('now', ? || ' days')
        GROUP BY date(created_at) ORDER BY day""",
        (event_type, f"-{days}"),
    )
    rows = await cursor.fetchall()
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in rows]


async def get_conversion_funnel(db: Database) -> dict:
    conn = _c(db)
    cursor = await conn.execute("SELECT COUNT(*) FROM events WHERE event_type = 'login'")
    logins = (await cursor.fetchone())[0]

    cursor = await conn.execute("SELECT COUNT(*) FROM events WHERE event_type = 'chat_message'")
    chats = (await cursor.fetchone())[0]

    cursor = await conn.execute("SELECT COUNT(*) FROM events WHERE event_type = 'payment_create'")
    payment_attempts = (await cursor.fetchone())[0]

    cursor = await conn.execute("SELECT COUNT(*) FROM events WHERE event_type = 'payment_complete'")
    payment_complete = (await cursor.fetchone())[0]

    return {
        "logins": logins,
        "chats": chats,
        "payment_attempts": payment_attempts,
        "payment_complete": payment_complete,
    }
