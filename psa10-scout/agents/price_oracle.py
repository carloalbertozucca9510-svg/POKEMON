"""
Price Oracle — fetches PSA 10 listings from eBay and computes FMV.

Uses eBay's Browse API with OAuth client credentials to pull current listings,
then computes 30-day and 90-day weighted average prices per card.
"""
import requests
import time
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
    logger.debug("OAuth token status={} body={}", resp.status_code, resp.text[:500])
    resp.raise_for_status()
    token_data = resp.json()
    _oauth_token = token_data["access_token"]
    _token_expiry = datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 7200) - 60)
    logger.info("OAuth token acquired, expires in {}s", token_data.get("expires_in"))
    return _oauth_token


def fetch_sold_comps(card_name: str, days: int = 90) -> list[dict]:
    """
    Query eBay Browse API for PSA 10 card listings.
    Returns list of {price, date} dicts.
    """
    token = get_oauth_token()
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    params = {
        "q": f"{card_name} PSA 10",
        "category_ids": "2536",
        "filter": "conditionIds:{3000},buyingOptions:{FIXED_PRICE}",
        "sort": "price",
        "limit": "50",
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        logger.debug("eBay Browse API status={} body={}", resp.status_code, resp.text[:500])
        resp.raise_for_status()
        data = resp.json()

        items = data.get("itemSummaries", [])
        cutoff = datetime.utcnow() - timedelta(days=days)
        comps = []
        for item in items:
            price = float(item.get("price", {}).get("value", 0))
            if price <= 0:
                continue
            date_str = item.get("itemCreationDate", "")
            if date_str:
                item_date = datetime.strptime(date_str[:19], "%Y-%m-%dT%H:%M:%S")
            else:
                item_date = datetime.utcnow()
            if item_date >= cutoff:
                comps.append({"price": price, "date": item_date})

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
        time.sleep(2)


if __name__ == "__main__":
    run_price_oracle()
