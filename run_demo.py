"""
End-to-end production runner.

Reads `To_be_update.xlsx` from the current working directory, runs the
single Claude agent on every eligible row, reconciles each result, and
writes the annotated output to `To_be_update_filled.xlsx`.

Crash-safe: partial results are flushed to the output Excel every
CHECKPOINT_EVERY completed rows, so if the run is interrupted (network,
API limit, accidental Ctrl-C, browser crash) no work is lost — the rows
that DID finish are already on disk.

A row is "eligible" iff:
  - Remarks L1 == "Refresh data"      (row_type = refresh_data)
  - OR status == "Missing in crawl"   (row_type = missing_in_crawl)
  - AND has a non-empty Url
  - AND has a non-null Original Price_validated

Rows that don't meet these conditions are silently left untouched in the
output (i.e. they keep whatever the human reviewer wrote, or remain blank
if they were never reviewed).

USAGE:
    python run_demo.py
"""
import asyncio
import os
import sys
import time
import pandas as pd

from agent_1 import verify_price_with_agent_1
from reconcile import reconcile
from excel_writer import make_output_path, write_reconciliation


# ============================================================
# Configuration — tweak only if you know what you're doing.
# ============================================================
INPUT_XLSX = "To_be_update.xlsx"

# Max number of Chromium+Claude tasks running in parallel.
# Each task uses ~300 MB RAM and ~3-5 K input tokens per minute.
#   - 3 = safe default (Tier-1 Anthropic accounts, any laptop)
#   - 5 = aggressive; only raise this if you've already validated 3
#         works cleanly on your machine AND your Anthropic account
#         is Tier-2+ (i.e. has been topped up).
MAX_CONCURRENT = 3

# Flush partial results to the output Excel every N completed rows.
# Lower = safer (less work lost on crash) but more disk writes.
CHECKPOINT_EVERY = 10

# Brands that should NEVER reach the agent. They require manual review
# per the team's onboarding guide (Loewe — region switching; AP — direct
# brand feed; Hermès — sometimes store-only data). The pre-flight check
# below warns if any of them are present in the input file.
EXCLUDED_BRANDS = {"Loewe", "AudemarsPiguet", "AP", "Hermès", "Hermes"}


