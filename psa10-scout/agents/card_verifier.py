# CLAUDE API USAGE
# Called once per unique listing found
# Typical run: 5-20 unique listings per card
# Each call: ~200 input tokens + ~50 output tokens
# Very low cost per run

import requests
import json
from loguru import logger
from core.config import ANTHROPIC_API_KEY

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

CARD_PROFILE = """
Card we are looking for:
- Name: Charizard ex Special Art Rare (SAR)
- Set: Pokemon 151 (Japanese version, set code SV2a)
- Card number: 201/165
- Year: 2023
- Language: Japanese
- Grade: PSA 10
- Also known as: Special Illustration Rare (SIR),
  リザードン, Lizardon
- NOT: XY era Charizard EX, Base Set Charizard,
  Mega Charizard, English version, non-PSA graded,
  PSA grades other than 10
"""

def verify_listing(title: str, price: float) -> dict:
    """
    Use Claude to verify if a listing title matches
    our target card.
    Returns: {
        "is_match": bool,
        "confidence": int (0-100),
        "reason": str,
        "card_identified": str
    }
    """
    prompt = f"""You are a Pokemon card expert and grading specialist.

{CARD_PROFILE}

Analyze this eBay listing and determine if it matches
our target card:

Title: "{title}"
Price: ${price}

Respond ONLY with a JSON object, no other text:
{{
  "is_match": true or false,
  "confidence": 0-100,
  "reason": "brief explanation",
  "card_identified": "what card this actually is"
}}

Be strict. If you are not at least 70% confident
it is the correct Japanese PSA 10 Pokemon 151
Charizard ex SAR, return is_match: false.
"""

    try:
        response = requests.post(
            ANTHROPIC_API_URL,
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 200,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        text = data["content"][0]["text"].strip()

        result = json.loads(text)
        logger.info(
            "Card verify | '{}' | match={} | confidence={}% | {}",
            title[:60], result["is_match"],
            result["confidence"], result["reason"]
        )
        return result

    except Exception as e:
        logger.warning("Card verifier error for '{}': {}", title[:50], e)
        return {
            "is_match": "charizard" in title.lower() and "psa" in title.lower(),
            "confidence": 30,
            "reason": "fallback check - verifier error",
            "card_identified": "unknown"
        }


def batch_verify(listings: list[dict]) -> list[dict]:
    """
    Verify a batch of listings and return only confirmed matches.
    listings: list of {"title": str, "price": float, ...}
    """
    verified = []
    for listing in listings:
        result = verify_listing(listing["title"], listing["price"])
        if result["is_match"] and result["confidence"] >= 70:
            listing["verify_confidence"] = result["confidence"]
            listing["card_identified"] = result["card_identified"]
            verified.append(listing)
        else:
            logger.info(
                "REJECTED by AI | '{}' | identified as: {}",
                listing["title"][:60],
                result["card_identified"]
            )

    logger.info(
        "Batch verify: {}/{} listings confirmed as target card",
        len(verified), len(listings)
    )
    return verified
