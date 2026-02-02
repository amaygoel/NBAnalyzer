#!/usr/bin/env python3
"""
Test bet selector sign conventions and probability calculations.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nb_analyzer.ml.bet_selector import (
    win_prob_from_margin,
    cover_prob_from_margin,
    american_to_decimal,
    ev_from_prob_and_american,
    DEFAULT_SIGMA
)


def test_sign_conventions():
    """Verify sign conventions match expectations."""
    print("="*80)
    print("SIGN CONVENTION TESTS")
    print("="*80)

    # Test case from user request
    print("\nTest 1: pred_margin=+10, spread_line_home=-6.5")
    print("  Model predicts home wins by 10 pts")
    print("  Market has home favored by 6.5 (home -6.5)")
    print("  Expected: home cover probability > 50% (model more bullish than market)")

    pred_margin = 10.0
    spread_line_home = -6.5
    p_home_cover = cover_prob_from_margin(pred_margin, spread_line_home, DEFAULT_SIGMA)

    print(f"  Result: P(home covers -6.5) = {p_home_cover:.1%}")
    print(f"  ✓ PASS" if p_home_cover > 0.5 else "  ✗ FAIL")

    # Additional test cases
    print("\nTest 2: pred_margin=+3, spread_line_home=-6.5")
    print("  Model predicts home wins by 3 pts")
    print("  Market has home favored by 6.5")
    print("  Expected: home cover probability < 50% (model less bullish)")

    pred_margin = 3.0
    spread_line_home = -6.5
    p_home_cover = cover_prob_from_margin(pred_margin, spread_line_home, DEFAULT_SIGMA)

    print(f"  Result: P(home covers -6.5) = {p_home_cover:.1%}")
    print(f"  ✓ PASS" if p_home_cover < 0.5 else "  ✗ FAIL")

    print("\nTest 3: pred_margin=-5, spread_line_home=+3.5")
    print("  Model predicts away wins by 5 pts")
    print("  Market has home underdog by 3.5 (home +3.5)")
    print("  Expected: home cover probability < 50% (model expects home to lose by more)")

    pred_margin = -5.0
    spread_line_home = +3.5
    p_home_cover = cover_prob_from_margin(pred_margin, spread_line_home, DEFAULT_SIGMA)

    print(f"  Result: P(home covers +3.5) = {p_home_cover:.1%}")
    print(f"  ✓ PASS" if p_home_cover < 0.5 else "  ✗ FAIL")

    print("\nTest 4: pred_margin=-5, spread_line_home=+7.5")
    print("  Model predicts away wins by 5 pts")
    print("  Market has home underdog by 7.5")
    print("  Expected: home cover probability > 50% (home can lose by 7)")

    pred_margin = -5.0
    spread_line_home = +7.5
    p_home_cover = cover_prob_from_margin(pred_margin, spread_line_home, DEFAULT_SIGMA)

    print(f"  Result: P(home covers +7.5) = {p_home_cover:.1%}")
    print(f"  ✓ PASS" if p_home_cover > 0.5 else "  ✗ FAIL")


def test_win_probability():
    """Test win probability calculations."""
    print("\n" + "="*80)
    print("WIN PROBABILITY TESTS")
    print("="*80)

    test_cases = [
        (10.0, "Home favored by 10", 0.50, ">"),
        (-10.0, "Away favored by 10", 0.50, "<"),
        (0.0, "Even game", 0.50, "="),
        (14.4, "Home favored by 1 sigma", 0.84, "≈"),
        (-14.4, "Away favored by 1 sigma", 0.16, "≈"),
    ]

    for pred_margin, desc, expected, comp in test_cases:
        p_home_win = win_prob_from_margin(pred_margin, DEFAULT_SIGMA)
        print(f"\npred_margin={pred_margin:+.1f}: {desc}")
        print(f"  P(home wins) = {p_home_win:.1%} (expected {comp} {expected:.1%})")


def test_ev_calculation():
    """Test expected value calculations."""
    print("\n" + "="*80)
    print("EV CALCULATION TESTS")
    print("="*80)

    print("\nTest 1: Fair bet (no edge)")
    print("  Prob=50%, Odds=+100 (even money)")
    ev = ev_from_prob_and_american(0.5, 100)
    print(f"  EV = {ev:.1%} (expected ≈ 0%)")

    print("\nTest 2: Positive edge")
    print("  Prob=60%, Odds=+100 (we have 60% but paid even money)")
    ev = ev_from_prob_and_american(0.6, 100)
    print(f"  EV = {ev:.1%} (expected = 20%)")
    print(f"  Calculation: 0.6 * 2.0 - 1 = {0.6 * 2.0 - 1:.1%}")

    print("\nTest 3: Negative edge")
    print("  Prob=40%, Odds=+100")
    ev = ev_from_prob_and_american(0.4, 100)
    print(f"  EV = {ev:.1%} (expected = -20%)")

    print("\nTest 4: Favorite odds")
    print("  Prob=70%, Odds=-200 (risk $200 to win $100)")
    decimal = american_to_decimal(-200)
    print(f"  Decimal odds: {decimal:.3f}")
    ev = ev_from_prob_and_american(0.7, -200)
    print(f"  EV = {ev:.1%}")
    print(f"  Calculation: 0.7 * {decimal:.3f} - 1 = {0.7 * decimal - 1:.1%}")


def test_odds_conversion():
    """Test odds conversion functions."""
    print("\n" + "="*80)
    print("ODDS CONVERSION TESTS")
    print("="*80)

    test_cases = [
        (100, 2.0),   # Even money
        (150, 2.5),   # +150 = win $150 on $100
        (-150, 1.667), # -150 = risk $150 to win $100
        (200, 3.0),   # +200 = 2-1 underdog
        (-200, 1.5),  # -200 = risk $200 to win $100
    ]

    for american, expected_decimal in test_cases:
        decimal = american_to_decimal(american)
        print(f"\n{american:+4d} -> {decimal:.3f} (expected {expected_decimal:.3f})")

        profit = (decimal - 1) * 100
        print(f"  Win ${profit:.0f} on $100 bet")


if __name__ == '__main__':
    test_sign_conventions()
    test_win_probability()
    test_ev_calculation()
    test_odds_conversion()

    print("\n" + "="*80)
    print("✅ All tests complete")
    print("="*80)
