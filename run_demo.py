"""
End-to-end demo: run the single Claude agent on multiple rows,
reconcile, write back to a new Excel, and print a summary report.
"""
import asyncio
import json
import time
import pandas as pd

from agent_1 import verify_price_with_agent_1
from reconcile import reconcile
from excel_writer import make_output_path, write_reconciliation

# ============================================================
# Fail-fast environment checks
# Run these BEFORE doing anything expensive (like loading Excel
# or starting the browser). If a teammate forgot to set up their
# API key, we want to tell them immediately, not after they've
# already waited 30 seconds for the browser to launch.
# ============================================================
import os
import sys


def _check_environment() -> None:
    """Verify all required environment variables and config before run."""
    errors = []

    # 1. Anthropic API key must be present
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        errors.append(
            "ANTHROPIC_API_KEY is not set in your environment.\n"
            "  → See README section 'API Key Configuration' for setup.\n"
            "  → On macOS: add `export ANTHROPIC_API_KEY=\"sk-ant-...\"` "
            "to ~/.zshrc, then `source ~/.zshrc`."
        )
    elif not api_key.startswith("sk-ant-"):
        errors.append(
            f"ANTHROPIC_API_KEY is set but doesn't look like a Claude key.\n"
            f"  → Expected prefix: 'sk-ant-...'\n"
            f"  → Got prefix: '{api_key[:10]}...'\n"
            f"  → Did you accidentally paste an OpenAI or other key?"
        )

    # 2. Input Excel file must exist
    if not os.path.exists("To_be_update.xlsx"):
        errors.append(
            "Input file 'To_be_update.xlsx' not found in current directory.\n"
            f"  → Current directory: {os.getcwd()}\n"
            "  → Make sure you ran the script from the project root."
        )

    # 3. Report and abort if anything is wrong
    if errors:
        print("\n" + "=" * 70)
        print("❌ Cannot start: environment is not configured correctly.")
        print("=" * 70)
        for i, msg in enumerate(errors, 1):
            print(f"\n[{i}] {msg}")
        print("\n" + "=" * 70 + "\n")
        sys.exit(1)

    # All clear
    print("✓ Environment checks passed:")
    print(f"  - ANTHROPIC_API_KEY: present ({api_key[:10]}...)")
    print(f"  - Input file:        To_be_update.xlsx")
    print()


# Run checks immediately at import time
_check_environment()

INPUT_XLSX = "To_be_update.xlsx"

# Hand-picked sample of representative rows
SAMPLE_URLS = [
    "https://www.dior.com/fr_fr/fashion/products/S0856ONGE_M900",
    "https://www.dior.com/fr_fr/fashion/products/M9243UWHC_M900",
    "https://www.dior.com/en_us/fashion/products/M1296ZGSB_M900",
    "https://www.dior.com/en_us/fashion/products/S0856ONGE_M900",
    "https://www.dior.com/ko_kr/fashion/products/M1286ZRIW_M828",
    "https://www.dior.com/ja_jp/fashion/products/M6301UNOZ_M900",
    "https://www.dior.com/en_hk/fashion/products/M6302UNOZ_M900",
    "https://www.gucci.com/us/en/pr/women/handbags/shoulder-bags-for-women/ophidia-small-shoulder-bag-p-722117FAAX39789",
]


def classify_row_type(row) -> str:
    """Decide whether a row is 'refresh_data' or 'missing_in_crawl'."""
    if row["Remarks L1"] == "Refresh data":
        return "refresh_data"
    if row["status"] == "Missing in crawl":
        return "missing_in_crawl"
    raise ValueError(
        f"Row type unclear: status='{row['status']}', "
        f"Remarks L1='{row['Remarks L1']}'"
    )


async def process_one_row(row, excel_row_index: int, label: str) -> dict:
    """Run the agent on one row, reconcile, return an update dict."""
    print(f"\n{'=' * 70}")
    print(f"{label}  |  Excel row {excel_row_index}  |  "
          f"{row['Brand']} / {row['Market']}")
    print(f"URL: {row['Url']}")
    print(f"{'=' * 70}")

    row_type = classify_row_type(row)
    print(f"Row type: {row_type}")

    t0 = time.time()

    print("\n→ Agent (Claude) running...")
    a = await verify_price_with_agent_1(
        url=row["Url"],
        expected_price=float(row["Original Price_validated"]),
        expected_currency=row["currency_s"],
        product_name=row["Name"],
        market=row["Market"],
    )
    res = a["result"]
    print(f"  price_found = {res.get('price_found')}  "
          f"confidence = {res.get('confidence')}  "
          f"redirected = {res.get('url_redirected')}")

    decision = reconcile(
        row_type=row_type,
        original_remark_l1=row["Remarks L1"] if pd.notna(row["Remarks L1"]) else None,
        validated_price=float(row["Original Price_validated"]),
        agent_result=res,
    )

    elapsed = time.time() - t0

    print(f"\n→ Decision: {decision['decision']}  ({elapsed:.1f}s)")
    print(f"  Write: L1='{decision['remark_l1']}', L2='{decision['remark_l2']}'")

    return {
        "row_index": excel_row_index,
        "remark_l1": decision["remark_l1"],
        "remark_l2": decision["remark_l2"],
        "decision": decision["decision"],
        # Bookkeeping for the summary report
        "_brand": row["Brand"],
        "_market": row["Market"],
        "_row_type": row_type,
        "_price": res.get("price_found"),
        "_confidence": res.get("confidence"),
        "_validated_price": float(row["Original Price_validated"]),
        "_elapsed_seconds": elapsed,
    }


