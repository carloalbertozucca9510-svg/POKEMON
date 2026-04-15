"""
Listing Scout — scans eBay active listings for PSA 10 cards on the watchlist.
Passes each listing to the Deal Ranker for scoring.
"""
import requests
from datetime import datetime
from loguru import logger
from core.config import EBAY_APP_ID, EBAY_FINDING_API_URL
from core.models import Listing
from data.watchlist import load_watchlist
from agents.deal_ranker import score_and_save_deal
from core.database import get_fmv


def fetch_active_listings(card_name: str) -> list[Listing]:
    """Search eBay active BIN and auction listings for a PSA 10 card."""
    params = {
        "OPERATION-NAME":                 "findItemsAdvanced",
        "SERVICE-VERSION":                "1.0.0",
        "SECURITY-APPNAME":               EBAY_APP_ID,
        "RESPONSE-DATA-FORMAT":           "JSON",
        "keywords":                       f"{card_name} PSA 10",
        "categoryId":                     "2536",
        "itemFilter(0).name":             "Condition",
        "itemFilter(0).value":            "3000",
        "sortOrder":                      "PricePlusShippingLowest",
        "paginationInput.entriesPerPage": "25",
    }

    try:
        resp = requests.get(EBAY_FINDING_API_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        items = (
            data.get("findItemsAdvancedResponse", [{}])[0]
               .get("searchResult", [{}])[0]
               .get("item", [])
        )

        listings = []
        for item in items:
            price_node = item.get("sellingStatus", [{}])[0].get("currentPrice", [{}])[0]
            price = float(price_node.get("__value__", 0))
            if price <= 0:
                continue

            listings.append(Listing(
                item_id     = item["itemId"][0],
                card_name   = card_name,
                psa_grade   = 10,
                ask_price   = price,
                listing_url = item["viewItemURL"][0],
                source      = "ebay",
                listed_at   = datetime.utcnow(),
                image_url   = item.get("galleryURL", [""])[0],
                seller      = item.get("sellerInfo", [{}])[0].get("sellerUserName", [""])[0],
            ))

        logger.info("Found {} listings for '{}'", len(listings), card_name)
        return listings

    except Exception as e:
        logger.error("Error fetching listings for '{}': {}", card_name, e)
        return []


def run_listing_scout():
    """Main entry — scout every card on the watchlist."""
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

    logger.info("Scout complete — {} new deals saved", deals_found)


if __name__ == "__main__":
    run_listing_scout()
