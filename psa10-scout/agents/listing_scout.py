"""
Listing Scout — scans eBay active listings for PSA 10 cards on the watchlist.
Passes each listing to the Deal Ranker for scoring.
"""
import requests
import time
import base64
from datetime import datetime
from loguru import logger
from core.config import EBAY_APP_ID, EBAY_CERT_ID
from core.models import Listing
from data.watchlist import load_watchlist
from agents.deal_ranker import score_and_save_deal
from core.database import get_fmv, init_db


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


def fetch_active_listings(card_name: str) -> list[Listing]:
    """Search eBay Browse API for active PSA 10 card listings."""
    token = get_oauth_token()
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    params = {
        "q": f"{card_name} PSA 10",
        "category_ids": "2536",
        "filter": "conditionIds:{3000}",
        "sort": "price",
        "limit": "25",
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
        listings = []
        for item in items:
            price = float(item.get("price", {}).get("value", 0))
            if price <= 0:
                continue

            listings.append(Listing(
                item_id     = item.get("itemId", ""),
                card_name   = card_name,
                psa_grade   = 10,
                ask_price   = price,
                listing_url = item.get("itemWebUrl", ""),
                source      = "ebay",
                listed_at   = datetime.utcnow(),
                image_url   = item.get("image", {}).get("imageUrl", ""),
                seller      = item.get("seller", {}).get("username", ""),
            ))

        logger.info("Found {} listings for '{}'", len(listings), card_name)
        return listings

    except Exception as e:
        logger.error("Error fetching listings for '{}': {}", card_name, e)
        return []


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

        listings = fetch_active_listings(card["name"])
        for listing in listings:
            if score_and_save_deal(listing, fmv_row):
                deals_found += 1
        time.sleep(2)

    logger.info("Scout complete — {} new deals saved", deals_found)


if __name__ == "__main__":
    run_listing_scout()
