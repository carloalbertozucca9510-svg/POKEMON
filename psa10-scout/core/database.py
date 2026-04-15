"""
SQLite persistence layer — schema creation and CRUD helpers.
"""
import sqlite3
from pathlib import Path
from loguru import logger
from core.config import DB_PATH


def get_conn() -> sqlite3.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sold_comps (
                item_id     TEXT PRIMARY KEY,
                card_name   TEXT NOT NULL,
                psa_grade   INTEGER NOT NULL,
                sale_price  REAL NOT NULL,
                sale_date   TEXT NOT NULL,
                source      TEXT DEFAULT 'ebay',
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS fmv_cache (
                card_key     TEXT PRIMARY KEY,
                card_name    TEXT NOT NULL,
                fmv_30d      REAL,
                fmv_90d      REAL,
                comp_count   INTEGER DEFAULT 0,
                last_updated TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS listings (
                item_id      TEXT PRIMARY KEY,
                card_name    TEXT NOT NULL,
                psa_grade    INTEGER NOT NULL,
                ask_price    REAL NOT NULL,
                listing_url  TEXT NOT NULL,
                source       TEXT NOT NULL,
                listed_at    TEXT NOT NULL,
                image_url    TEXT DEFAULT '',
                seller       TEXT DEFAULT '',
                created_at   TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS deals (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id      TEXT NOT NULL,
                card_name    TEXT NOT NULL,
                ask_price    REAL NOT NULL,
                fmv_90d      REAL NOT NULL,
                discount_pct REAL NOT NULL,
                deal_score   INTEGER NOT NULL,
                is_fire_deal INTEGER DEFAULT 0,
                listing_url  TEXT NOT NULL,
                alerted      INTEGER DEFAULT 0,
                found_at     TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_deals_score ON deals(deal_score DESC);
            CREATE INDEX IF NOT EXISTS idx_deals_found ON deals(found_at DESC);
            CREATE INDEX IF NOT EXISTS idx_comps_card  ON sold_comps(card_name);
            CREATE INDEX IF NOT EXISTS idx_comps_date  ON sold_comps(sale_date DESC);
        """)
    logger.info("Database initialised at {}", DB_PATH)


def upsert_fmv(card_key: str, card_name: str, fmv_30d, fmv_90d, comp_count: int):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO fmv_cache (card_key, card_name, fmv_30d, fmv_90d, comp_count, last_updated)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(card_key) DO UPDATE SET
                fmv_30d=excluded.fmv_30d,
                fmv_90d=excluded.fmv_90d,
                comp_count=excluded.comp_count,
                last_updated=excluded.last_updated
        """, (card_key, card_name, fmv_30d, fmv_90d, comp_count))


def get_fmv(card_key: str):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM fmv_cache WHERE card_key = ?", (card_key,)
        ).fetchone()


def insert_deal(deal_data: dict):
    with get_conn() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO deals
            (item_id, card_name, ask_price, fmv_90d, discount_pct, deal_score, is_fire_deal, listing_url)
            VALUES (:item_id, :card_name, :ask_price, :fmv_90d, :discount_pct, :deal_score, :is_fire_deal, :listing_url)
        """, deal_data)


def get_recent_deals(limit: int = 50):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM deals ORDER BY found_at DESC, deal_score DESC LIMIT ?", (limit,)
        ).fetchall()


def mark_alerted(deal_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE deals SET alerted = 1 WHERE id = ?", (deal_id,))
