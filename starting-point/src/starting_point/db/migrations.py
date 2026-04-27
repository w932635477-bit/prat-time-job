from __future__ import annotations

import aiosqlite


async def run_migrations(db: aiosqlite.Connection) -> None:
    await db.executescript("""
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

        CREATE INDEX IF NOT EXISTS idx_users_wx_openid ON users(wx_openid);
        CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
        CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
    """)
    await db.commit()
