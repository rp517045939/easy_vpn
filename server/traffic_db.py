"""
SQLite 流量持久化
数据库路径：server/data/traffic.db
累计存储每台设备的流量（重置需手动清库）
"""
import logging
import time
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)
DB_PATH = Path(__file__).parent / "data" / "traffic.db"


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS traffic (
                client_id       TEXT    PRIMARY KEY,
                bytes_in        INTEGER NOT NULL DEFAULT 0,
                bytes_out       INTEGER NOT NULL DEFAULT 0,
                http_requests   INTEGER NOT NULL DEFAULT 0,
                tcp_connections INTEGER NOT NULL DEFAULT 0,
                last_active     REAL    NOT NULL DEFAULT 0
            )
        """)
        await db.commit()
    logger.info(f"Traffic DB ready: {DB_PATH}")


async def flush_to_db(pending: dict[str, dict]) -> None:
    """将内存增量批量 upsert 进数据库。"""
    if not pending:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        for client_id, d in pending.items():
            await db.execute("""
                INSERT INTO traffic
                    (client_id, bytes_in, bytes_out, http_requests, tcp_connections, last_active)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(client_id) DO UPDATE SET
                    bytes_in        = bytes_in        + excluded.bytes_in,
                    bytes_out       = bytes_out       + excluded.bytes_out,
                    http_requests   = http_requests   + excluded.http_requests,
                    tcp_connections = tcp_connections + excluded.tcp_connections,
                    last_active     = excluded.last_active
            """, (
                client_id,
                d.get("bytes_in", 0),
                d.get("bytes_out", 0),
                d.get("http_requests", 0),
                d.get("tcp_connections", 0),
                d.get("last_active", time.time()),
            ))
        await db.commit()


async def query_all() -> list[dict]:
    """查询所有设备的流量记录，按最近活跃时间倒序。"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM traffic ORDER BY last_active DESC"
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]
