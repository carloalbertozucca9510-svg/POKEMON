from loguru import logger

CARD_RULES = {
    "must_have_one_of": [
        "psa 10", "psa10"
    ],
    "must_have_one_name": [
        "charizard", "リザードン", "lizardon"
    ],
    "set_identifiers": [
        "sv2a", "151", "201", "2023",
        "pokemon 151", "scarlet violet 151"
    ],
    "quality_boosters": [
        "special art", "sar", "sir",
        "special illustration", "full art"
    ],
    "japanese_indicators": [
        "japanese", "japan", " jp ", "jpn",
        "日本", "sv2a", "リザードン"
    ],
    "disqualifiers": [
        "xy", "wild blaze", "mega ", "m charizard",
        "base set", "shadowless", "1st edition",
        "1999", "2014", "2015", "2016",
        "fossil", "jungle", "neo",
        "psa 9", "psa 8", "psa 7",
        "psa 6", "psa 5", "psa 4",
        "psa 3", "psa 2", "psa 1",
        "cgc", "bgs", "tag team",
        "vmax", "vstar", "gx", "ex holo"
    ]
}


def score_listing_title(title: str, price: float) -> dict:
    title_lower = title.lower()
    score = 0
    reasons = []

    # Immediate disqualifiers — return 0 if any match
    for term in CARD_RULES["disqualifiers"]:
        if term in title_lower:
            return {
                "is_match": False,
                "confidence": 0,
                "reason": f"disqualified: contains '{term}'",
                "card_identified": "wrong card"
            }

    # Must have PSA 10
    if "psa 10" in title_lower or "psa10" in title_lower:
        score += 30
        reasons.append("PSA 10 confirmed")
    elif "psa" in title_lower:
        score += 10
        reasons.append("PSA mentioned")
    else:
        return {
            "is_match": False,
            "confidence": 0,
            "reason": "no PSA mention",
            "card_identified": "ungraded or wrong grader"
        }

    # Must have card name
    has_name = False
    for name in CARD_RULES["must_have_one_name"]:
        if name in title_lower:
            score += 20
            reasons.append(f"name match: {name}")
            has_name = True
            break
    if not has_name:
        return {
            "is_match": False,
            "confidence": 0,
            "reason": "card name not found",
            "card_identified": "wrong card"
        }

    # Set identifiers — score for each match
    set_matches = 0
    for identifier in CARD_RULES["set_identifiers"]:
        if identifier in title_lower:
            score += 10
            set_matches += 1
            reasons.append(f"set id: {identifier}")

    # Japanese indicators
    jp_matches = 0
    for jp in CARD_RULES["japanese_indicators"]:
        if jp in title_lower:
            score += 15
            jp_matches += 1
            reasons.append(f"JP indicator: {jp}")
            break  # only count first match

    # Quality boosters
    for kw in CARD_RULES["quality_boosters"]:
        if kw in title_lower:
            score += 10
            reasons.append(f"keyword: {kw}")
            break

    # Price sanity check
    # Japanese Charizard ex SAR PSA 10 should be $100-$2000
    if price < 50:
        score -= 20
        reasons.append("price too low for PSA 10")
    elif 150 <= price <= 800:
        score += 10
        reasons.append("price in expected range")

    # Final decision
    confidence = min(100, score)
    is_match = confidence >= 50 and jp_matches > 0 and set_matches > 0

    return {
        "is_match": is_match,
        "confidence": confidence,
        "reason": " | ".join(reasons),
        "card_identified": "Charizard ex SAR 151 Japanese PSA 10"
                           if is_match else "uncertain/wrong card"
    }


def batch_verify(listings: list[dict]) -> list[dict]:
    verified = []
    for listing in listings:
        result = score_listing_title(
            listing["title"],
            listing.get("price", listing.get("ask_price", 0))
        )
        if result["is_match"]:
            listing["verify_confidence"] = result["confidence"]
            listing["card_identified"] = result["card_identified"]
            verified.append(listing)
            logger.info(
                "VERIFIED ({}%) | {} | ${}",
                result["confidence"],
                listing["title"][:60],
                listing.get("price", listing.get("ask_price", 0))
            )
        else:
            logger.info(
                "REJECTED | {} | reason: {}",
                listing["title"][:60],
                result["reason"]
            )

    logger.info(
        "Batch verify: {}/{} listings confirmed",
        len(verified), len(listings)
    )
    return verified
