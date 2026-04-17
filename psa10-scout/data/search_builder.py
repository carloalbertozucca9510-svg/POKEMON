# API CALL BUDGET
# 15 cards × 6 queries × 1 call each = 90 calls per run
# 12 runs per day (every 2 hours) = 1,080 calls/day
# eBay Browse API limit = 5,000 calls/day
# Usage = 21.6% of daily limit — safe margin

from itertools import product

FIXED_TERMS = ["pokemon", "PSA 10"]

def build_search_queries(card: dict) -> list[str]:
    """
    Generates all meaningful search query combinations
    for a card based on its variant fields.

    Fixed terms always included: "pokemon PSA 10"

    Variable terms: combines name_variants with
    set_variants OR number_variants OR keyword_variants
    to generate targeted queries.

    Returns a deduplicated list of query strings,
    max 6 queries per card to stay within API limits.
    """
    queries = []
    name_variants = card.get("name_variants", [card["name"]])
    set_variants = card.get("set_variants", [])
    number_variants = card.get("number_variants", [])
    keyword_variants = card.get("keyword_variants", [])
    languages = card.get("language", ["english"])

    fixed = "pokemon PSA 10"

    # Query type 1: name + number (most specific)
    for name, number in product(name_variants[:1], number_variants[:1]):
        queries.append(f"{fixed} {name} {number}".strip())

    # Query type 2: name + keyword
    for name, keyword in product(name_variants[:1], keyword_variants[:1]):
        queries.append(f"{fixed} {name} {keyword}".strip())

    # Query type 3: name + set
    for name, set_v in product(name_variants[:1], set_variants[:1]):
        queries.append(f"{fixed} {name} {set_v}".strip())

    # Query type 4: japanese variant if applicable
    if "japanese" in languages:
        for name in name_variants[:1]:
            queries.append(f"{fixed} {name} japanese".strip())

    # Query type 5: name + second number variant (shorter form)
    if len(number_variants) > 1:
        for name in name_variants[:1]:
            queries.append(f"{fixed} {name} {number_variants[1]}".strip())

    # Query type 6: second name variant + first keyword
    if len(name_variants) > 1 and keyword_variants:
        queries.append(f"{fixed} {name_variants[1]} {keyword_variants[0]}".strip())

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            unique.append(q)

    return unique[:6]  # max 6 queries per card


def deduplicate_listings(listings: list) -> list:
    """Remove duplicate listings by item_id."""
    seen_ids = set()
    unique = []
    for listing in listings:
        if listing.get("item_id") not in seen_ids:
            seen_ids.add(listing.get("item_id"))
            unique.append(listing)
    return unique
