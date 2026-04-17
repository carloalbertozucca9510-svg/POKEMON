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
    Generates 20 targeted search queries for maximum coverage.
    Fixed prefix: "PSA 10"
    Returns deduplicated list of query strings.
    """
    name_variants = card.get("name_variants", [card["name"]])
    set_variants = card.get("set_variants", [])
    number_variants = card.get("number_variants", [])
    keyword_variants = card.get("keyword_variants", [])
    language_variants = card.get("language_variants", [])

    n = lambda i: name_variants[i] if i < len(name_variants) else ""
    s = lambda i: set_variants[i] if i < len(set_variants) else ""
    num = lambda i: number_variants[i] if i < len(number_variants) else ""
    k = lambda i: keyword_variants[i] if i < len(keyword_variants) else ""
    lang = lambda i: language_variants[i] if i < len(language_variants) else ""

    fixed = "PSA 10"

    raw_queries = [
        # Group A — name + language + number (most specific)
        f"{fixed} {n(0)} {lang(0)} {num(0)}",
        f"{fixed} {n(0)} {lang(0)} {num(1)}",
        f"{fixed} {n(1)} {lang(0)} {num(0)}",
        f"{fixed} {n(0)} {lang(2)} {num(0)}",
        f"{fixed} {n(0)} {lang(3)} {num(1)}",

        # Group B — name + language + keyword
        f"{fixed} {n(0)} {lang(0)} {k(1)}",
        f"{fixed} {n(0)} {lang(0)} {k(0)}",
        f"{fixed} {n(0)} {lang(0)} {k(2)}",
        f"{fixed} {n(1)} {lang(1)} {k(1)}",
        f"{fixed} {n(0)} {lang(2)} {k(4)}",

        # Group C — name + language + set
        f"{fixed} {n(0)} {lang(0)} {s(0)}",
        f"{fixed} {n(0)} {lang(0)} {s(1)}",
        f"{fixed} {n(0)} {lang(1)} {s(2)}",
        f"{fixed} {n(1)} {lang(0)} {s(1)}",
        f"{fixed} {n(0)} {lang(2)} {s(0)}",

        # Group D — broader fallback searches
        f"{fixed} {n(0)} {lang(0)}",
        f"{fixed} {n(3)} {lang(0)} {num(1)}",
        f"{fixed} {n(3)} {s(1)} {k(1)}",
        f"{fixed} {n(0)} {s(1)} {k(1)} PSA",
        f"{fixed} {n(2)} {num(1)} {lang(0)} graded",
    ]

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for q in raw_queries:
        q = " ".join(q.split())  # normalize whitespace
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
