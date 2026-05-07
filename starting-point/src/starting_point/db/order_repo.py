from __future__ import annotations

from datetime import datetime

import aiosqlite

from starting_point.models import Order


def _conn(db: object) -> aiosqlite.Connection:
    if hasattr(db, 'conn') and callable(db.conn):
        return db.conn()
    return db


class OrderRepo:
    def __init__(self, db: object) -> None:
        self._db = db

    async def save_order(self, order: Order) -> None:
        conn = _conn(self._db)
        await conn.execute(
            """INSERT INTO orders
            (id, user_id, tier, amount, wx_prepay_id, wx_transaction_id, status, paid_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(id) DO UPDATE SET
                wx_prepay_id = excluded.wx_prepay_id,
                wx_transaction_id = excluded.wx_transaction_id,
                status = excluded.status,
                paid_at = CASE WHEN excluded.status = 'paid' AND paid_at IS NULL
                    THEN datetime('now') ELSE paid_at END""",
            (order.id, order.user_id, order.tier, order.amount,
             order.wx_prepay_id, order.wx_transaction_id, order.status,
             order.paid_at),
        )
        await conn.commit()

    async def get_order(self, order_id: str) -> Order | None:
        conn = _conn(self._db)
        cursor = await conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in cursor.description]
        return Order(**dict(zip(cols, row)))

    async def update_status(
        self, order_id: str, status: str, wx_transaction_id: str = "",
    ) -> None:
        paid_at = datetime.now().isoformat() if status == "paid" else None
        conn = _conn(self._db)
        await conn.execute(
            """UPDATE orders SET status = ?, wx_transaction_id = ?, paid_at = ?
            WHERE id = ?""",
            (status, wx_transaction_id, paid_at, order_id),
        )
        await conn.commit()

    async def get_orders_by_user(self, user_id: str) -> list[Order]:
        conn = _conn(self._db)
        cursor = await conn.execute(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        rows = await cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        return [Order(**dict(zip(cols, row))) for row in rows]

    async def list_orders(self, page: int = 1, size: int = 20, status: str = "") -> list[Order]:
        conn = _conn(self._db)
        offset = (page - 1) * size
        if status:
            cursor = await conn.execute(
                "SELECT * FROM orders WHERE status = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (status, size, offset),
            )
        else:
            cursor = await conn.execute(
                "SELECT * FROM orders ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (size, offset),
            )
        rows = await cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        return [Order(**dict(zip(cols, row))) for row in rows]

    async def count_orders(self, status: str = "") -> int:
        conn = _conn(self._db)
        if status:
            cursor = await conn.execute("SELECT COUNT(*) FROM orders WHERE status = ?", (status,))
        else:
            cursor = await conn.execute("SELECT COUNT(*) FROM orders")
        row = await cursor.fetchone()
        return row[0]

    async def total_revenue(self) -> int:
        conn = _conn(self._db)
        cursor = await conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM orders WHERE status = 'paid'"
        )
        row = await cursor.fetchone()
        return row[0]

    async def revenue_by_day(self, days: int = 30) -> list[dict]:
        conn = _conn(self._db)
        cursor = await conn.execute(
            """SELECT date(paid_at) as day, SUM(amount) as revenue, COUNT(*) as count
            FROM orders WHERE status = 'paid'
            AND paid_at >= datetime('now', ? || ' days')
            GROUP BY date(paid_at) ORDER BY day""",
            (f"-{days}",),
        )
        rows = await cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in rows]
