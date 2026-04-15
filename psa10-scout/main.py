"""
Main runner — schedules all agents on their configured intervals.

Usage:
  python main.py

Runs one full cycle immediately on startup, then continues on the
SCOUT_INTERVAL_MINUTES schedule defined in .env.
"""
import schedule
import time
from loguru import logger
from core.config import SCOUT_INTERVAL_MINUTES, LOG_LEVEL
from core.database import init_db, get_recent_deals
from agents.price_oracle import run_price_oracle
from agents.listing_scout import run_listing_scout
from alerts.telegram_bot import send_daily_summary
from datetime import datetime


def run_all():
    logger.info("=== Scout cycle starting — {} ===", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))
    run_price_oracle()
    run_listing_scout()
    logger.info("=== Scout cycle complete ===")


def run_daily_summary():
    deals = [dict(r) for r in get_recent_deals(limit=100)]
    today = [d for d in deals if d["found_at"][:10] == datetime.utcnow().strftime("%Y-%m-%d")]
    send_daily_summary(today)
    logger.info("Daily summary sent ({} deals today)", len(today))


if __name__ == "__main__":
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        level=LOG_LEVEL,
        colorize=True,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}"
    )
    logger.add(
        "logs/scout.log",
        rotation="10 MB",
        retention="30 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}"
    )

    init_db()
    logger.info("PSA 10 Scout started — scanning every {}m", SCOUT_INTERVAL_MINUTES)

    run_all()  # run immediately on start

    schedule.every(SCOUT_INTERVAL_MINUTES).minutes.do(run_all)
    schedule.every().day.at("09:00").do(run_daily_summary)

    while True:
        schedule.run_pending()
        time.sleep(30)