def print_summary(updates: list, total_elapsed: float) -> None:
    """Print a clean evaluation report."""
    print(f"\n\n{'#' * 70}")
    print(f"#  DEMO RUN SUMMARY (Single-Agent Pipeline)")
    print(f"{'#' * 70}\n")

    total = len(updates)
    if total == 0:
        print("No rows processed.")
        return

    auto = sum(1 for u in updates if u["decision"].startswith("AUTO_"))
    manual = sum(1 for u in updates if u["decision"].startswith("LOW_"))

    print(f"Total rows processed:    {total}")
    print(f"  AUTO (no human needed): {auto}  ({auto / total * 100:.0f}%)")
    print(f"  MANUAL (escalated):     {manual}  ({manual / total * 100:.0f}%)")
    print(f"\nTotal elapsed: {total_elapsed:.0f}s  "
          f"(avg {total_elapsed / total:.0f}s per row)")

    print(f"\n{'-' * 78}")
    print(f"DETAIL BY ROW")
    print(f"{'-' * 78}")
    print(f"{'Brand':<10} {'Mkt':<5} {'Type':<9} {'Price':<10} "
          f"{'Conf':<8} {'Decision'}")
    print(f"{'-' * 78}")
    for u in updates:
        rtype_short = "Refresh" if u["_row_type"] == "refresh_data" else "Missing"
        price = str(u["_price"]) if u["_price"] is not None else "null"
        conf = u["_confidence"] or "-"
        print(f"{u['_brand']:<10} {u['_market']:<5} {rtype_short:<9} "
              f"{price:<10} {conf:<8} {u['decision']}")

    print(f"\n{'-' * 78}")
    print(f"KEY METRICS")
    print(f"{'-' * 78}")
    print(f"  Automation rate:        {auto / total * 100:.0f}%")
    print(f"  Manual escalation rate: {manual / total * 100:.0f}%")


async def main():
    df = pd.read_excel(INPUT_XLSX)
    print(f"Loaded {len(df)} rows from {INPUT_XLSX}")

    sample_rows = []
    for url in SAMPLE_URLS:
        matches = df[df["Url"] == url]
        if len(matches) == 0:
            print(f"⚠️  URL not found in Excel, skipping: {url}")
            continue
        row = matches.iloc[0]
        excel_row_index = int(row.name) + 2
        sample_rows.append((row, excel_row_index))

    # ============================================================
    # Parallel execution with concurrency cap.
    #
    # Each task = one Chromium + one Claude call. The semaphore
    # ensures we never have more than MAX_CONCURRENT running at
    # once, which protects against:
    #   - RAM exhaustion (each browser ~300MB)
    #   - Anthropic per-minute token rate limits
    #   - System file descriptor exhaustion
    #
    # Start with 3 (conservative). If stable, bump to 5.
    # ============================================================
    MAX_CONCURRENT = 3
    sem = asyncio.Semaphore(MAX_CONCURRENT)

    print(f"\nWill process {len(sample_rows)} rows in parallel "
          f"(max {MAX_CONCURRENT} concurrent):")
    for row, idx in sample_rows:
        print(f"  - [row {idx}] {row['Brand']} / {row['Market']}")

    async def process_with_limit(row, excel_row_index, label):
        """Wrapper: hold semaphore while one row is being processed."""
        async with sem:
            try:
                return await process_one_row(row, excel_row_index, label)
            except Exception as e:
                print(f"\n❌ Row {excel_row_index} failed with exception: {e}")
                return None

    t_start = time.time()

    # Launch ALL tasks at once. The semaphore inside process_with_limit
    # holds the rest back so only MAX_CONCURRENT actually run.
    tasks = [
        process_with_limit(row, idx, f"[{i+1}/{len(sample_rows)}]")
        for i, (row, idx) in enumerate(sample_rows)
    ]
    raw_results = await asyncio.gather(*tasks)

    # Filter out the Nones from failed rows
    updates = [r for r in raw_results if r is not None]

    total_elapsed = time.time() - t_start

    output_path = make_output_path(INPUT_XLSX)
    write_updates = [
        {k: v for k, v in u.items() if not k.startswith("_")}
        for u in updates
    ]
    write_reconciliation(
        input_path=INPUT_XLSX,
        output_path=output_path,
        updates=write_updates,
    )

    print_summary(updates, total_elapsed)

    print(f"\n✅ Output: {output_path}")

if __name__ == "__main__":
    asyncio.run(main())
