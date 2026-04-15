"""Unit tests for the deal scoring logic."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.deal_ranker import compute_score


def test_fire_deal_scores_high():
    score = compute_score(discount_pct=0.30, fmv_90d=500, ask_price=350)
    assert score >= 70, f"Expected >=70, got {score}"


def test_small_discount_scores_low():
    score = compute_score(discount_pct=0.05, fmv_90d=100, ask_price=95)
    assert score <= 40, f"Expected <=40, got {score}"


def test_score_bounded():
    score = compute_score(discount_pct=0.99, fmv_90d=10000, ask_price=100)
    assert 0 <= score <= 100, f"Score out of bounds: {score}"


def test_high_value_card_scores_higher():
    score_cheap = compute_score(discount_pct=0.15, fmv_90d=30,   ask_price=25)
    score_exp   = compute_score(discount_pct=0.15, fmv_90d=2000, ask_price=1700)
    assert score_exp > score_cheap


if __name__ == "__main__":
    test_fire_deal_scores_high()
    test_small_discount_scores_low()
    test_score_bounded()
    test_high_value_card_scores_higher()
    print("All tests passed.")