# ============================================================
# Fail-fast environment checks.
# Run BEFORE doing anything expensive (Excel load, browser launch).
# ============================================================
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
    if not os.path.exists(INPUT_XLSX):
        errors.append(
            f"Input file '{INPUT_XLSX}' not found in current directory.\n"
            f"  → Current directory: {os.getcwd()}\n"
            "  → Make sure you ran the script from the project root, "
            "and that your prepared file is named exactly "
            f"'{INPUT_XLSX}' (see README 'Input Preparation Guide')."
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
    print(f"  - Input file:        {INPUT_XLSX}")
    print()


# Run checks immediately at import time
_check_environment()


# ============================================================
# Row eligibility + classification
# ============================================================
def classify_row_type(row) -> str:
    """Decide whether a row is 'refresh_data' or 'missing_in_crawl'."""
    if row.get("Remarks L1") == "Refresh data":
        return "refresh_data"
    if row.get("status") == "Missing in crawl":
        return "missing_in_crawl"
    raise ValueError(
        f"Row type unclear: status='{row.get('status')}', "
        f"Remarks L1='{row.get('Remarks L1')}'"
    )


def is_eligible_row(row) -> bool:
    """Return True iff this row should be sent to the agent."""
    is_refresh = row.get("Remarks L1") == "Refresh data"
    is_missing = row.get("status") == "Missing in crawl"
    if not (is_refresh or is_missing):
        return False
    if pd.isna(row.get("Url")) or not str(row.get("Url")).strip():
        return False
    if pd.isna(row.get("Original Price_validated")):
        return False
    return True


# ============================================================
# Per-row processing
# ============================================================
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


# ============================================================
# Output helpers
# ============================================================
def _flush_checkpoint(output_path: str, updates: list) -> None:
    """Rewrite the output Excel with the current cumulative updates list.

    write_reconciliation() starts by copying INPUT_XLSX over output_path,
    then applies ALL updates from scratch. That means calling this
    repeatedly with a growing updates list is correct and idempotent:
    the output file always reflects the full current state.
    """
    write_updates = [
        {k: v for k, v in u.items() if not k.startswith("_")}
        for u in updates
    ]
    write_reconciliation(
        input_path=INPUT_XLSX,
        output_path=output_path,
        updates=write_updates,
    )


def print_summary(updates: list, total_elapsed: float, n_failed: int) -> None:
    """Print a clean evaluation report."""
    print(f"\n\n{'#' * 70}")
    print(f"#  RUN SUMMARY (Single-Agent Pipeline)")
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
    if n_failed:
        print(f"  FAILED (exception):     {n_failed}  "
              f"— see '❌ Row' lines above")
    print(f"\nTotal elapsed: {total_elapsed:.0f}s  "
          f"(avg {total_elapsed / total:.0f}s per row)")

    print(f"\n{'-' * 78}")
    print(f"DETAIL BY ROW")
    print(f"{'-' * 78}")
    print(f"{'Brand':<14} {'Mkt':<5} {'Type':<9} {'Price':<10} "
          f"{'Conf':<8} {'Decision'}")
    print(f"{'-' * 78}")
    for u in updates:
        rtype_short = "Refresh" if u["_row_type"] == "refresh_data" else "Missing"
        price = str(u["_price"]) if u["_price"] is not None else "null"
        conf = u["_confidence"] or "-"
        print(f"{u['_brand']:<14} {u['_market']:<5} {rtype_short:<9} "
              f"{price:<10} {conf:<8} {u['decision']}")

    print(f"\n{'-' * 78}")
    print(f"KEY METRICS")
    print(f"{'-' * 78}")
    print(f"  Automation rate:        {auto / total * 100:.0f}%")
    print(f"  Manual escalation rate: {manual / total * 100:.0f}%")


# ============================================================
# Main
# ============================================================
async def main():
    df = pd.read_excel(INPUT_XLSX)
    print(f"Loaded {len(df)} rows from {INPUT_XLSX}")

    # ─────────────────────────────────────────────────────────
    # Pre-flight: warn if excluded brands slipped in.
    # We don't auto-remove them — the operator should know.
    # ─────────────────────────────────────────────────────────
    brands_in_file = set(df["Brand"].dropna().unique())
    leaked = brands_in_file & EXCLUDED_BRANDS
    if leaked:
        print(f"\n⚠️  WARNING: input contains excluded brand(s): "
              f"{sorted(leaked)}")
        print("   The agent is not validated against these brands. They "
              "will still be processed, but the recommended workflow is")
        print("   to remove them manually before running (see README "
              "'Input Preparation Guide').\n")

    # ─────────────────────────────────────────────────────────
    # Build the work list.
    # excel_row_index = pandas 0-based index + 2  (header row + 1-based)
    # ─────────────────────────────────────────────────────────
    eligible_rows = []
    for idx, row in df.iterrows():
        if not is_eligible_row(row):
            continue
        excel_row_index = int(idx) + 2
        eligible_rows.append((row, excel_row_index))

    if not eligible_rows:
        print("No eligible rows found. Nothing to do.")
        return

    output_path = make_output_path(INPUT_XLSX)

    print(f"\nWill process {len(eligible_rows)} eligible rows in parallel "
          f"(max {MAX_CONCURRENT} concurrent).")
    print(f"Checkpointing every {CHECKPOINT_EVERY} completed rows to: "
          f"{output_path}")
    print(f"  → If anything crashes, completed rows so far are already "
          f"on disk.\n")

    # ─────────────────────────────────────────────────────────
    # Parallel execution with concurrency cap.
    #
    # Each task = one Chromium + one Claude call. The semaphore
    # ensures we never have more than MAX_CONCURRENT running at
    # once, which protects against:
    #   - RAM exhaustion (each browser ~300 MB)
    #   - Anthropic per-minute token rate limits
    #   - System file descriptor exhaustion
    #
    # checkpoint_lock guards the shared `updates` list AND the
    # disk write — two coroutines must not write the same Excel
    # at the same time.
    # ─────────────────────────────────────────────────────────
    sem = asyncio.Semaphore(MAX_CONCURRENT)
    updates: list = []
    checkpoint_lock = asyncio.Lock()

    async def process_with_limit(row, excel_row_index, label):
        async with sem:
            try:
                update = await process_one_row(row, excel_row_index, label)
            except Exception as e:
                print(f"\n❌ Row {excel_row_index} failed with exception: "
                      f"{type(e).__name__}: {e}")
                return None

            async with checkpoint_lock:
                updates.append(update)
                if len(updates) % CHECKPOINT_EVERY == 0:
                    print(f"\n💾 Checkpoint: {len(updates)} rows done, "
                          f"flushing to {output_path}...")
                    _flush_checkpoint(output_path, updates)

            return update

    t_start = time.time()

    tasks = [
        process_with_limit(row, idx, f"[{i+1}/{len(eligible_rows)}]")
        for i, (row, idx) in enumerate(eligible_rows)
    ]
    raw_results = await asyncio.gather(*tasks)
    total_elapsed = time.time() - t_start

    # Final flush — always, even if the last batch wasn't on a
    # checkpoint boundary.
    _flush_checkpoint(output_path, updates)

    n_failed = sum(1 for r in raw_results if r is None)
    print_summary(updates, total_elapsed, n_failed)

    print(f"\n✅ Output: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
