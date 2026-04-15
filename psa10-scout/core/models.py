"""
Dataclasses for the core domain objects.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class SoldComp:
    """A completed eBay sale used to compute FMV."""
    item_id:    str
    card_name:  str
    psa_grade:  int
    sale_price: float
    sale_date:  datetime
    source:     str = "ebay"


@dataclass
class FairMarketValue:
    """Computed FMV for a specific card at PSA 10."""
    card_key:     str            # normalised name used as lookup key
    card_name:    str
    fmv_30d:      Optional[float]
    fmv_90d:      Optional[float]
    comp_count:   int
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Listing:
    """An active listing found by the scout."""
    item_id:     str
    card_name:   str
    psa_grade:   int
    ask_price:   float
    listing_url: str
    source:      str
    listed_at:   datetime
    image_url:   str = ""
    seller:      str = ""


@dataclass
class Deal:
    """A listing flagged as a potential deal."""
    listing:      Listing
    fmv:          FairMarketValue
    discount_pct: float          # e.g. 0.18 = 18% below FMV
    deal_score:   int            # 0–100
    is_fire_deal: bool
    alerted:      bool = False
    found_at:     datetime = field(default_factory=datetime.utcnow)
