"""
Deal Ranker — scores a listing against FMV and saves qualifying deals.

Scoring model (0–100):
  60pts  discount % (scaled relative to fire deal threshold)
  20pts  card value tier (higher value cards = more upside)
  20pts  liquidity placeholder (will use PSA pop report data)
"""
from loguru import logger
from core.config import DEAL_DISCOUNT_THRESHOLD, FIRE_DEAL_THRESHOLD
from core.models import Listing
from core.database import insert_deal


def compute_score(discount_pct: float, fmv_90d: float, ask_price: float) -> int:
    """
    Score a deal 0–100. Higher = better deal.
    Expand with pop report and trend data once those feeds are wired in.
    """
    # Discount component (0–60 pts)
    max_discount = FIRE_DEAL_THRESHOLD * 2
    discount_score = min(60, int((discount_pct / max_discount) * 60))

    # Value tier component (0–20 pts) — higher value cards score better
    if fmv_90d >= 1000:
        value_score = 20
    elif fmv_90d >= 200:
        value_score = 14
    elif fmv_90d >= 50:
        value_score = 8
    else:
        value_score = 4

    # Liquidity placeholder (0–20 pts) — replaced with pop report later
    liquidity_score = 15

    total = discount_score + value_score + liquidity_score
    return min(100, max(0, total))


def score_and_save_deal(listing: Listing, fmv_row) -> bool:
    """
    Score a listing. If it qualifies as a deal, persist it.
    Returns True if a deal was saved.
    """
    fmv = fmv_row["fmv_90d"]
    if not fmv or fmv <= 0:
        return False

    discount_pct = (fmv - listing.ask_price) / fmv
    if discount_pct < DEAL_DISCOUNT_THRESHOLD:
        return False

    score    = compute_score(discount_pct, fmv, listing.ask_price)
    is_fire  = discount_pct >= FIRE_DEAL_THRESHOLD

    deal_data = {
        "item_id":      listing.item_id,
        "card_name":    listing.card_name,
        "ask_price":    listing.ask_price,
        "fmv_90d":      fmv,
        "discount_pct": round(discount_pct, 4),
        "deal_score":   score,
        "is_fire_deal": int(is_fire),
        "listing_url":  listing.listing_url,
    }

    insert_deal(deal_data)
    label = "FIRE DEAL" if is_fire else "deal"
    logger.info(
        "New {} | {} | Ask: ${} | FMV: ${} | -{:.0f}% | Score: {}",
        label, listing.card_name, listing.ask_price,
        fmv, discount_pct * 100, score
    )
    return True
