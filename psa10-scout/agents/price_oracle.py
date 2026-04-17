"""
Price Oracle — fetches PSA 10 sold comps from eBay and computes FMV.

Uses eBay's Finding API (completedItems=true) to pull recent sales,
then computes 30-day and 90-day weighted average sale prices per card.
"""
import requests
from datetime import datetime, timedelta
from loguru import logger
from core.config import (
    EBAY_APP_ID, EBAY_FINDING_API_URL,
    FMV_LOOKBACK_DAYS, MIN_SOLD_COMPS
)
from core.database import upsert_fmv, init_db
from data.watchlist import load_watchlist


def fetch_sold_comps(card_name: str, days: int = 90) -> list[dict]:
    """
    Query eBay completed listings for a PSA 10 card.
    Returns list of {price, date} dicts.
    """
    url = "https://svcs.ebay.com/services/search/FindingService/v1"
    params = {
        "OPERATION-NAME":                 "findCompletedItems",
        "SERVICE-VERSION":                "1.0.0",
        "SECURITY-APPNAME":               EBAY_APP_ID,
        "RESPONSE-DATA-FORMAT":           "JSON",
        "keywords":                       f"{card_name} PSA 10",
        "categoryId":                     "2536",
        "itemFilter(0).name":             "SoldItemsOnly",
        "itemFilter(0).value":            "true",
        "itemFilter(1).name":             "Condition",
        "itemFilter(1).value":            "3000",
        "sortOrder":                      "EndTimeSoonest",
        "paginationInput.entriesPerPage": "50",
    }
    headers = {
        "Content-Type": "application/json",
    }

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        logger.debug("eBay findCompletedItems status={} body={}", resp.status_code, resp.text[:500])
        resp.raise_for_status()
        data = resp.json()

        items = (
            data.get("findCompletedItemsResponse", [{}])[0]
               .get("searchResult", [{}])[0]
               .get("item", [])
        )

        cutoff = datetime.utcnow() - timedelta(days=days)
        comps = []
        for item in items:
            price = float(item["sellingStatus"][0]["currentPrice"][0]["__value__"])
            end_time = datetime.strptime(
                item["listingInfo"][0]["endTime"][0], "%Y-%m-%dT%H:%M:%S.%fZ"
            )
            if end_time >= cutoff:
                comps.append({"price": price, "date": end_time})

        logger.info("Fetched {} comps for '{}' ({}d)", len(comps), card_name, days)
        return comps

    except Exception as e:
        logger.error("Error fetching comps for '{}': {}", card_name, e)
        return []


def compute_fmv(comps: list[dict], lookback_days: int) -> float | None:
    """Weighted average — more recent sales weighted higher."""
    if not comps:
        return None
    now = datetime.utcnow()
    total_weight = 0.0
    weighted_sum = 0.0
    for c in comps:
        age_days = (now - c["date"]).days
        weight = max(1, lookback_days - age_days)
        weighted_sum += c["price"] * weight
        total_weight += weight
    return round(weighted_sum / total_weight, 2) if total_weight else None


def run_price_oracle():
    """Main entry point — update FMV for all watchlist cards."""
    init_db()
    watchlist = load_watchlist()
    logger.info("Price Oracle running for {} cards", len(watchlist))

    for card in watchlist:
        name = card["name"]
        key  = card["key"]

        comps_90d = fetch_sold_comps(name, days=90)
        comps_30d = [c for c in comps_90d if (datetime.utcnow() - c["date"]).days <= 30]

        fmv_90d = compute_fmv(comps_90d, 90)
        fmv_30d = compute_fmv(comps_30d, 30)

        if len(comps_90d) < MIN_SOLD_COMPS:
            logger.warning("Insufficient comps for '{}' ({}), skipping FMV", name, len(comps_90d))
            continue

        upsert_fmv(key, name, fmv_30d, fmv_90d, len(comps_90d))
        logger.info("FMV updated | {} | 30d: ${} | 90d: ${}", name, fmv_30d, fmv_90d)


if __name__ == "__main__":
    run_price_oracle()
