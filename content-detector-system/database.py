"""
Async SQLite database layer.
Uses aiosqlite — zero infrastructure, file-based, async-compatible.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

logger = logging.getLogger("database")

_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "detector.db")


class ConnectionContext:
    def __init__(self):
        os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
        self.conn = aiosqlite.connect(_DB_PATH)
    
    async def __aenter__(self):
        db = await self.conn.__aenter__()
        db.row_factory = aiosqlite.Row
        return db
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.conn.__aexit__(exc_type, exc_val, exc_tb)


async def get_db():
    return ConnectionContext()


async def init_db() -> None:
    """Create tables if they don't exist."""
    async with await get_db() as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS analyses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                text_hash   TEXT NOT NULL,
                text        TEXT NOT NULL,
                source_url  TEXT,
                platform    TEXT,
                classification TEXT NOT NULL,
                confidence  REAL NOT NULL,
                risk_score  REAL NOT NULL,
                reasoning   TEXT NOT NULL,
                flags       TEXT NOT NULL,
                created_at  TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_analyses_hash ON analyses(text_hash);
            CREATE INDEX IF NOT EXISTS idx_analyses_created ON analyses(created_at);

            CREATE TABLE IF NOT EXISTS review_queue (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_id     INTEGER NOT NULL REFERENCES analyses(id),
                status          TEXT NOT NULL DEFAULT 'pending',
                reviewer        TEXT,
                reviewer_verdict TEXT,
                reviewer_notes  TEXT,
                submitted_at    TEXT NOT NULL,
                reviewed_at     TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_queue_status ON review_queue(status);

            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT UNIQUE NOT NULL,
                hashed_pw   TEXT NOT NULL,
                role        TEXT NOT NULL DEFAULT 'analyst',
                created_at  TEXT NOT NULL
            );
        """)
        await db.commit()
    logger.info("Database initialised at %s", _DB_PATH)


# ---- analyses ----

async def save_analysis(text: str, source_url: Optional[str], platform: str, result: dict) -> int:
    import hashlib
    text_hash = hashlib.sha256(text.encode()).hexdigest()
    now = datetime.now(timezone.utc).isoformat()
    async with await get_db() as db:
        cursor = await db.execute(
            """INSERT INTO analyses
               (text_hash, text, source_url, platform, classification, confidence,
                risk_score, reasoning, flags, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                text_hash, text[:2000], source_url, platform,
                result["classification"], result["confidence"], result["risk_score"],
                json.dumps(result.get("reasoning", {})),
                json.dumps(result.get("flags", [])),
                now,
            ),
        )
        await db.commit()
        return cursor.lastrowid


async def get_recent_analyses(limit: int = 20) -> list:
    async with await get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM analyses ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_stats() -> dict:
    async with await get_db() as db:
        total = (await (await db.execute("SELECT COUNT(*) FROM analyses")).fetchone())[0]
        by_class = await (await db.execute(
            "SELECT classification, COUNT(*) as cnt FROM analyses GROUP BY classification"
        )).fetchall()
        avg_risk = (await (await db.execute(
            "SELECT AVG(risk_score) FROM analyses"
        )).fetchone())[0] or 0.0
        pending_reviews = (await (await db.execute(
            "SELECT COUNT(*) FROM review_queue WHERE status='pending'"
        )).fetchone())[0]
    return {
        "total_analyses": total,
        "by_classification": {r["classification"]: r["cnt"] for r in by_class},
        "avg_risk_score": round(avg_risk, 2),
        "pending_reviews": pending_reviews,
    }


# ---- review queue ----

async def submit_for_review(analysis_id: int) -> int:
    now = datetime.now(timezone.utc).isoformat()
    async with await get_db() as db:
        cursor = await db.execute(
            "INSERT INTO review_queue (analysis_id, submitted_at) VALUES (?,?)",
            (analysis_id, now),
        )
        await db.commit()
        return cursor.lastrowid


async def get_review_queue(status: str = "pending") -> list:
    async with await get_db() as db:
        cursor = await db.execute(
            """SELECT rq.*, a.text, a.classification, a.confidence, a.risk_score
               FROM review_queue rq JOIN analyses a ON rq.analysis_id = a.id
               WHERE rq.status = ? ORDER BY rq.submitted_at ASC""",
            (status,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def update_review(review_id: int, reviewer: str, verdict: str, notes: str) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    async with await get_db() as db:
        result = await db.execute(
            """UPDATE review_queue
               SET status='reviewed', reviewer=?, reviewer_verdict=?,
                   reviewer_notes=?, reviewed_at=?
               WHERE id=? AND status='pending'""",
            (reviewer, verdict, notes, now, review_id),
        )
        await db.commit()
        return result.rowcount > 0


# ---- users ----

async def create_user(username: str, hashed_pw: str, role: str = "analyst") -> int:
    now = datetime.now(timezone.utc).isoformat()
    async with await get_db() as db:
        cursor = await db.execute(
            "INSERT INTO users (username, hashed_pw, role, created_at) VALUES (?,?,?,?)",
            (username, hashed_pw, role, now),
        )
        await db.commit()
        return cursor.lastrowid


async def get_user(username: str) -> Optional[dict]:
    async with await get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM users WHERE username=?", (username,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
