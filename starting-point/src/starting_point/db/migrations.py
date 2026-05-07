from __future__ import annotations

import aiosqlite


def _conn(db: object) -> aiosqlite.Connection:
    if hasattr(db, 'conn') and callable(db.conn):
        return db.conn()
    return db


async def run_migrations(db: object) -> None:
    conn = _conn(db)
    await conn.executescript("""
        CREATE TABLE IF NOT EXISTS user_states (
            user_id TEXT PRIMARY KEY,
            data TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            wx_openid TEXT UNIQUE NOT NULL,
            wx_unionid TEXT NOT NULL DEFAULT '',
            nickname TEXT NOT NULL DEFAULT '',
            avatar_url TEXT NOT NULL DEFAULT '',
            phone TEXT NOT NULL DEFAULT '',
            tier TEXT NOT NULL DEFAULT 'free',
            tier_expires_at DATETIME,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id),
            tier TEXT NOT NULL,
            amount INTEGER NOT NULL,
            wx_prepay_id TEXT NOT NULL DEFAULT '',
            wx_transaction_id TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            paid_at DATETIME,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id TEXT PRIMARY KEY REFERENCES users(id),
            industry TEXT NOT NULL DEFAULT '',
            years_experience INTEGER NOT NULL DEFAULT 0,
            goals TEXT NOT NULL DEFAULT '',
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL REFERENCES users(id),
            rating INTEGER CHECK(rating BETWEEN 1 AND 5),
            content TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'new',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            event_data TEXT NOT NULL DEFAULT '{}',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_users_wx_openid ON users(wx_openid);
        CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
        CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
        CREATE INDEX IF NOT EXISTS idx_events_user_id ON events(user_id);
        CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
        CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at);
        CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON feedback(user_id);

        -- Migrate legacy low_ticket tier to standard
        UPDATE users SET tier = 'standard' WHERE tier = 'low_ticket';
        UPDATE orders SET tier = 'standard' WHERE tier = 'low_ticket';
    """)
    await conn.commit()
