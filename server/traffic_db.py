"""
SQLite 流量持久化
数据库路径：server/data/traffic.db
- traffic       : 每台设备的累计总量
- traffic_daily : 按日粒度的增量，用于今日/本月/本年统计
"""
import logging
import time
from datetime import datetime
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
        await db.execute("""
            CREATE TABLE IF NOT EXISTS traffic_daily (
                client_id       TEXT    NOT NULL,
                date            TEXT    NOT NULL,
                bytes_in        INTEGER NOT NULL DEFAULT 0,
                bytes_out       INTEGER NOT NULL DEFAULT 0,
                http_requests   INTEGER NOT NULL DEFAULT 0,
                tcp_connections INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (client_id, date)
            )
        """)
        await db.commit()
    logger.info(f"Traffic DB ready: {DB_PATH}")


async def flush_to_db(pending: dict[str, dict]) -> None:
    """将内存增量批量 upsert 进累计表和日粒度表。"""
    if not pending:
        return
    today = datetime.now().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_PATH) as db:
        for client_id, d in pending.items():
            bi  = d.get("bytes_in", 0)
            bo  = d.get("bytes_out", 0)
            hr  = d.get("http_requests", 0)
            tc  = d.get("tcp_connections", 0)
            la  = d.get("last_active", time.time())

            # 累计总量
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
            """, (client_id, bi, bo, hr, tc, la))

            # 日粒度增量
            await db.execute("""
                INSERT INTO traffic_daily
                    (client_id, date, bytes_in, bytes_out, http_requests, tcp_connections)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(client_id, date) DO UPDATE SET
                    bytes_in        = bytes_in        + excluded.bytes_in,
                    bytes_out       = bytes_out       + excluded.bytes_out,
                    http_requests   = http_requests   + excluded.http_requests,
                    tcp_connections = tcp_connections + excluded.tcp_connections
            """, (client_id, today, bi, bo, hr, tc))

        await db.commit()


async def query_all() -> list[dict]:
    """查询所有设备的流量记录，按最近活跃时间倒序。"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM traffic ORDER BY last_active DESC"
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def query_client_detail(client_id: str) -> dict:
    """返回指定设备的今日/本月/本年流量及近 30 天明细。"""
    now        = datetime.now()
    today      = now.strftime("%Y-%m-%d")
    this_month = now.strftime("%Y-%m")
    this_year  = now.strftime("%Y")

    def _clean(row) -> dict:
        if not row:
            return {"bytes_in": 0, "bytes_out": 0, "http_requests": 0, "tcp_connections": 0}
        return {
            "bytes_in":        row["bytes_in"]        or 0,
            "bytes_out":       row["bytes_out"]        or 0,
            "http_requests":   row["http_requests"]    or 0,
            "tcp_connections": row["tcp_connections"]  or 0,
        }

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # 累计总量
        async with db.execute(
            "SELECT * FROM traffic WHERE client_id = ?", (client_id,)
        ) as cur:
            total_row = await cur.fetchone()

        # 今日
        async with db.execute(
            "SELECT bytes_in, bytes_out, http_requests, tcp_connections "
            "FROM traffic_daily WHERE client_id = ? AND date = ?",
            (client_id, today)
        ) as cur:
            today_row = await cur.fetchone()

        # 本月
        async with db.execute(
            "SELECT SUM(bytes_in) bytes_in, SUM(bytes_out) bytes_out, "
            "       SUM(http_requests) http_requests, SUM(tcp_connections) tcp_connections "
            "FROM traffic_daily WHERE client_id = ? AND date LIKE ?",
            (client_id, f"{this_month}-%")
        ) as cur:
            month_row = await cur.fetchone()

        # 本年
        async with db.execute(
            "SELECT SUM(bytes_in) bytes_in, SUM(bytes_out) bytes_out, "
            "       SUM(http_requests) http_requests, SUM(tcp_connections) tcp_connections "
            "FROM traffic_daily WHERE client_id = ? AND date LIKE ?",
            (client_id, f"{this_year}-%")
        ) as cur:
            year_row = await cur.fetchone()

        # 近 30 天明细
        async with db.execute(
            "SELECT date, bytes_in, bytes_out, http_requests, tcp_connections "
            "FROM traffic_daily WHERE client_id = ? "
            "ORDER BY date DESC LIMIT 30",
            (client_id,)
        ) as cur:
            daily_rows = await cur.fetchall()

    return {
        "client_id": client_id,
        "total":     _clean(total_row),
        "today":     _clean(today_row),
        "month":     _clean(month_row),
        "year":      _clean(year_row),
        "daily":     [dict(r) for r in daily_rows],
    }
