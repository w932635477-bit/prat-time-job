from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_checkin_inserts_record(db):
    from starting_point.db.migrations import run_migrations

    await run_migrations(db)
    conn = db.conn()
    await conn.execute(
        "INSERT OR IGNORE INTO checkins (user_id, kit_id, platform, day) VALUES (?, ?, ?, ?)",
        ("u1", "kit1", "douyin", 1),
    )
    await conn.commit()

    cursor = await conn.execute("SELECT user_id, kit_id, platform, day FROM checkins")
    rows = await cursor.fetchall()
    assert len(rows) == 1
    row = rows[0]
    assert (row[0], row[1], row[2], row[3]) == ("u1", "kit1", "douyin", 1)


@pytest.mark.asyncio
async def test_checkin_duplicate_ignored(db):
    from starting_point.db.migrations import run_migrations

    await run_migrations(db)
    conn = db.conn()
    await conn.execute(
        "INSERT OR IGNORE INTO checkins (user_id, kit_id, platform, day) VALUES (?, ?, ?, ?)",
        ("u1", "kit1", "douyin", 1),
    )
    await conn.commit()
    await conn.execute(
        "INSERT OR IGNORE INTO checkins (user_id, kit_id, platform, day) VALUES (?, ?, ?, ?)",
        ("u1", "kit1", "douyin", 1),
    )
    await conn.commit()

    cursor = await conn.execute("SELECT COUNT(*) FROM checkins")
    count = (await cursor.fetchone())[0]
    assert count == 1


@pytest.mark.asyncio
async def test_checkin_different_days_allowed(db):
    from starting_point.db.migrations import run_migrations

    await run_migrations(db)
    conn = db.conn()
    for day in (1, 2, 3):
        await conn.execute(
            "INSERT OR IGNORE INTO checkins (user_id, kit_id, platform, day) VALUES (?, ?, ?, ?)",
            ("u1", "kit1", "douyin", day),
        )
    await conn.commit()

    cursor = await conn.execute("SELECT COUNT(*) FROM checkins")
    count = (await cursor.fetchone())[0]
    assert count == 3
