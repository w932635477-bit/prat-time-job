from __future__ import annotations

import json

from starting_point.db.database import Database


def _c(db: Database):
    return db.conn()


async def get_dashboard_stats(db: Database) -> dict:
    conn = _c(db)

    cursor = await conn.execute("SELECT COUNT(*) FROM users")
    total_users = (await cursor.fetchone())[0]

    cursor = await conn.execute(
        "SELECT COUNT(*) FROM users WHERE created_at >= date('now')"
    )
    today_new = (await cursor.fetchone())[0]

    cursor = await conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM orders WHERE status = 'paid'"
    )
    total_revenue = (await cursor.fetchone())[0]

    cursor = await conn.execute(
        "SELECT COUNT(DISTINCT user_id) FROM orders WHERE status = 'paid'"
    )
    paid_users = (await cursor.fetchone())[0]

    cursor = await conn.execute("SELECT COUNT(*) FROM orders WHERE status = 'pending'")
    pending_orders = (await cursor.fetchone())[0]

    cursor = await conn.execute(
        "SELECT COUNT(*) FROM orders WHERE status = 'paid' AND paid_at >= date('now')"
    )
    today_orders = (await cursor.fetchone())[0]

    cursor = await conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM orders WHERE status = 'paid' AND paid_at >= date('now')"
    )
    today_revenue = (await cursor.fetchone())[0]

    return {
        "total_users": total_users,
        "today_new": today_new,
        "total_revenue": total_revenue,
        "paid_users": paid_users,
        "pending_orders": pending_orders,
        "today_orders": today_orders,
        "today_revenue": today_revenue,
    }


async def get_recent_messages(db: Database, limit: int = 50) -> list[dict]:
    conn = _c(db)
    cursor = await conn.execute(
        """SELECT m.id, m.user_id, m.role, m.content, m.stage, m.created_at, u.nickname
        FROM messages m LEFT JOIN users u ON m.user_id = u.id
        ORDER BY m.created_at DESC LIMIT ?""",
        (limit,),
    )
    rows = await cursor.fetchall()
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in rows]


async def get_feedback_list(db: Database, page: int = 1, size: int = 20) -> dict:
    conn = _c(db)
    offset = (page - 1) * size

    cursor = await conn.execute("SELECT COUNT(*) FROM feedback")
    total = (await cursor.fetchone())[0]

    cursor = await conn.execute(
        """SELECT f.id, f.user_id, f.rating, f.content, f.status, f.created_at, u.nickname
        FROM feedback f LEFT JOIN users u ON f.user_id = u.id
        ORDER BY f.created_at DESC LIMIT ? OFFSET ?""",
        (size, offset),
    )
    rows = await cursor.fetchall()
    cols = [d[0] for d in cursor.description]
    items = [dict(zip(cols, row)) for row in rows]

    return {"total": total, "page": page, "size": size, "items": items}


async def get_retention_data(db: Database) -> list[dict]:
    conn = _c(db)
    cursor = await conn.execute(
        """SELECT
            date(u.created_at) as cohort_date,
            COUNT(DISTINCT u.id) as cohort_size,
            COUNT(DISTINCT CASE WHEN e.event_type = 'chat_message'
                AND date(e.created_at) <= date(u.created_at, '+7 days') THEN u.id END) as d7_active,
            COUNT(DISTINCT CASE WHEN e.event_type = 'chat_message'
                AND date(e.created_at) <= date(u.created_at, '+30 days') THEN u.id END) as d30_active
        FROM users u
        LEFT JOIN events e ON e.user_id = u.id AND e.event_type = 'chat_message'
        GROUP BY date(u.created_at)
        ORDER BY cohort_date DESC LIMIT 30"""
    )
    rows = await cursor.fetchall()
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in rows]
