"""
Agent 1: Price verification agent using Claude in DOM mode.

Workflow:
  1. Open product URL on a luxury brand website
  2. Detect URL redirects (which indicate the product is gone)
  3. If product is found, read its current price from the page HTML
  4. Compare against the expected price from our records
  5. Return a structured JSON result with strict anti-hallucination safeguards

Strategy:
  - DOM mode (use_vision=False): faster, cheaper, more reliable on slow
    JS-heavy luxury sites than screenshot-based vision mode.
  - Cross-model independence will come from Agent 2 using GPT-4o.

First test target: Fendi (low anti-bot complexity).
"""
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
            "'yes' = product page renders with the correct product name and a "
            "visible price; "
            "'no' = the URL was redirected to homepage/category page/search "
            "page, OR the page shows 404, 'product not found', 'sold out', "
            "or 'no longer available'; "
            "'uncertain' = page failed to load, was blocked, or content unclear."
        )
    )

    url_redirected: bool = Field(
        description=(
            "Did the browser end up on a different URL than the one you opened? "
            "Luxury sites often redirect dead product URLs to the homepage, "
            "category page, or a search page."
        )
    )

    final_url: Optional[str] = Field(
        default=None,
        description="The URL after the page finished loading. Null if unknown."
    )

    price_found: Optional[float] = Field(
        default=None,
        description=(
            "The current price shown on the page as a plain number. "
            "Example: '€2,000.00' becomes 2000.0. "
            "STRICT: if url_redirected is true, OR you cannot clearly see "
            "a price for THIS product, set this to null. "
            "NEVER guess. NEVER echo the reference price. "
            "Null is the correct answer when uncertain."
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
            "What you actually observed. Examples: "
            "'Page DOM contains <span class=price>€2,000.00</span> next to "
            "product title Fendi Sunshine Small.' OR "
            "'Browser redirected from /products/X to homepage. Product not "
            "listed.' OR 'Page returned Cloudflare challenge.' "
            "Describe observations, not expectations."
        )
    )

    confidence: Literal["high", "medium", "low"] = Field(
        description=(
            "'high' = price clearly in DOM and product name matches; "
            "'medium' = some ambiguity (sale price vs regular, etc); "
            "'low' = unsure or no price found."
        )
    )


# ============================================================
# 2. Main function
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

    # Browser tuned for slow luxury sites
    browser_profile = BrowserProfile(
    # Give SPA-heavy luxury sites enough time to fully render
    default_navigation_timeout=45_000,         # 45 sec for navigation
    minimum_wait_page_load_time=3.0,           # always wait >= 3s after load
    wait_for_network_idle_page_load_time=3.0,  # wait for network to settle
    maximum_wait_page_load_time=10.0,          # but cap at 10s
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
Look for price information in HTML elements (often inside <span>, <div>,
<meta>, or <script type="application/ld+json"> tags with class names or
attributes containing "price", "amount", "value", or similar).

STEPS
1. Open the URL.
2. After the page loads, observe the final URL in the address bar.
3. CHECK FOR REDIRECT:
   - If the final URL is the same as the one you opened (or trivially
     different), continue.
   - If the final URL is the homepage, a category page, or a search page,
     the product is gone. Set url_redirected = true, product_available = "no",
     price_found = null. Do NOT search for the product.
4. If no redirect, find the product name on the page. It should match
   "{product_name}" closely.
5. Extract the price from the DOM.
6. Return your findings in the required structured format.

CRITICAL ANTI-HALLUCINATION RULES

Rule 1 — Never fabricate prices.
   If the price is not clearly in the DOM, price_found MUST be null. We have
   been burned before by an AI that invented a price when it could not find
   one. Returning null is correct behavior. Fabricating a number causes
   real financial damage.

Rule 2 — The reference price is for context, not for you to echo.
   The reference price tells you what is on file. It is NOT the answer.
   Read the actual price from the page DOM. If you cannot find it, return null.

Rule 3 — Redirects mean "product is gone", not "try harder".
   If redirected, do not browse, search, or navigate to find a similar
   product. Just report the redirect and stop.

Rule 4 — Evidence must be what you SAW, not what you expected.
   Quote DOM content where possible.

EARLY-TERMINATION RULES (highest priority - check FIRST after page loads)

If at ANY point you observe ANY of the following, STOP IMMEDIATELY.
Do NOT retry, do NOT wait, do NOT navigate elsewhere. Return the result
described below and exit.

  - Page shows "Access Denied" / "Acces refuse" / "Zugriff verweigert"
  - Page shows HTTP 403 Forbidden
  - Page shows a Cloudflare challenge / "Checking your browser"
  - Page shows a CAPTCHA / "I am not a robot"
  - Page shows "Too many requests" / 429 rate limit message
  - Page shows a PerimeterX / DataDome / Akamai block screen
  - The entire visible content is a blocking message with no product info

→ When you see any of the above, return IMMEDIATELY with:
  - product_available = "uncertain"
  - url_redirected = false
  - price_found = null
  - currency_found = null
  - evidence = "BLOCKED: [describe what blocked you, e.g. 'Cloudflare
    challenge page', 'Access Denied (HTTP 403)', 'CAPTCHA presented']"
  - confidence = "low"

This rule has higher priority than "wait for the page to load". A blocked
page will NEVER load no matter how long you wait. Recognize and exit.

Be concise. Null is correct when uncertain. Fabrication is forbidden.
"""

    agent = Agent(
        task=task,
        llm=llm,
        controller=controller,
        browser_profile=browser_profile,
        use_vision=False,   # DOM mode: faster, cheaper, more reliable
        initial_actions=[
            {'navigate': {'url': url, 'new_tab': False}}
        ]
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
# 3. Entry point
# ============================================================
async def main():
    print("=" * 70)
    print("Agent 1 test (DOM mode): Fendi")
    print("=" * 70)

    result = await verify_price_with_agent_1(
        url="https://www.fendi.com/fr-fr/8BH394ABVLF0PWZ.html",
        expected_price=2000.0,
        expected_currency="EUR",
        product_name="Fendi Sunshine Small",
        market="FRA",
    )

    print("\n" + "=" * 70)
    print("Agent 1 result")
    print("=" * 70)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())