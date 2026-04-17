"""
Central configuration — loads from .env and exposes typed settings.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── eBay API ──────────────────────────────────────────────
EBAY_APP_ID     = os.getenv("EBAY_APP_ID", "")
EBAY_CERT_ID    = os.getenv("EBAY_CERT_ID", "")
EBAY_DEV_ID     = os.getenv("EBAY_DEV_ID", "")
EBAY_USER_TOKEN = os.getenv("EBAY_USER_TOKEN", "")

EBAY_FINDING_API_URL = "https://svcs.ebay.com/services/search/FindingService/v1"
EBAY_BROWSE_API_URL  = "https://api.ebay.com/buy/browse/v1"

# ── Telegram ──────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")

# ── Deal logic ────────────────────────────────────────────
DEAL_DISCOUNT_THRESHOLD = float(os.getenv("DEAL_DISCOUNT_THRESHOLD", "0.10"))
FIRE_DEAL_THRESHOLD     = float(os.getenv("FIRE_DEAL_THRESHOLD", "0.25"))
FMV_LOOKBACK_DAYS       = int(os.getenv("FMV_LOOKBACK_DAYS", "90"))
MIN_SOLD_COMPS          = 3     # minimum sold comps needed to trust FMV

# ── Scheduler ─────────────────────────────────────────────
SCOUT_INTERVAL_MINUTES = int(os.getenv("SCOUT_INTERVAL_MINUTES", "5"))

# ── Storage ───────────────────────────────────────────────
DB_PATH        = os.getenv("DB_PATH", "data/psa10_scout.db")
WATCHLIST_PATH = "data/watchlist.json"
LOG_LEVEL      = os.getenv("LOG_LEVEL", "INFO")
