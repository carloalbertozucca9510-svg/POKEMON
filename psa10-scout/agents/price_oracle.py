"""
Price Oracle — estimates FMV for PSA 10 cards using eBay Browse API.

Uses IQR-filtered median of active asking prices as an FMV proxy,
since findCompletedItems is restricted for our account type.
"""
import requests
import time
import statistics
import base64
import numpy as np
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
            "limit": "200",
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
                if price > 0:
                    all_results.append({
                        "item_id": item.get("itemId", ""),
                        "price": price,
                    })

        except Exception as e:
            logger.error("Error on query '{}': {}", query, e)

    deduped = deduplicate_listings(all_results)
    prices = sorted(r["price"] for r in deduped)
    logger.info("'{}' — raw results: {}, after dedup: {}", card["name"], raw_total, len(deduped))
    return prices


def compute_iqr_fmv(prices: list[float]) -> tuple[float | None, float, float]:
    """
    Use IQR method to remove outliers, then return median of cleaned prices.
    Returns (fmv, lower_fence, upper_fence).
    """
    if len(prices) < 3:
        return None, 0.0, 0.0

    q1 = float(np.percentile(prices, 25))
    q3 = float(np.percentile(prices, 75))
    iqr = q3 - q1
    lower_fence = q1 - (1.5 * iqr)
    upper_fence = q3 + (1.5 * iqr)
    cleaned = [p for p in prices if lower_fence <= p <= upper_fence]

    logger.info("IQR stats — Q1: ${:.2f}, Q3: ${:.2f}, IQR: ${:.2f}, fences: [${:.2f}, ${:.2f}], cleaned: {}/{}",
                q1, q3, iqr, lower_fence, upper_fence, len(cleaned), len(prices))

    if len(cleaned) < 3:
        return None, lower_fence, upper_fence

    fmv = round(statistics.median(cleaned), 2)
    return fmv, lower_fence, upper_fence


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

        fmv, lower_fence, upper_fence = compute_iqr_fmv(prices)

        if fmv is None:
            logger.warning("Could not compute FMV for '{}' — too few prices after IQR filtering", name)
            time.sleep(5)
            continue

        upsert_fmv(key, name, fmv, fmv, len(prices))
        logger.info("FMV | {} | ${} (IQR median) | total listings: {}", name, fmv, len(prices))
        time.sleep(5)


if __name__ == "__main__":
    run_price_oracle()
