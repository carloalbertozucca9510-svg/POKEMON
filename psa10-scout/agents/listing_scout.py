"""
Listing Scout — scans eBay active listings for PSA 10 cards on the watchlist.
Passes each listing to the Deal Ranker for scoring.
"""
import requests
import time
import base64
import numpy as np
from datetime import datetime
from loguru import logger
from core.config import EBAY_APP_ID, EBAY_CERT_ID
from core.models import Listing
from data.watchlist import load_watchlist
from agents.deal_ranker import score_and_save_deal
from core.database import get_fmv, init_db
from data.search_builder import build_search_queries, deduplicate_listings
from agents.card_verifier import batch_verify


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


def is_valid_japanese_psa10(title: str) -> bool:
    title_lower = title.lower()

    has_psa = "psa" in title_lower

    jp_keywords = ["japanese", "japan", " jp ",
                   "jpn", "日本", "sv2a", "リザードン"]
    has_japanese = any(kw in title_lower for kw in jp_keywords)

    card_keywords = ["charizard", "リザードン", "lizardon"]
    has_card = any(kw in title_lower for kw in card_keywords)

    return has_psa and has_japanese and has_card


def compute_iqr_fences(prices: list[float]) -> tuple[float, float]:
    """Compute IQR fences for outlier detection."""
    if len(prices) < 3:
        return 0.0, float("inf")
    q1 = float(np.percentile(prices, 25))
    q3 = float(np.percentile(prices, 75))
    iqr = q3 - q1
    return q1 - (1.5 * iqr), q3 + (1.5 * iqr)


def fetch_active_listings(card: dict) -> list[dict]:
    """Search eBay Browse API using short queries, then filter and verify."""
    token = get_oauth_token()
    queries = build_search_queries(card)
    logger.info("Searching '{}' with {} queries", card["name"], len(queries))

    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    all_results = []
    raw_total = 0

    for query in queries:
        params = {
            "q": query,
            "category_ids": "2536",
            "filter": "conditionIds:{3000|4000}",
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
                if price <= 0:
                    continue

                all_results.append({
                    "item_id": item.get("itemId", ""),
                    "title": item.get("title", ""),
                    "price": price,
                    "listing": Listing(
                        item_id     = item.get("itemId", ""),
                        card_name   = card["name"],
                        psa_grade   = 10,
                        ask_price   = price,
                        listing_url = item.get("itemWebUrl", ""),
                        source      = "ebay",
                        listed_at   = datetime.utcnow(),
                        image_url   = item.get("image", {}).get("imageUrl", ""),
                        seller      = item.get("seller", {}).get("username", ""),
                    ),
                })

        except Exception as e:
            logger.error("Error on query '{}': {}", query, e)

    deduped = deduplicate_listings(all_results)

    validated = [r for r in deduped if is_valid_japanese_psa10(r["title"])]
    title_removed = len(deduped) - len(validated)
    logger.info("Title validation: {} passed, {} removed", len(validated), title_removed)

    verified = batch_verify(validated)
    logger.info("After AI verification: {}/{} listings confirmed", len(verified), len(validated))
    logger.info("'{}' pipeline: raw={}, dedup={}, title_validated={}, ai_verified={}",
                card["name"], raw_total, len(deduped), len(validated), len(verified))
    return verified


def run_listing_scout():
    """Main entry — scout every card on the watchlist."""
    init_db()
    watchlist = load_watchlist()
    logger.info("Listing Scout scanning {} cards...", len(watchlist))

    deals_found = 0
    for card in watchlist:
        fmv_row = get_fmv(card["key"])
        if not fmv_row or not fmv_row["fmv_90d"]:
            logger.warning("No FMV for '{}', skipping", card["name"])
            continue

        results = fetch_active_listings(card)
        listings = [r["listing"] for r in results]

        all_prices = [l.ask_price for l in listings]
        lower_fence, upper_fence = compute_iqr_fences(all_prices)
        logger.info("'{}' IQR fences: [${:.2f}, ${:.2f}]", card["name"], lower_fence, upper_fence)

        fmv_value = fmv_row["fmv_90d"]
        for r in results:
            listing = r["listing"]
            title = r["title"]
            confidence = r.get("verify_confidence", 0)

            if not (lower_fence <= listing.ask_price <= upper_fence):
                logger.debug("Skipping outlier: ${:.2f} — {}", listing.ask_price, title[:80])
                continue

            if score_and_save_deal(listing, fmv_row):
                discount_pct = ((fmv_value - listing.ask_price) / fmv_value) * 100 if fmv_value else 0
                logger.info("DEAL FOUND | title: {} | ask: ${:.2f} | FMV: ${:.2f} | discount: {:.1f}% | confidence: {}%",
                            title[:100], listing.ask_price, fmv_value, discount_pct, confidence)
                deals_found += 1
        time.sleep(5)

    logger.info("Scout complete — {} new deals saved", deals_found)


if __name__ == "__main__":
    run_listing_scout()
