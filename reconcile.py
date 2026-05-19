"""
Reconciliation logic for the SINGLE-AGENT pipeline.

The previous version compared two independent agents (Claude + GPT-4o)
and used price agreement as the primary signal. With only one agent
remaining, that cross-check is no longer available, so the decision
relies on:

  1. url_redirected — did the product disappear?
  2. confidence — did the agent feel certain about what it saw?
  3. price_found — does the price match Original Price_validated?

Decision priority (top-down, first match wins):

  P1. Agent says redirected + no price          -> product gone
  P2. Agent says blocked (BLOCKED: in evidence) -> manual review
  P3. Confidence == high AND price found        -> trust the agent
  P4. Anything else                              -> manual review

Business rules (locked with user):
  - Price tolerance: < 1% diff counts as matching Original Price_validated
  - Disagreement / null / medium-low confidence -> Remark L2 = "manual"
  - Both row types preserve original Remark L1 on manual fallback
"""
from typing import Optional, Literal


# ============================================================
# Constants
# ============================================================
PRICE_TOLERANCE_PCT = 1.0   # % difference still counts as "matching"
MANUAL_TAG = "manual"        # written to Remark L2 when human review needed


# ============================================================
# Helper functions
# ============================================================
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


def _format_price(price: float) -> str:
    """Format a price number for writing to Remark L2."""
    if price == int(price):
        return str(int(price))
    return f"{price:.2f}"


def _evidence_indicates_block(evidence: Optional[str]) -> bool:
    """Detect the 'BLOCKED:' prefix our agent uses on anti-bot pages."""
    if not evidence:
        return False
    return evidence.strip().upper().startswith("BLOCKED")


# ============================================================
# Main reconciliation function (single-agent)
# ============================================================
def reconcile(
    row_type: Literal["refresh_data", "missing_in_crawl"],
    original_remark_l1: Optional[str],
    validated_price: float,
    agent_result: dict,
) -> dict:
    """
    Decide what to write to Remarks L1 and Remarks L2 based on a single
    agent's output.

    Args:
        row_type: "refresh_data" or "missing_in_crawl"
        original_remark_l1: current value of Remarks L1 (e.g. "Refresh data")
        validated_price: Original Price_validated from the Excel
        agent_result: parsed dict from the agent

    Returns:
        {
            "remark_l1": str or None,
            "remark_l2": str or None,
            "decision": str,
            "reasoning": str,
        }
    """
    a = agent_result
    redirected = a.get("url_redirected", False)
    price = a.get("price_found")
    confidence = a.get("confidence", "low")
    evidence = a.get("evidence", "")

    # ─────────────────────────────────────────────────────────
    # P1. Agent confirmed product is gone (redirect + no price)
    # ─────────────────────────────────────────────────────────
    if redirected and price is None:
        if row_type == "refresh_data":
            return {
                "remark_l1": "Missing-remove",
                "remark_l2": None,
                "decision": "AUTO_PRODUCT_GONE",
                "reasoning": "Agent detected redirect and no price; product gone.",
            }
        else:  # missing_in_crawl
            return {
                "remark_l1": "OK, missing",
                "remark_l2": None,
                "decision": "AUTO_CONFIRMED_MISSING",
                "reasoning": "Agent confirmed product is no longer on site.",
            }

    # ─────────────────────────────────────────────────────────
    # P2. Page was blocked (anti-bot, network error, etc.)
    # ─────────────────────────────────────────────────────────
    if _evidence_indicates_block(evidence):
        return {
            "remark_l1": original_remark_l1,
            "remark_l2": MANUAL_TAG,
            "decision": "LOW_CONFIDENCE_BLOCKED",
            "reasoning": f"Agent reported block: {evidence[:120]}",
        }

    # ─────────────────────────────────────────────────────────
    # P3. High confidence + price found -> trust the agent
    # ─────────────────────────────────────────────────────────
    if confidence == "high" and price is not None:
        if price_matches_validated(price, validated_price):
            # Price unchanged
            if row_type == "refresh_data":
                return {
                    "remark_l1": "Refresh data",
                    "remark_l2": "Same price",
                    "decision": "AUTO_REFRESH_SAME_PRICE",
                    "reasoning": (
                        f"Agent found {price} with high confidence, "
                        f"matches validated price {validated_price}."
                    ),
                }
            else:  # missing_in_crawl
                return {
                    "remark_l1": "Not OK, available",
                    "remark_l2": "Same price",
                    "decision": "AUTO_MISSING_BUT_AVAILABLE_SAME_PRICE",
                    "reasoning": (
                        f"Agent found {price} (matches validated), so "
                        "product is actually still on site. Crawler missed it."
                    ),
                }
        else:
            # Price has changed
            new_price_str = _format_price(price)
            if row_type == "refresh_data":
                return {
                    "remark_l1": "Refresh data",
                    "remark_l2": new_price_str,
                    "decision": "AUTO_REFRESH_NEW_PRICE",
                    "reasoning": (
                        f"Agent found {price} with high confidence, "
                        f"differs from validated {validated_price}."
                    ),
                }
            else:  # missing_in_crawl
                return {
                    "remark_l1": "Not OK, available",
                    "remark_l2": new_price_str,
                    "decision": "AUTO_MISSING_BUT_AVAILABLE_NEW_PRICE",
                    "reasoning": (
                        f"Agent found {price} (differs from validated "
                        f"{validated_price}), product still on site."
                    ),
                }

    # ─────────────────────────────────────────────────────────
    # P4. Anything else -> manual review
    # (medium/low confidence, null price without redirect, etc.)
    # ─────────────────────────────────────────────────────────
    return {
        "remark_l1": original_remark_l1,
        "remark_l2": MANUAL_TAG,
        "decision": "LOW_CONFIDENCE_NEEDS_REVIEW",
        "reasoning": (
            f"Confidence={confidence}, price={price}, redirected={redirected}. "
            "Single-agent pipeline escalates anything below 'high' confidence."
        ),
    }
