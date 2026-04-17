"""
Price Oracle — estimates FMV for PSA 10 cards using eBay Browse API.

Uses the median of the lowest active asking prices as an FMV proxy,
since findCompletedItems is restricted for our account type.
"""
import requests
import time
import statistics
from datetime import datetime, timedelta
from loguru import logger
from core.config import (
    EBAY_APP_ID, EBAY_CERT_ID,
    FMV_LOOKBACK_DAYS, MIN_SOLD_COMPS
)
from core.database import upsert_fmv, init_db
from data.watchlist import load_watchlist

_oauth_token: str | None = None
_token_expiry: datetime | None = None


def get_oauth_token() -> str:
    """Get an OAuth app token, refreshing if expired."""
    global _oauth_token, _token_expiry
    if _oauth_token and _token_expiry and datetime.utcnow() < _token_expiry:
        return _oauth_token

    resp = requests.post(
        "https://api.ebay.com/identity/v1/oauth2/token",
        auth=(EBAY_APP_ID, EBAY_CERT_ID),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "client_credentials",
            "scope": "https://api.ebay.com/oauth/api_scope",
        },
        timeout=15,
    )
    resp.raise_for_status()
    token_data = resp.json()
    _oauth_token = token_data["access_token"]
    _token_expiry = datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 7200) - 60)
    logger.info("OAuth token acquired, expires in {}s", token_data.get("expires_in"))
    return _oauth_token


def fetch_active_prices(card_name: str) -> list[float]:
    """
    Query eBay Browse API for active PSA 10 listings.
    Returns list of asking prices sorted ascending.
    """
    token = get_oauth_token()
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    params = {
        "q": f"{card_name} PSA 10",
        "category_ids": "2536",
        "filter": "buyingOptions:{FIXED_PRICE},conditionIds:{3000}",
        "sort": "price",
        "limit": "50",
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        logger.info("Browse API for '{}' — status {}", card_name, resp.status_code)
        resp.raise_for_status()
        data = resp.json()

        items = data.get("itemSummaries", [])
        prices = []
        for item in items:
            price = float(item.get("price", {}).get("value", 0))
            if price > 0:
                prices.append(price)

        prices.sort()
        logger.info("Found {} active PSA 10 listings for '{}'", len(prices), card_name)
        return prices

    except Exception as e:
        logger.error("Error fetching listings for '{}': {}", card_name, e)
        return []


def compute_median_fmv(prices: list[float], sample_size: int = 5) -> float | None:
    """Take the median of the lowest N asking prices as an FMV proxy."""
    if not prices:
        return None
    lowest = prices[:sample_size]
    return round(statistics.median(lowest), 2)


def run_price_oracle():
    """Main entry point — update FMV for all watchlist cards."""
    init_db()
    watchlist = load_watchlist()
    logger.info("Price Oracle running for {} cards", len(watchlist))

    for card in watchlist:
        name = card["name"]
        key  = card["key"]

        prices = fetch_active_prices(name)

        if len(prices) < MIN_SOLD_COMPS:
            logger.warning("Insufficient data for '{}' ({} listings found, need {}), skipping", name, len(prices), MIN_SOLD_COMPS)
            time.sleep(5)
            continue

        fmv = compute_median_fmv(prices)
        upsert_fmv(key, name, fmv, fmv, len(prices))
        logger.info("FMV proxy | {} | median of lowest 5: ${} | total listings: {}", name, fmv, len(prices))
        time.sleep(5)


if __name__ == "__main__":
    run_price_oracle()
