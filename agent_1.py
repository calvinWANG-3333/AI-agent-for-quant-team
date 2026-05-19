"""
Agent 1: Price verification agent using Claude in DOM mode.

This is the SOLE agent in the production pipeline. The previous dual-agent
architecture (see deprecated_agent_2.py for the GPT-4o variant) has been
retired to halve LLM costs.

Because there is no longer a second agent to cross-validate, the
'confidence' field carries more weight: when confidence is medium or low,
the row is escalated to manual review by reconcile.py.

Workflow:
  1. Open product URL on a luxury brand website
  2. Detect URL redirects (which indicate the product is gone)
  3. If product is found, read its current price from the page
  4. Self-assess confidence using the strict rubric below
  5. Return a structured JSON result with anti-hallucination safeguards
"""
import logging
# Silence noisy retry warnings from browser-use 0.12.6's known DOM bug.
# These warnings do not affect functionality but flood the console.
logging.getLogger("browser_use.browser").setLevel(logging.ERROR)
logging.getLogger("bubus").setLevel(logging.ERROR)
logging.getLogger("cdp_use").setLevel(logging.ERROR)

import asyncio
import json
from pydantic import BaseModel, Field
from typing import Optional, Literal

from browser_use import Agent, Controller, BrowserProfile
from browser_use.llm import ChatAnthropic


# ============================================================
# 1. Structured output schema
# ============================================================
class PriceVerificationResult(BaseModel):
    """Strict schema Agent 1 must follow when returning its findings."""

    product_available: Literal["yes", "no", "uncertain"] = Field(
        description=(
            "Is the original product still on sale at the original URL? "
            "'yes' = product page renders with the correct product name "
            "AND a visible price; "
            "'no' = redirected to homepage/category/search page, OR page "
            "shows 404/sold out/no longer available; "
            "'uncertain' = page failed to load, was blocked, or unclear."
        )
    )

    url_redirected: bool = Field(
        description=(
            "Did the browser end up on a different URL than the one you "
            "opened? Note: many luxury sites rewrite URLs to SEO-friendly "
            "slugs while STAYING on the same product page. That is NOT a "
            "redirect away from the product. Only set true if the final URL "
            "is a homepage, category, or search page."
        )
    )

    final_url: Optional[str] = Field(
        default=None,
        description="The URL after the page finished loading."
    )

    price_found: Optional[float] = Field(
        default=None,
        description=(
            "The current price of THIS product as a plain number. "
            "Example: '€2,000.00' becomes 2000.0. "
            "STRICT: if url_redirected is true, OR you cannot clearly see "
            "a price for THIS specific product, set this to null. "
            "NEVER guess, NEVER echo the reference price."
        )
    )

    currency_found: Optional[str] = Field(
        default=None,
        description=(
            "Currency as a 3-letter ISO code (EUR, USD, GBP, JPY, CNY). "
            "Return null if price_found is null."
        )
    )

    evidence: str = Field(
        description=(
            "What you actually observed on the page. Quote DOM content "
            "where possible. If blocked, start with 'BLOCKED: ...'. "
            "Describe observations, not expectations."
        )
    )

    confidence: Literal["high", "medium", "low"] = Field(
        description=(
            "STRICT confidence rubric (we now rely on this for auto vs "
            "manual escalation, since there is no second agent to cross-check):"
            "\n"
            "  'high' — ALL of: (1) exactly one main product price clearly "
            "visible in DOM, (2) product name on page matches the requested "
            "name closely, (3) page is a proper product page (not blocked, "
            "not partially loaded), (4) no ambiguity from sale/regular price "
            "or installments confused with main price."
            "\n"
            "  'medium' — Price was found but at least one of: multiple "
            "prices visible (sale vs regular, variants with different "
            "prices), product name only partially matches, page seems to "
            "have rendered only partially, or you used reasoning to pick "
            "among candidates."
            "\n"
            "  'low' — Any of: price not visible, page blocked, redirect "
            "detected, product name does not match, page failed to load, "
            "or you are guessing."
            "\n"
            "When in doubt between two levels, choose the LOWER one. "
            "False 'high' confidence causes downstream errors that "
            "human review would have caught."
        )
    )


