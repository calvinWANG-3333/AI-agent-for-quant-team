"""
End-to-end demo: run both agents on multiple rows, reconcile,
write back to a new Excel, and print a summary report.
"""
import asyncio
import json
import time
import pandas as pd

from agent_1 import verify_price_with_agent_1
from agent_2 import verify_price_with_agent_2
from reconcile import reconcile
from excel_writer import make_output_path, write_reconciliation


INPUT_XLSX = "To_be_update.xlsx"

# Hand-picked sample of 8 representative rows
# Mix of Refresh data + Missing in crawl, multiple brands, easy markets
SAMPLE_URLS = [
    # Refresh data (5)
    "https://www.fendi.com/fr-fr/8BH394ABVLF0PWZ.html",
    "https://www.dior.com/fr_fr/fashion/products/S5573CRIW_M928",
    "https://www.dior.com/fr_fr/fashion/products/M1265ZRIW_M828",
    "https://www.chanel.com/gb/fashion/p/A35200Y0405994305/mini-classic-handbag-lambskin/",
    "https://www.fendi.com/fr-fr/8br798a5dyf1hej.html",
    # Missing in crawl (3)
    "https://www.dior.com/fr_fr/fashion/products/M9319UTZQ_M928",
    "https://www.dior.com/fr_fr/fashion/products/M9203UMOS_M911",
    "https://www.chanel.com/fr/mode/p/A35200Y0405994305/mini-sac-classique-agneau-metal-dore/",
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
    """Run both agents on one row, reconcile, return an update dict."""
    print(f"\n{'=' * 70}")
    print(f"{label}  |  Excel row {excel_row_index}  |  "
          f"{row['Brand']} / {row['Market']}")
    print(f"URL: {row['Url']}")
    print(f"{'=' * 70}")

    row_type = classify_row_type(row)
    print(f"Row type: {row_type}")

    t0 = time.time()

    # --- Agent 1 ---
    print("\n→ Agent 1 (Claude) running...")
    a1 = await verify_price_with_agent_1(
        url=row["Url"],
        expected_price=float(row["Original Price_validated"]),
        expected_currency=row["currency_s"],
        product_name=row["Name"],
        market=row["Market"],
    )
    print(f"  price_found = {a1['result'].get('price_found')}")

    # --- Agent 2 ---
    print("\n→ Agent 2 (GPT-4o) running...")
    a2 = await verify_price_with_agent_2(
        url=row["Url"],
        expected_price=float(row["Original Price_validated"]),
        expected_currency=row["currency_s"],
        product_name=row["Name"],
        market=row["Market"],
    )
    print(f"  price_found = {a2['result'].get('price_found')}")

    # --- Reconcile ---
    decision = reconcile(
        row_type=row_type,
        original_remark_l1=row["Remarks L1"] if pd.notna(row["Remarks L1"]) else None,
        validated_price=float(row["Original Price_validated"]),
        agent_1_result=a1["result"],
        agent_2_result=a2["result"],
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
        "_a1_price": a1["result"].get("price_found"),
        "_a2_price": a2["result"].get("price_found"),
        "_validated_price": float(row["Original Price_validated"]),
        "_elapsed_seconds": elapsed,
    }


def print_summary(updates: list, total_elapsed: float) -> None:
    """Print a clean evaluation report."""
    print(f"\n\n{'#' * 70}")
    print(f"#  DEMO RUN SUMMARY")
    print(f"{'#' * 70}\n")

    total = len(updates)
    auto = sum(1 for u in updates if u["decision"].startswith("AUTO_"))
    manual = sum(1 for u in updates if u["decision"].startswith("LOW_"))

    print(f"Total rows processed:    {total}")
    print(f"  AUTO (no human needed): {auto}  ({auto / total * 100:.0f}%)")
    print(f"  MANUAL (escalated):     {manual}  ({manual / total * 100:.0f}%)")
    print(f"\nTotal elapsed: {total_elapsed:.0f}s  "
          f"(avg {total_elapsed / total:.0f}s per row)")

    print(f"\n{'-' * 70}")
    print(f"DETAIL BY ROW")
    print(f"{'-' * 70}")
    print(f"{'Brand':<12} {'Mkt':<5} {'Type':<10} {'A1 Price':<10} "
          f"{'A2 Price':<10} {'Decision'}")
    print(f"{'-' * 70}")
    for u in updates:
        rtype_short = "Refresh" if u["_row_type"] == "refresh_data" else "Missing"
        a1p = str(u["_a1_price"]) if u["_a1_price"] is not None else "null"
        a2p = str(u["_a2_price"]) if u["_a2_price"] is not None else "null"
        print(f"{u['_brand']:<12} {u['_market']:<5} {rtype_short:<10} "
              f"{a1p:<10} {a2p:<10} {u['decision']}")

    print(f"\n{'-' * 70}")
    print(f"KEY METRICS")
    print(f"{'-' * 70}")
    print(f"  Automation rate: {auto / total * 100:.0f}%")
    print(f"  Manual escalation rate: {manual / total * 100:.0f}%")


async def main():
    # 1. Load Excel
    df = pd.read_excel(INPUT_XLSX)
    print(f"Loaded {len(df)} rows from {INPUT_XLSX}")

    # 2. Find each sample URL in the dataframe
    sample_rows = []
    for url in SAMPLE_URLS:
        matches = df[df["Url"] == url]
        if len(matches) == 0:
            print(f"⚠️  URL not found in Excel, skipping: {url}")
            continue
        row = matches.iloc[0]
        excel_row_index = int(row.name) + 2  # +1 for header, +1 because pandas is 0-indexed
        sample_rows.append((row, excel_row_index))

    print(f"\nWill process {len(sample_rows)} rows:")
    for row, idx in sample_rows:
        print(f"  - [row {idx}] {row['Brand']} / {row['Market']}")

    # 3. Process each row sequentially
    t_start = time.time()
    updates = []
    for i, (row, excel_row_index) in enumerate(sample_rows, 1):
        label = f"[{i}/{len(sample_rows)}]"
        try:
            update = await process_one_row(row, excel_row_index, label)
            updates.append(update)
        except Exception as e:
            print(f"\n❌ Row {excel_row_index} failed with exception: {e}")
            # Continue with the rest; don't let one bad row crash everything

    total_elapsed = time.time() - t_start

    # 4. Write to a new Excel
    output_path = make_output_path(INPUT_XLSX)
    # Strip bookkeeping fields before writing
    write_updates = [
        {k: v for k, v in u.items() if not k.startswith("_")}
        for u in updates
    ]
    write_reconciliation(
        input_path=INPUT_XLSX,
        output_path=output_path,
        updates=write_updates,
    )

    # 5. Summary report
    print_summary(updates, total_elapsed)

    print(f"\n✅ Output: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())