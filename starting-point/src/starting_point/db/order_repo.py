from __future__ import annotations

import aiosqlite
from datetime import datetime

from starting_point.models import Order


class OrderRepo:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def save_order(self, order: Order) -> None:
        await self._db.execute(
            """INSERT OR REPLACE INTO orders
            (id, user_id, tier, amount, wx_prepay_id, wx_transaction_id, status, paid_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (order.id, order.user_id, order.tier, order.amount,
             order.wx_prepay_id, order.wx_transaction_id, order.status,
             order.paid_at, order.created_at),
        )
        await self._db.commit()

    async def get_order(self, order_id: str) -> Order | None:
        cursor = await self._db.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in cursor.description]
        return Order(**dict(zip(cols, row)))

    async def update_status(
        self, order_id: str, status: str, wx_transaction_id: str = "",
    ) -> None:
        paid_at = datetime.now().isoformat() if status == "paid" else None
        await self._db.execute(
            """UPDATE orders SET status = ?, wx_transaction_id = ?, paid_at = ?
            WHERE id = ?""",
            (status, wx_transaction_id, paid_at, order_id),
        )
        await self._db.commit()

    async def get_orders_by_user(self, user_id: str) -> list[Order]:
        cursor = await self._db.execute(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        rows = await cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        return [Order(**dict(zip(cols, row))) for row in rows]