# ============================================================
# 2. Main function: run Agent 1 on a single URL
# ============================================================
async def verify_price_with_agent_1(
    url: str,
    expected_price: float,
    expected_currency: str,
    product_name: str,
    market: str,
) -> dict:
    """Use Claude + browser-use (DOM mode) to extract the current price."""

    controller = Controller(output_model=PriceVerificationResult)
    llm = ChatAnthropic(model="claude-sonnet-4-5")

    browser_profile = BrowserProfile(
        minimum_wait_page_load_time=3.0,
    )

    task = f"""
You are a price verification agent for a luxury goods analytics company.

YOUR TASK
Open this URL: {url}

Find the current selling price of this product, IF it is still available:
- Product name: "{product_name}"
- Market: {market}
- Expected currency: {expected_currency}
- Reference price on file (FOR CONTEXT ONLY, DO NOT ECHO): {expected_price} {expected_currency}

You are working in DOM mode. You read the page HTML structure, not screenshots.

==========================================================================
EARLY-TERMINATION RULES (HIGHEST PRIORITY - check FIRST after page loads)
==========================================================================

If you observe ANY of the following, STOP IMMEDIATELY and return null.
Do NOT retry, do NOT wait, do NOT navigate elsewhere.

  - "Access Denied" / "Acces refuse" / "Zugriff verweigert"
  - HTTP 403 Forbidden / "Forbidden" message
  - Cloudflare challenge / "Checking your browser" / "Just a moment..."
  - CAPTCHA / hCaptcha / reCAPTCHA / "I am not a robot"
  - "Too many requests" / 429 rate limit message
  - PerimeterX / DataDome / Akamai block screens
  - ERR_TUNNEL_CONNECTION_FAILED / ERR_CONNECTION_REFUSED / DNS errors
  - Page is entirely a blocking message with no product info

When blocked, return:
  product_available = "uncertain"
  url_redirected    = false
  price_found       = null
  currency_found    = null
  evidence          = "BLOCKED: [what you saw, e.g. 'Access Denied page']"
  confidence        = "low"

A blocked page will NEVER load. Recognize quickly and exit.

==========================================================================
STEPS (if not blocked)
==========================================================================

1. Open the URL.
2. After the page loads, observe the final URL in the browser address bar.
3. CHECK FOR REDIRECT:
   - If the final URL is the same product page (possibly with an SEO slug
     rewrite that still contains the product code), continue.
   - If the final URL is homepage, category page, or search page, the
     product is gone. Set url_redirected=true, product_available="no",
     price_found=null. Do NOT search for the product.
4. If no redirect, confirm the product name on the page matches
   "{product_name}" closely.
5. Extract the price for THIS specific product from the DOM.
6. Self-assess your confidence using the rubric in the schema.
7. Return the structured output.

==========================================================================
CRITICAL ANTI-HALLUCINATION RULES
==========================================================================

Rule 1 — Never fabricate prices.
   If the price is not clearly in the DOM, price_found MUST be null.
   We have been burned before by an AI inventing prices. Null is correct
   behavior when uncertain.

Rule 2 — The reference price is for context, not for you to echo.
   The reference price tells you what is on file. It is NOT the answer.
   Read the actual price from the page DOM. If you cannot find it, null.

Rule 3 — Redirects mean "product is gone", not "try harder".
   If redirected, do not browse, search, or navigate. Report and stop.

Rule 4 — Evidence must be what you SAW, not what you expected.
   Quote DOM content where possible.

Rule 5 — Be conservative with confidence.
   This system no longer has a second agent to cross-check you. A row
   marked 'high' confidence will be written to the output Excel
   automatically. If you have ANY doubt, mark it 'medium' or 'low' so
   it gets human review. False 'high' costs more than false 'medium'.

Be honest. Null is correct when uncertain. Fabrication is forbidden.
"""

    agent = Agent(
        task=task,
        llm=llm,
        controller=controller,
        browser_profile=browser_profile,
        use_vision=False,
        # Defensive: explicitly force navigation as the first action.
        # Claude usually navigates on its own, but we don't rely on that.
        initial_actions=[
            {'navigate': {'url': url, 'new_tab': False}}
        ],
    )

    history = await agent.run(max_steps=8)
    final_result = history.final_result()

    if final_result:
        parsed = json.loads(final_result)
    else:
        parsed = {
            "product_available": "uncertain",
            "url_redirected": False,
            "final_url": None,
            "price_found": None,
            "currency_found": None,
            "evidence": "Agent failed to produce a final result.",
            "confidence": "low",
        }

    return {
        "url": url,
        "expected_price": expected_price,
        "expected_currency": expected_currency,
        "product_name": product_name,
        "market": market,
        "result": parsed,
    }


# ============================================================
# 3. Entry point: test on one real URL
# ============================================================
async def main():
    print("=" * 70)
    print("Agent 1 standalone test: Fendi (single-agent mode)")
    print("=" * 70)

    result = await verify_price_with_agent_1(
        url="https://www.dior.com/fr_fr/fashion/products/S5573CRIW_M928",
        expected_price=2150.0,
        expected_currency="EUR",
        product_name="Sac Dior Book Tote Mini",
        market="FRA",
    )

    print("\n" + "=" * 70)
    print("Agent 1 result")
    print("=" * 70)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())

