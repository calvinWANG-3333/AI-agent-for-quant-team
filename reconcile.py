"""
Reconciliation logic: given outputs from Agent 1 and Agent 2,
decide what to write to Remarks L1 and Remarks L2.

This module is PURE LOGIC (no I/O, no LLM, no browser).
That makes it easy to unit-test and reason about.

Business rules: see decision tables in the project blueprint.
Anchors:
  - Refresh data flow:   onboarding guide section 3.5.4.5
  - Missing in crawl flow: onboarding guide section 3.5.4.3
  - Price tolerance: 1% (both agents must agree within this band)
  - Manual escalation: any disagreement or any nulls -> Remark L2 = "manual"
"""
from typing import Optional, Literal


# ============================================================
# Constants
# ============================================================
PRICE_TOLERANCE_PCT = 1.0   # % difference still counts as "agreed"
MANUAL_TAG = "manual"        # written to Remark L2 when human review needed


# ============================================================
# Helper functions
# ============================================================
def prices_agree(p1: Optional[float], p2: Optional[float]) -> bool:
    """Return True if two prices are within PRICE_TOLERANCE_PCT of each other."""
    if p1 is None or p2 is None:
        return False
    if p1 == 0 or p2 == 0:
        return p1 == p2
    diff_pct = abs(p1 - p2) / max(p1, p2) * 100
    return diff_pct <= PRICE_TOLERANCE_PCT


def price_matches_validated(
    agent_price: Optional[float],
    validated_price: float,
) -> bool:
    """Return True if agent_price matches the Original Price_validated."""
    if agent_price is None:
        return False
    if validated_price == 0:
        return agent_price == 0
    diff_pct = abs(agent_price - validated_price) / validated_price * 100
    return diff_pct <= PRICE_TOLERANCE_PCT


# ============================================================
# Main reconciliation function
# ============================================================
def reconcile(
    row_type: Literal["refresh_data", "missing_in_crawl"],
    original_remark_l1: Optional[str],
    validated_price: float,
    agent_1_result: dict,
    agent_2_result: dict,
) -> dict:
    """
    Decide what to write to Remarks L1 and Remarks L2.

    Logic priority (top-down):
      1. If both agents agree on a price -> trust the price, write accordingly.
         (This is the strongest signal; we trust it even if redirect flags
          slightly disagree, because Claude sometimes flags SEO URL rewrites
          as 'redirected' while GPT correctly doesn't.)
      2. If both agents agree the product is gone (both redirected, both
         null price) -> mark product gone.
      3. Anything else -> manual.
    """
    a1 = agent_1_result
    a2 = agent_2_result

    a1_redirected = a1.get("url_redirected", False)
    a2_redirected = a2.get("url_redirected", False)
    a1_price = a1.get("price_found")
    a2_price = a2.get("price_found")

    # ─────────────────────────────────────────────────────────
    # Priority 1: Both agents found a price AND prices agree
    # → trust them, regardless of redirect flag inconsistencies.
    # ─────────────────────────────────────────────────────────
    if a1_price is not None and a2_price is not None and prices_agree(a1_price, a2_price):
        canonical_price = a1_price

        if price_matches_validated(canonical_price, validated_price):
            # Price unchanged
            if row_type == "refresh_data":
                return {
                    "remark_l1": "Refresh data",
                    "remark_l2": "Same price",
                    "decision": "AUTO_REFRESH_SAME_PRICE",
                    "reasoning": (
                        f"Both agents found {canonical_price}, matches "
                        f"validated price {validated_price}."
                    ),
                }
            else:  # missing_in_crawl
                return {
                    "remark_l1": "Not OK, available",
                    "remark_l2": "Same price",
                    "decision": "AUTO_MISSING_BUT_AVAILABLE_SAME_PRICE",
                    "reasoning": (
                        f"Product is actually still available at {canonical_price}, "
                        "matches validated price. Crawler missed it."
                    ),
                }
        else:
            # Price has changed
            new_price_str = _format_price(canonical_price)
            if row_type == "refresh_data":
                return {
                    "remark_l1": "Refresh data",
                    "remark_l2": new_price_str,
                    "decision": "AUTO_REFRESH_NEW_PRICE",
                    "reasoning": (
                        f"Both agents found {canonical_price}, differs from "
                        f"validated {validated_price}."
                    ),
                }
            else:  # missing_in_crawl
                return {
                    "remark_l1": "Not OK, available",
                    "remark_l2": new_price_str,
                    "decision": "AUTO_MISSING_BUT_AVAILABLE_NEW_PRICE",
                    "reasoning": (
                        f"Product still on site at {canonical_price}, "
                        f"differs from validated {validated_price}."
                    ),
                }

    # ─────────────────────────────────────────────────────────
    # Priority 2: Both agents agree the product is gone
    # (both redirected AND both have null price)
    # ─────────────────────────────────────────────────────────
    both_say_gone = (
        a1_redirected and a2_redirected
        and a1_price is None and a2_price is None
    )
    if both_say_gone:
        if row_type == "refresh_data":
            return {
                "remark_l1": "Missing-remove",
                "remark_l2": None,
                "decision": "AUTO_PRODUCT_GONE",
                "reasoning": "Both agents redirected and found no price; product gone.",
            }
        else:  # missing_in_crawl
            return {
                "remark_l1": "OK, missing",
                "remark_l2": None,
                "decision": "AUTO_CONFIRMED_MISSING",
                "reasoning": "Both agents confirmed product is no longer on site.",
            }

    # ─────────────────────────────────────────────────────────
    # Priority 3: Anything else → manual review
    # (price disagreement, one null, one redirect / one not without
    #  agreeing prices, page blocked, etc.)
    # ─────────────────────────────────────────────────────────
    return {
        "remark_l1": original_remark_l1,
        "remark_l2": MANUAL_TAG,
        "decision": "LOW_CONFIDENCE_NEEDS_REVIEW",
        "reasoning": (
            f"Agent 1: redirect={a1_redirected}, price={a1_price}. "
            f"Agent 2: redirect={a2_redirected}, price={a2_price}. "
            "Cannot reconcile automatically."
        ),
    }

def _format_price(price: float) -> str:
    """Format a price number for writing to Remark L2."""
    # Drop trailing .0 if integer-valued
    if price == int(price):
        return str(int(price))
    return f"{price:.2f}"