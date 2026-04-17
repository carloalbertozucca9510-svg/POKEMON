"""
Price Oracle — estimates FMV for PSA 10 cards using eBay Browse API.

Uses the median of the lowest active asking prices as an FMV proxy,
since findCompletedItems is restricted for our account type.
"""
import requests
import time
import statistics
import base64
from datetime import datetime, timedelta
from loguru import logger
from core.config import (
    EBAY_APP_ID, EBAY_CERT_ID,
    FMV_LOOKBACK_DAYS, MIN_SOLD_COMPS
)
from core.database import upsert_fmv, init_db
from data.watchlist import load_watchlist
from data.search_builder import build_search_queries, deduplicate_listings

def get_oauth_token():
    credentials = f"{EBAY_APP_ID}:{EBAY_CERT_ID}"
    encoded = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = "grant_type=client_credentials&scope=https%3A%2F%2Fapi.ebay.com%2Foauth%2Fapi_scope"

    resp = requests.post(
        "https://api.ebay.com/identity/v1/oauth2/token",
        headers=headers,
        data=data,
        timeout=15,
    )

    logger.debug("OAuth token status={} body={}", resp.status_code, resp.text[:300])
    resp.raise_for_status()
    token_data = resp.json()
    return token_data["access_token"]


def fetch_active_prices(card: dict) -> list[float]:
    """
    Query eBay Browse API for active PSA 10 listings using multiple search queries.
    Returns deduplicated list of asking prices sorted ascending.
    """
    token = get_oauth_token()
    queries = build_search_queries(card)
    logger.info("Searching '{}' with {} queries: {}", card["name"], len(queries), queries)

    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    all_results = []
    raw_total = 0

    for query in queries:
        params = {
            "q": query,
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
            logger.debug("Browse API query='{}' — status {}", query, resp.status_code)
            resp.raise_for_status()
            data = resp.json()

            items = data.get("itemSummaries", [])
            raw_total += len(items)
            for item in items:
                price = float(item.get("price", {}).get("value", 0))
                if price >= 50:
                    all_results.append({
                        "item_id": item.get("itemId", ""),
                        "price": price,
                    })

        except Exception as e:
            logger.error("Error on query '{}': {}", query, e)

    deduped = deduplicate_listings(all_results)
    prices = sorted(r["price"] for r in deduped)
    logger.info("'{}' — raw results: {}, after dedup: {}, after $50 filter: {}",
                card["name"], raw_total, len(deduped), len(prices))
    return prices


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

        prices = fetch_active_prices(card)

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
