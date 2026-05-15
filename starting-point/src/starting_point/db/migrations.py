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
            wx_openid TEXT UNIQUE,
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

        CREATE TABLE IF NOT EXISTS creator_examples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_name TEXT NOT NULL,
            douyin_id TEXT NOT NULL DEFAULT '',
            category TEXT NOT NULL,
            sub_category TEXT NOT NULL DEFAULT '',
            follower_tier TEXT NOT NULL DEFAULT '',
            monetization_methods TEXT NOT NULL DEFAULT '[]',
            origin_story TEXT NOT NULL DEFAULT '',
            user_profile_tags TEXT NOT NULL DEFAULT '[]',
            content_style TEXT NOT NULL DEFAULT '',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_creators_category ON creator_examples(category);

        -- Add platform and revenue_estimate columns to creator_examples (2026-05-15)
        """)
    # SQLite doesn't support IF NOT EXISTS for ALTER TABLE ADD COLUMN
    cursor = await conn.execute("PRAGMA table_info(creator_examples)")
    col_names = {row[1] for row in await cursor.fetchall()}
    if 'platform' not in col_names:
        await conn.execute("ALTER TABLE creator_examples ADD COLUMN platform TEXT NOT NULL DEFAULT ''")
    if 'revenue_estimate' not in col_names:
        await conn.execute("ALTER TABLE creator_examples ADD COLUMN revenue_estimate TEXT NOT NULL DEFAULT ''")
    await conn.executescript("""

        -- Fix: allow anonymous users (wx_openid can be NULL)
        -- SQLite doesn't support ALTER COLUMN, so recreate the table if needed
        """)
    # Check if wx_openid allows NULL
    cursor = await conn.execute("PRAGMA table_info(users)")
    columns = await cursor.fetchall()
    for col in columns:
        if col[1] == 'wx_openid' and col[3] == 1:  # col[3] = notnull
            # wx_openid is NOT NULL, need to recreate
            await conn.executescript("""
                CREATE TABLE users_new (
                    id TEXT PRIMARY KEY,
                    wx_openid TEXT UNIQUE,
                    wx_unionid TEXT NOT NULL DEFAULT '',
                    nickname TEXT NOT NULL DEFAULT '',
                    avatar_url TEXT NOT NULL DEFAULT '',
                    phone TEXT NOT NULL DEFAULT '',
                    tier TEXT NOT NULL DEFAULT 'free',
                    tier_expires_at DATETIME,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                INSERT OR IGNORE INTO users_new SELECT * FROM users;
                DROP TABLE users;
                ALTER TABLE users_new RENAME TO users;
                CREATE INDEX IF NOT EXISTS idx_users_wx_openid ON users(wx_openid);
            """)
            await conn.commit()
            break
    await conn.commit()
