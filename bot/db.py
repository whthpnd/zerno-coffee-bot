import json
from pathlib import Path

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    username   TEXT,
    items      TEXT    NOT NULL,
    total      INTEGER NOT NULL,
    pickup     TEXT    NOT NULL,
    comment    TEXT,
    status     TEXT    NOT NULL DEFAULT 'new',
    created_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""


class Database:
    def __init__(self, path: str):
        self.path = path

    async def init(self) -> None:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.path) as db:
            await db.execute(SCHEMA)
            await db.commit()

    async def create_order(
        self,
        user_id: int,
        username: str | None,
        items: list[dict],
        total: int,
        pickup: str,
        comment: str | None,
    ) -> int:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "INSERT INTO orders (user_id, username, items, total, pickup, comment) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, username, json.dumps(items, ensure_ascii=False), total, pickup, comment),
            )
            await db.commit()
            return cursor.lastrowid

    async def get_order(self, order_id: int) -> dict | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
            row = await cursor.fetchone()
        if row is None:
            return None
        order = dict(row)
        order["items"] = json.loads(order["items"])
        return order

    async def set_status(self, order_id: int, status: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
            await db.commit()
