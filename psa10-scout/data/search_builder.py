# API CALL BUDGET (1 card, 20 queries - testing mode)
# 1 card × 20 queries × 1 API call each = 20 calls per run
# Price oracle: 20 calls
# Listing scout: 20 calls
# Total per run: 40 calls
# 12 runs per day (every 2 hours) = 480 calls/day
# eBay Browse API limit = 5,000 calls/day
# Usage = 9.6% of daily limit — very safe for testing

from loguru import logger


def build_search_queries(card: dict) -> list[str]:
    """
    Generates 20 SHORT focused queries (3-4 words max) to maximize
    eBay result count. Filtering happens on our side after results come back.
    Returns deduplicated list of query strings.
    """
    raw_queries = [
        # Group A — shortest most effective (2-3 words)
        "Charizard ex japanese PSA 10",
        "Charizard ex SV2a PSA 10",
        "Charizard ex 201 PSA 10",
        "リザードン SV2a PSA 10",
        "リザードン 201 PSA 10",

        # Group B — slightly more specific (3-4 words)
        "Charizard ex 151 PSA 10",
        "Charizard SAR japanese PSA 10",
        "Charizard SV2a SAR PSA 10",
        "Charizard ex SAR japanese",
        "Charizard 201 japanese PSA",

        # Group C — keyword variations
        "Charizard Special Art japanese PSA",
        "Charizard SIR japanese PSA 10",
        "Charizard Special Illustration SV2a",
        "Charizard ex 201 SV2a",
        "リザードン SAR PSA 10",

        # Group D — broader fallbacks
        "Charizard ex japanese graded",
        "Charizard 151 SAR PSA",
        "Charizard SV2a japanese graded",
        "Charizard ex 2023 japanese PSA",
        "リザードン Special Art PSA",
    ]

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for q in raw_queries:
        q = " ".join(q.split())
        if q and q not in seen:
            seen.add(q)
            unique.append(q)

    logger.info("Built {} unique queries for '{}'", len(unique), card.get("name", "unknown"))
    return unique


def deduplicate_listings(listings: list) -> list:
    """Remove duplicate listings by item_id."""
    seen_ids = set()
    unique = []
    for listing in listings:
        if listing.get("item_id") not in seen_ids:
            seen_ids.add(listing.get("item_id"))
            unique.append(listing)
    return unique
