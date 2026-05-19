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

    print(f"\nWill process {len(sample_rows)} rows:")
    for row, idx in sample_rows:
        print(f"  - [row {idx}] {row['Brand']} / {row['Market']}")

    t_start = time.time()
    updates = []
    for i, (row, excel_row_index) in enumerate(sample_rows, 1):
        label = f"[{i}/{len(sample_rows)}]"
        try:
            update = await process_one_row(row, excel_row_index, label)
            updates.append(update)
        except Exception as e:
            print(f"\n❌ Row {excel_row_index} failed with exception: {e}")

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
