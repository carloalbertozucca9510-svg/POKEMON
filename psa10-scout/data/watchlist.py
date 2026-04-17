"""
Watchlist loader — reads watchlist.json and returns a normalised list.
"""
import json
import re
from pathlib import Path
from core.config import WATCHLIST_PATH


def normalise_key(name: str) -> str:
    """Lowercase, strip special chars — used as DB lookup key."""
    return re.sub(r"[^a-z0-9]", "_", name.lower()).strip("_")


def load_watchlist() -> list[dict]:
    path = Path(WATCHLIST_PATH)
    if not path.exists():
        return []
    with open(path) as f:
        cards = json.load(f)
    for card in cards:
        if "key" not in card:
            card["key"] = normalise_key(card["name"])
        card.setdefault("language", ["english"])
        card.setdefault("name_variants", [card["name"]])
        card.setdefault("set_variants", [])
        card.setdefault("number_variants", [])
        card.setdefault("keyword_variants", [])
    return cards
