# AI-agent-for-quant-team
# Luxury Price Reconciliation Agent

[![Python Version](https://img.shields.io/badge/Python-3.11-blue.svg?style=flat-square&logo=python)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Framework-Browser--Use-orange.svg?style=flat-square)](https://github.com/browser-use/browser-use)
[![Automation](https://img.shields.io/badge/Driver-Playwright-green.svg?style=flat-square&logo=playwright)](https://playwright.dev/)
[![Architecture](https://img.shields.io/badge/Architecture-Native--ARM64-red.svg?style=flat-square&logo=apple)](https://developer.apple.com/apple-silicon/)

An enterprise-grade automated reconciliation system (Web Agent) powered by **Browser-Use** and **Claude 3.5 Sonnet**. This system automates the end-to-end workflow of fetching, parsing, and validating real-time product prices and inventory statuses from global luxury brand websites (e.g., Fendi, Dior, Chanel, YSL) against internal financial data structures (Excel), automatically executing backfills, and flagging audit mismatches.

---

## ⚡ Critical Performance Warning (Rosetta 2 Overhead)

> [!CAUTION]
> **Avoid Rosetta 2 Architecture Pollution on Apple Silicon Macs!**
> This project standardizes on native ARM64 Python via `uv` to ensure clean dependency resolution and consistent runtime behavior across team members. While the dominant performance bottlenecks in this agent are network latency and LLM inference time, running under Rosetta 2 emulation adds measurable overhead to DOM parsing and package import. A native ARM64 venv eliminates this overhead and also avoids the dependency conflicts that arise from mixing Anaconda's globally-installed packages with project-specific ones.
>
> **Impact:** Processing a single product URL under emulation takes **4 to 5 minutes**. By enforcing a **pure native Apple Silicon (aarch64/arm64)** execution space via this setup guide, DOM parsing efficiency increases 10x, reducing single-URL execution down to **20 to 40 seconds**.

---

## 🛠️ Environment Configuration Guide

To eliminate global dependency drift and avoid heavy, fragmented `Anaconda` environments, this project standardizes environment isolation and deterministic package synchronization using **`uv`**, a hyper-fast Python package manager written in Rust.

### 1. Apple Silicon (M1/M2/M3/M4) macOS Setup

#### Step 1: Verify Host Terminal Architecture
Open your native macOS Terminal or iTerm2 and execute:
```bash
arch
```
* **If it outputs `x86_64` (⚠️ Action Required)**: Your terminal application is locked under Rosetta 2 emulation. Completely quit the terminal. Open `Finder -> Applications`, locate your terminal app icon, right-click and select **Get Info**. **Uncheck the "Open using Rosetta" checkbox**. Relaunch the terminal.
* **If it outputs `arm64` (✅ Optimal)**: Your terminal environment is native. Proceed to the next step.

#### Step 2: Purge Conflicted Virtual Environments
Navigate to the repository root and destroy any pre-existing, poisoned virtual environments:
```bash
cd ~/path/to/your/agent_project
rm -rf .venv
```

#### Step 3: Provision a Native Apple Silicon Virtual Environment
Force `uv` to pull and isolate a pure ARM64 Python interpreter by explicitly targeting the `aarch64` target:
```bash
uv venv --python cpython-3.11-macos-aarch64 .venv
```

#### Step 4: Activate Environment and Synchronize Dependencies
```bash
# Activate the isolated project environment
source .venv/bin/activate

# Install the exact dependency tree (This completely overrides and bypasses global Anaconda overrides)
uv pip install -r requirements.txt
```

#### Step 5: Install Native ARM64 Browser Binaries
Since your isolated Python space is now verified `aarch64`, the Playwright automated driver utility will bypass translation layers and provision a native Apple Silicon compiled Chromium binary:
```bash
uv run playwright install chromium
```

---

### 2. Windows 11 / 10 Enterprise Setup

Windows hosts do not encounter architecture translation penalties, but must follow strict sandboxed isolation.

#### Step 1: Bootstrap the `uv` Toolchain via PowerShell
Open **PowerShell** (Do NOT use the legacy CMD prompt) and execute the official installer:
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
Once complete, **restart your PowerShell window** to register the environment variables, and verify with `uv --version`.

#### Step 2: Initialize and Isolate the Environment
```powershell
# Navigate to project repository
cd C:\path\to\your\agent_project

# Force delete legacy env artifacts
Remove-Item -Recurse -Force .venv

# Bootstrap a clean Python 3.11 runtime environment
uv venv --python 3.11

# Activate the environment via execution policy wrapper
.venv\Scripts\Activate.ps1
```

#### Step 3: Sync Dependencies and Headless Browsers
Within the activated virtual environment (`(.venv)` should be visible in the prompt prefix), execute:
```powershell
uv pip install -r requirements.txt
uv run playwright install chromium
```

---

## 🔐 API Key Configuration (Required Before First Run)

This agent utilizes the Anthropic Claude API via `browser-use` to drive intelligent web navigation. You must configure your Claude API key as an environment variable before running `run_demo.py`. The orchestration script will explicitly refuse to boot if the key is missing to prevent silent failures mid-run.

> [!IMPORTANT]
> **`venv` and environment variables are two unrelated things.**
> * `venv` **only isolates Python packages** (where `pandas`, `playwright`, etc. live on disk). It has **no influence whatsoever** on shell environment variables.
> * `export ANTHROPIC_API_KEY=...` is a **shell-level** instruction. Whether your venv is activated or not, any Python process started from that shell can read it via `os.environ.get("ANTHROPIC_API_KEY")`.
>
> The recommended pattern below — writing one `export` line into `~/.zshrc` — gives you a key that survives terminal restarts, venv rebuilds, project switches, and machine reboots, with **zero leakage risk** (because `~/.zshrc` is `chmod 600` — readable only by you).

### 1. Provision an Anthropic API Key
If you are joining the project team, **do not reuse another developer's key**. Every engineer must provision an individual credential for audit logging and usage tracking.

1. Sign in to the [Anthropic Console](https://console.anthropic.com/).
2. Navigate to **Settings** → **API Keys** → Click **Create Key**.
3. Copy the generated string immediately (prefixed with `sk-ant-...`). *Note: It will be permanently obscured after closing the modal.*

> [!CAUTION]
> **Credential Security Warning**
> An API key grants direct billing privileges. **Never** hardcode it into scripts, commit it to Git repositories, share it via Slack/Teams, or expose it in unblurred screenshots.

### 2. Configure the Key as an Environment Variable

#### macOS / Linux (`zsh` — default on modern macOS)

**Step 1.** Open your shell profile configuration file in a terminal text editor:
```bash
nano ~/.zshrc
```

**Step 2.** What you will see inside.
The file is **not blank** — it almost certainly already contains a `conda` initialization block (auto-generated by Anaconda) and possibly a few other tool hooks. A perfectly healthy `~/.zshrc` typically looks like this:

```bash
# >>> conda initialize >>>
# !! Contents within this block are managed by 'conda init' !!
__conda_setup="$('/Users/<you>/anaconda3/bin/conda' 'shell.zsh' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "/Users/<you>/anaconda3/etc/profile.d/conda.sh" ]; then
        . "/Users/<you>/anaconda3/etc/profile.d/conda.sh"
    else
        export PATH="/Users/<you>/anaconda3/bin:$PATH"
    fi
fi
unset __conda_setup
# <<< conda initialize <<<

unset ALL_PROXY
# Added by LM Studio CLI (lms)
```

This is **fine**. Do not panic, do not delete anything.

> [!WARNING]
> **Do NOT modify anything between `# >>> conda initialize >>>` and `# <<< conda initialize <<<`.** That block is owned and rewritten by `conda init`. Editing it will break your `conda` command and require a reinstall.

**Step 3.** Use the arrow keys to scroll to the **very bottom** of the file (below the last existing line, e.g. below `# Added by LM Studio CLI (lms)`). On a new line, paste:

```bash
export ANTHROPIC_API_KEY="sk-ant-api03-paste-your-real-key-here"
```

**Step 4.** Save and exit nano: press `Ctrl + O` → `Enter` (write) → `Ctrl + X` (exit).

**Step 5.** Re-load the profile so the change takes effect in your current terminal — **or** simply close this terminal window and open a fresh one (same effect):
```bash
source ~/.zshrc
```

**Step 6.** Confirm the key is live. This step has **nothing to do with `venv`** — run it directly in your shell, with or without `.venv` activated:
```bash
echo $ANTHROPIC_API_KEY
```
If you see your key printed back, configuration is complete.

#### Windows 11 / 10 (PowerShell)
*For the active temporary terminal session only:*
```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```
*For permanent configuration (persists across system reboots and new shell instances):*
```powershell
[System.Environment]::SetEnvironmentVariable('ANTHROPIC_API_KEY', 'sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxx', 'User')
```
*Note: After applying the permanent registry update, completely restart PowerShell for the context switch to bind.*

### 3. Verify Local Runtime Exposure
Ensure your local virtual environment is active, then execute this diagnostics one-liner to verify variable exposure:
```bash
python -c "import os; k = os.environ.get('ANTHROPIC_API_KEY'); print('Key found:', bool(k), '| Starts with:', (k or '')[:10] + '...')"
```

#### Expected Diagnostics Outputs:
* **Success Matrix:**
  ```text
  Key found: True | Starts with: sk-ant-api...
  ```
* **Failure Matrix:**
  ```text
  Key found: False | Starts with: ...
  ```

#### Common Root Causes & Fixes:
* **Stale Shell Context:** Run `source ~/.zshrc` (macOS) or spawn a fresh PowerShell window (Windows).
* **Naming Asymmetry:** Ensure the variable is capitalized exactly as `ANTHROPIC_API_KEY`.
* **Isolation Loss:** Confirm that your shell prompt explicitly shows the `(.venv)` namespace active.
* **Missing Scope (macOS):** Ensure you included the explicit `export ` statement prefix in `.zshrc`.

### 4. Direct Client Initialization Check
Execute a localized live client instantiation check to confirm that the API key maps successfully against Anthropic's gateway servers:
```bash
python -c "from browser_use.llm import ChatAnthropic; ChatAnthropic(model='claude-sonnet-4-5'); print('OK: Client initialized')"
```
If the terminal prints `OK: Client initialized`, your integration layer is fully certified — you can proceed to `python run_demo.py`. If a handshake error or `AuthenticationError` is raised, revoke the current key and provision a clean entry from the Anthropic console.

---

## 📋 Standard Dependency Ledger (`requirements.txt`)

Ensure your root `requirements.txt` file is structured precisely as follows to maintain the optimized Single-Agent configuration footprint also ensure that `requirements.txt` file is under the same file path with the main program:

```text
# ============================================================
# Luxury Price Reconciliation Agent Core Dependencies
# ============================================================

# Core Automation & AI Agent Frameworks
browser-use>=0.1.0
playwright>=1.40.0

# LLM Orchestration Interfaces
langchain-anthropic>=0.1.0

# High-fidelity Data Structures & Excel Engineering
pandas>=2.0.0
openpyxl>=3.1.0

# Asynchronous Runtimes & Data Validation Layers
pydantic>=2.0.0
```

---

## 🏃‍♂️ Verification & Execution

### 🎯 The Golden Environment Sanity Check
Before initializing a large-scale automated data run, execute the following runtime assertion check inside your active virtual environment:

```bash
python -c "import platform; import sys; print('='*50); print('Python Runtime Path:', sys.executable); print('Host Machine Architecture:', platform.machine()); print('='*50)"
```

#### Expected Benchmark Outputs:
* **Apple Silicon Mac Host**: `Host Machine Architecture` **must** return **`arm64`**.
* **Windows Host**: `Host Machine Architecture` typically returns **`AMD64`**.

### 🚀 Launching the Reconciliation Job
Once the telemetry assertion above passes, initiate the core execution orchestration script:
```bash
python run_demo.py
```

---

## 📥 Input Preparation Guide (`To_be_update.xlsx`)

Always refer to Ruihang's sample input file **Sample_To_be_update.xlsx**. The agent expects a hand-prepared Excel file named **exactly** `To_be_update.xlsx` in the project root. The quality of the run **depends entirely on the quality of this file.**

### 1. Source of the input file
Start from the standard `evolution` sheet produced by the legacy Price Check report (`price_check_tool_all_brands_-_VXII.py`). The agent consumes the **same column schema**: `Url`, `Name`, `Brand`, `Market`, `currency_s`, `Original Price_validated`, `status`, `Remarks L1`, `Remarks L2 (details)`. **Do not rename, reorder, or delete these columns** — the writer locates `Remarks L1` and `Remarks L2 (details)` by header name and will refuse to start if either is missing. Manually create a new excel file called `To_be_update.xlsx` and copy the header from report genrated by `price_check_tool_all_brands_-_VXII.py` then copy the rows you want agent to check and paste it to `To_be_update.xlsx` following the rules below in Mandatory pre-filter chapter. When copy and paste rows from price check report, due to the fact that some columns are hidden and pasting may unhide the columns, make sure what you paste align with the header or you will waste the API usage.

### 2. Mandatory pre-filter (manual, before saving the file)

> [!CAUTION]
> **The agent is not a replacement for the human review filter.** Skipping the steps below will either waste API budget on rows that don't need verification, or worse, write the wrong Remark to rows the agent was never validated against.

Apply these filters in the order listed:

| # | Action | Reason |
| --- | --- | --- |
| 1 | **Keep only `status == "Missing in crawl"` OR `Remarks L1 == "Refresh data"`** | These are the only two row types the reconciliation logic in `reconcile.py` knows how to handle: **refresh data(data outside of delivery range) and pure missing in crawl data(with status of missing in crawl and no compensating pair in new addition)** . Any other row will be skipped. |
| 2 | **Drop every row where `Brand == "Loewe"`** | Loewe requires region switching that the headless browser cannot perform. Loewe rows are 100% human-owned. |
| 3 | **Drop `Audemars Piguet` (AP) rows** | AP data comes directly from the brand feed, not from a re-crawl, so it must not be flagged as `Refresh data` in the first place. |
| 4 | **Drop `Hermès` rows where data originates from in-store collection** | Per the onboarding guide §3.2.3, Hermès store data must not be modified. |
| 5 | **Drop rows already reviewed by a human in this delivery cycle** | For **missing in crawl data** If `Remarks L1` or `Remarks L2 (details)` already contains a non-blank manual note, or for **refresh data** if `Remarks L2 (details)` already contains info, the agent will overwrite it. Filter these out. In another word: For **missing in crawl data**, keep `Remarks L1` or `Remarks L2 (details)` blank, for **refresh data**, keep `Remarks L2 (details)` empty and `Remarks L1` remained as refresh data |
| 6 | **Save as `To_be_update.xlsx` in the project root** | The filename is enforced by `run_demo.py`. |

The runner performs a **pre-flight scan** at startup and prints a warning if any rows from `EXCLUDED_BRANDS` slipped through, but it will not auto-remove them — the operator is expected to know.

### 3. Sanity-check checklist before launching

Run through this mentally before typing `python run_demo.py`:

- [ ] File is named exactly `To_be_update.xlsx` (case-sensitive on macOS/Linux).
- [ ] File sits in the same directory you will launch the script from.
- [ ] Loewe rows: 0.
- [ ] AP rows: 0.
- [ ] Every remaining row has a non-blank `Url`, `Original Price_validated`, and `currency_s`.
- [ ] You have a sense of the row count — a 500-row file will take roughly 1.5–3 hours wall-clock at `MAX_CONCURRENT = 3`.

---

## 📤 Output Interpretation Guide (`To_be_update_filled.xlsx`)

The runner **never modifies the input file in place**. It writes a new file named `<input_stem>_filled.xlsx` next to the input — for the canonical `To_be_update.xlsx`, this is `To_be_update_filled.xlsx`.

### 1. What gets written

Only two columns are touched: `Remarks L1` and `Remarks L2 (details)`. Everything else in every row is copied from the source verbatim, including original formatting, column widths, filters, and any pre-existing cell fills.

### 2. Cell color legend

The writer applies a fill color to the two updated cells based on the reconciliation decision label:

| Color | Hex | Meaning | What you should do |
| --- | --- | --- | --- |
| 🟢 Light green | `#C6EFCE` | `AUTO_*` decision — agent saw a high-confidence price that matched, or a same-price refresh, with no anomalies. | Spot-check ~5%. If clean, accept the whole batch. |
| 🟡 Light yellow | `#FFEB9C` | `LOW_CONFIDENCE_NEEDS_REVIEW` — the agent extracted something, but its self-rated confidence was `medium` or `low`, so the row was escalated. The original `Remarks L1` is preserved and `Remarks L2 = "manual"`. | Open the URL yourself and confirm the price. The agent's structured log will already tell you why it wasn't sure. |
| 🔴 Light red | `#F4CCCC` | `AUTO_PRODUCT_GONE` / `AUTO_CONFIRMED_MISSING` — the URL redirected to a homepage / category / search page, meaning the product is no longer on sale. | Sanity-check by opening the URL in a real browser. If it really is dead, accept; otherwise treat as manual. |

### 3. Crash-safety guarantee

`run_demo.py` flushes partial progress to `To_be_update_filled.xlsx` every `CHECKPOINT_EVERY` (default: 10) completed rows. **If the run is interrupted** (network drop, API rate limit, browser hang, accidental Ctrl-C), every checkpointed row is already on disk and you only lose the in-flight `MAX_CONCURRENT` rows. To resume after a partial run, simply launch the script again — but be aware that the current implementation **does not skip already-completed rows**; it will re-process them. For now, the recommended pattern is: let the full run complete, accept that the few in-flight rows at crash time are wasted API calls, and live with it.

---

## 🚦 Pipeline Flow & Reconciliation Logic

For colleagues who will operate or extend the runner, the high-level data flow is:

```
   To_be_update.xlsx
          │
          ▼
   ┌─────────────────────────────────────────┐
   │  run_demo.py  (orchestrator)            │
   │  - eligibility filter                   │
   │  - asyncio.Semaphore (MAX_CONCURRENT)   │
   │  - checkpointing every 10 rows          │
   └─────────────────────────────────────────┘
          │
          ▼  for each eligible row, in parallel
   ┌─────────────────────────────────────────┐
   │  agent_1.py  (Claude Sonnet 4.5)        │
   │  - browser-use + Chromium, DOM mode     │
   │  - structured Pydantic output           │
   │    {price_found, url_redirected,        │
   │     confidence ∈ {high, medium, low},   │
   │     evidence}                           │
   └─────────────────────────────────────────┘
          │
          ▼
   ┌─────────────────────────────────────────┐
   │  reconcile.py  (pure rule engine)       │
   │  Priority cascade (first match wins):   │
   │    P1. redirected + null price          │
   │        → AUTO_PRODUCT_GONE              │
   │    P2. evidence starts with "BLOCKED:"  │
   │        → LOW_CONFIDENCE_NEEDS_REVIEW    │
   │    P3. confidence=high AND price set    │
   │        → AUTO_REFRESH_* / AUTO_MISSING_*│
   │    P4. anything else                    │
   │        → LOW_CONFIDENCE_NEEDS_REVIEW    │
   └─────────────────────────────────────────┘
          │
          ▼
   ┌─────────────────────────────────────────┐
   │  excel_writer.py                        │
   │  - copies input → output                │
   │  - patches Remarks L1 / L2 only         │
   │  - color-codes by decision label        │
   └─────────────────────────────────────────┘
          │
          ▼
   To_be_update_filled.xlsx
```

**Why the agent escalates so aggressively.** The previous dual-agent architecture (Claude + GPT-4o cross-verification) was retired to halve LLM cost. With only one agent left, the `confidence` field is the **sole gate** between auto-accept and human review. The rubric is intentionally strict: anything that isn't a textbook "one product, one price, page fully rendered" answer drops to `medium`, which means manual review. Expect a real-world AUTO rate around 70–80% on a clean input, not 100%.

---

## 🧬 Component Specifications

This section documents the **exact behavioral rules** encoded in each of the three core components. It is intended for colleagues who need to understand *why* the agent made a particular call on a particular row, or who will maintain or extend the pipeline. The rules below are extracted directly from the source code — if the code and this document ever disagree, the code is authoritative and this section should be updated.

### 1. Agent 1 — Verification Agent (`agent_1.py`)

#### 1.1 Purpose
A single Claude-driven browser agent that opens a product URL, detects whether the product is still on sale, reads the current price from the DOM, and returns a structured JSON result with a self-assessed confidence score. **This is the only LLM call per row** — the previous dual-agent (Claude + GPT-4o) cross-verification architecture has been retired to halve LLM cost.

#### 1.2 Structured Output Schema (`PriceVerificationResult`)
Every agent invocation must produce a JSON object matching this Pydantic schema. Fields the agent fails to populate are coerced to `null` (or `"low"` for confidence) by the fallback handler.

| Field | Type | Meaning |
| --- | --- | --- |
| `product_available` | `"yes"` / `"no"` / `"uncertain"` | Is the product still on sale at the original URL? `"yes"` requires both a recognizable product name AND a visible price in the DOM. |
| `url_redirected` | `bool` | Did the browser end up on a different page than the one we opened? See §1.3 for the strict definition. |
| `final_url` | `str` or `null` | The URL after the page finished loading. |
| `price_found` | `float` or `null` | Current price as a plain number (`€2,000.00` → `2000.0`). **Must be `null` if the agent is not certain.** |
| `currency_found` | 3-letter ISO code or `null` | EUR, USD, GBP, JPY, CNY, etc. Must be `null` if `price_found` is `null`. |
| `evidence` | `str` | What the agent actually observed. When the page was blocked, this field **must start with the literal prefix `"BLOCKED:"`** — `reconcile.py` keys off this exact prefix in §2.2. |
| `confidence` | `"high"` / `"medium"` / `"low"` | Self-assessed certainty. The reconciliation engine relies entirely on this field to decide auto-accept vs manual escalation (§2.2). |

#### 1.3 URL Redirect — Strict Definition
> [!IMPORTANT]
> **Not all URL changes are redirects.** Many luxury sites rewrite URLs to SEO-friendly slugs *while remaining on the same product page* (e.g., `/products/S5573CRIW_M928` → `/products/sac-dior-book-tote-mini-S5573CRIW_M928`). This is **NOT** a redirect.
>
> `url_redirected = true` is set **only** when the final URL is a homepage, a category listing, or a search results page — i.e., the original product has been removed from sale and the site now points elsewhere.

#### 1.4 Confidence Rubric (Verbatim from Prompt)

| Level | Required Conditions |
| --- | --- |
| **`high`** | **ALL FOUR** must hold: (1) exactly one main product price clearly visible in DOM; (2) product name on page closely matches the requested name; (3) page is a proper, fully-rendered product page (not blocked, not partially loaded); (4) no ambiguity from sale/regular price or installment plans being mistaken for the main price. |
| **`medium`** | A price was found, but **at least one** of: multiple prices visible (sale vs regular, multiple variants), product name only partially matches, page seems to have rendered only partially, or the agent had to use reasoning to pick among candidate prices. |
| **`low`** | **Any** of: price not visible, page blocked, redirect detected, product name does not match, page failed to load, or the agent is guessing. |

> [!CAUTION]
> **Tie-breaker rule:** When the agent is between two confidence levels, the prompt instructs it to **always choose the lower one**. False `high` causes silent data corruption (the wrong price is written to Excel without human review); false `medium` only costs a few minutes of manual review. The asymmetry of cost is the entire justification for the strict rubric.

#### 1.5 Hard-Coded Behavioral Rules (Encoded in the Prompt)

##### a) Early-Termination Triggers
The agent is instructed to **stop immediately, without retrying or navigating elsewhere**, if it observes any of the following, and return a `BLOCKED:` evidence string with `confidence = "low"`:

- `"Access Denied"` / `"Accès refusé"` / `"Zugriff verweigert"` (multilingual variants)
- HTTP 403 Forbidden
- Cloudflare challenge pages (`"Checking your browser"`, `"Just a moment..."`)
- CAPTCHA, hCaptcha, reCAPTCHA
- HTTP 429 / `"Too many requests"`
- PerimeterX / DataDome / Akamai block screens
- Network errors: `ERR_TUNNEL_CONNECTION_FAILED`, `ERR_CONNECTION_REFUSED`, DNS errors
- A page that is entirely a blocking message with no product information

##### b) Pre-Content Interstitial Handling
Luxury sites frequently show one of these before the product page renders — the agent has a **strict 2-step budget** to dismiss them, after which it proceeds regardless:

| Interstitial | Action |
| --- | --- |
| Cookie consent banner | Click `Accept` / `Accept all` / `OK` |
| Region / country selector | Pick the country matching the URL market (`fr_fr` → France, `en_us` → US, `gb` → UK) |
| Newsletter signup popup | Click the `X` close button or `No thanks` |
| Age gate or terms confirmation | Confirm to proceed |

##### c) Anti-Hallucination Rules
Five non-negotiable rules baked into the prompt:

1. **Never fabricate prices.** If the price is not clearly visible in the DOM, `price_found` MUST be `null`.
2. **The reference price is context, not the answer.** The expected price is passed to the agent for grounding, but it must read the actual price from the page, not echo the reference.
3. **Redirects mean "product is gone", not "try harder".** If a redirect is detected, do not browse, do not search, do not navigate. Report and stop.
4. **Evidence must be observation, not expectation.** Quote DOM content where possible.
5. **Be conservative with confidence.** Because no second agent cross-checks the result, a false `high` will be written to Excel without review. When in doubt, downgrade.

#### 1.6 Runtime Configuration

| Parameter | Value | Rationale |
| --- | --- | --- |
| Model | `claude-sonnet-4-5` | Current production model. |
| `use_vision` | `False` | DOM mode (read raw HTML structure). 3–4× cheaper and 2× faster than vision mode; tradeoff documented in §⚠️.1. |
| `minimum_wait_page_load_time` | `3.0` seconds | Forces a 3-second floor on page-load waits to mitigate JS-injected price delays. |
| `max_steps` | `8` | The agent gets at most 8 reasoning steps; beyond that the run is terminated and the fallback (§1.7) kicks in. |
| `initial_actions` | Force `navigate` | Defensive — we explicitly enqueue the navigation as the first action instead of trusting the LLM to navigate on its own. |

#### 1.7 Failure Fallback
If the agent exhausts `max_steps = 8` without producing a parseable `final_result`, the code synthesizes a safe placeholder:

```python
{
    "product_available": "uncertain",
    "url_redirected": False,
    "final_url": None,
    "price_found": None,
    "currency_found": None,
    "evidence": "Agent failed to produce a final result.",
    "confidence": "low",
}
```

This placeholder is routed by `reconcile.py` to the P4 manual-review bucket (§2.2), so the row is **never silently dropped** — it is always either written or flagged for human review.

---

### 2. Reconciliation Engine (`reconcile.py`)

#### 2.1 Purpose
A pure rule engine (no LLM, fully deterministic) that consumes the agent's structured output and decides:
- Which two values to write into the `Remarks L1` and `Remarks L2 (details)` columns
- Which color the cells should be filled with (via the `decision` label, consumed by `excel_writer.py` in §3)

#### 2.2 Tunable Constants

| Constant | Value | Meaning |
| --- | --- | --- |
| `PRICE_TOLERANCE_PCT` | `0.1` | A `price_found` is considered to **match** `Original Price_validated` if their absolute difference is ≤ **0.1%** of the validated price. For a €2,000 product, this is a €2 window. |
| `MANUAL_TAG` | `"manual"` | The literal string written to `Remarks L2 (details)` whenever a row is escalated for human review. |

#### 2.3 Decision Priority Cascade
The engine evaluates four priority levels in strict top-down order. **The first match wins**; subsequent rules are not evaluated.

| Priority | Trigger Condition | Outcome Family |
| --- | --- | --- |
| **P1** | `url_redirected == true` AND `price_found is None` | Product gone — auto-mark removed/confirmed-missing |
| **P2** | `evidence` (stripped, uppercased) starts with `"BLOCKED"` | Page was blocked — escalate to manual |
| **P3** | `confidence == "high"` AND `price_found is not None` | Trust the agent — auto-write the price |
| **P4** | Everything else (medium/low confidence, or high with `null` price, etc.) | Escalate to manual |

#### 2.4 Complete Decision Matrix
The combination of P1–P4 and the two possible `row_type` values yields exactly **eight** output patterns:

| # | Trigger | `row_type` | Remarks L1 written | Remarks L2 written | `decision` label |
| --- | --- | --- | --- | --- | --- |
| 1 | redirect + `null` price | `refresh_data` | `Missing-remove` | *(blank)* | `AUTO_PRODUCT_GONE` |
| 2 | redirect + `null` price | `missing_in_crawl` | `OK, missing` | *(blank)* | `AUTO_CONFIRMED_MISSING` |
| 3 | `BLOCKED:` in evidence | any | **original L1 preserved** | `manual` | `LOW_CONFIDENCE_BLOCKED` |
| 4 | high + price matches validated | `refresh_data` | `Refresh data` | `Same price` | `AUTO_REFRESH_SAME_PRICE` |
| 5 | high + price matches validated | `missing_in_crawl` | `Not OK, available` | `Same price` | `AUTO_MISSING_BUT_AVAILABLE_SAME_PRICE` |
| 6 | high + price differs from validated | `refresh_data` | `Refresh data` | *(new price as number)* | `AUTO_REFRESH_NEW_PRICE` |
| 7 | high + price differs from validated | `missing_in_crawl` | `Not OK, available` | *(new price as number)* | `AUTO_MISSING_BUT_AVAILABLE_NEW_PRICE` |
| 8 | anything else | any | **original L1 preserved** | `manual` | `LOW_CONFIDENCE_NEEDS_REVIEW` |

#### 2.5 Business Semantics: `refresh_data` vs `missing_in_crawl`
The two row types represent different business situations and trigger different L1 labels:

**`refresh_data` rows** —— These are existing records that the team has flagged for a price re-check.

- Agent says product is gone → `Missing-remove` (downstream should delete this SKU from inventory)
- Agent confirms price unchanged → `Refresh data` + `Same price` (no action needed)
- Agent finds a new price → `Refresh data` + the new price number (price update applied)

**`missing_in_crawl` rows** —— These are SKUs the daily crawler failed to retrieve. They might be genuinely off-sale, OR the crawler might have missed them.

- Agent confirms product is gone → `OK, missing` (the crawler was correct; product is indeed off-sale)
- Agent finds the product still on sale → `Not OK, available` (the crawler missed it; data needs to be restored manually)

**Why "preserve original L1" matters (rows 3 and 8).** When the agent cannot produce a confident answer, the engine **does not overwrite** whatever `Remarks L1` value already existed in the input file. It only stamps `manual` into `Remarks L2`. This prevents the agent from destroying human-curated annotations during ambiguous cases.

---

### 3. Excel Writer (`excel_writer.py`)

#### 3.1 Purpose
Apply the reconciliation engine's decisions to the input Excel — without ever modifying the original file — and color-code the affected cells for fast visual triage.

#### 3.2 Workflow
1. **Copy.** `shutil.copyfile(input_path, output_path)` — the original input file is never opened in write mode. The output is always a fresh copy.
2. **Open the copy.** `openpyxl.load_workbook(output_path)`.
3. **Locate columns by header name.** Walk row 1 looking for the literal strings `"Remarks L1"` and `"Remarks L2 (details)"`. **Column positions are not hard-coded** — if the schema reorders columns, the writer still works as long as the header names are intact. If either header is missing, the writer raises `ValueError` and aborts.
4. **Apply each update.** For each `(row_index, remark_l1, remark_l2, decision)` tuple, write the two cell values and apply a fill color derived from the `decision` label (see §3.3).
5. **Save.** `wb.save(output_path)`.

#### 3.3 Decision-to-Color Mapping
The mapping is defined by `_decision_to_color()` as a **priority-ordered `if` chain**. The order matters — `AUTO_PRODUCT_GONE` and `AUTO_CONFIRMED_MISSING` are checked **before** the generic `AUTO_` prefix, otherwise they would incorrectly resolve to green.

| Match Order | Decision Prefix | Fill Color | Hex |
| --- | --- | --- | --- |
| 1st | `AUTO_PRODUCT_GONE` OR `AUTO_CONFIRMED_MISSING` | 🔴 Light red | `#F4CCCC` |
| 2nd | Any other `AUTO_*` | 🟢 Light green | `#C6EFCE` |
| 3rd | Any `LOW_CONFIDENCE*` | 🟡 Light yellow | `#FFEB9C` |
| Default | (no match) | *(no fill)* | — |

#### 3.4 What is Preserved vs Modified

| Aspect of the file | Behavior |
| --- | --- |
| Original input file | **Never touched.** All work is done on the copy. |
| Columns other than `Remarks L1` / `Remarks L2 (details)` | Copied verbatim from the input — values, formatting, column widths, autofilters, frozen panes, pre-existing fill colors. |
| Row order | Preserved — the writer locates rows by 1-based `row_index` passed in from `run_demo.py`, never by re-sorting. |
| Cells in the two Remarks columns for **eligible** rows | Overwritten with the engine's decision; filled with the color from §3.3. |
| Cells in the two Remarks columns for **ineligible** rows | Untouched — they keep whatever the human reviewer wrote (or stay blank). |

---

## ⚠️ Known Operational Issues (Read Before First Run)

These are not bugs — they are real-world behaviors a colleague will encounter on the first run and may misinterpret as a broken script.

### 1. JavaScript-rendered prices (Dior, Gucci, others)

The agent runs in **DOM mode** (`use_vision=False`). It reads the page's HTML structure directly, not a rendered screenshot. This is 3–4× cheaper and 2× faster than vision mode, but it has one real cost:

> Some luxury sites — **Dior is the worst offender** — inject the price into the DOM via client-side JavaScript with a noticeable delay. On a slow connection, the agent can finish reading the page **before** the price node has been injected. From the agent's perspective: it loaded the URL, the product name was there, but the price field was empty. It correctly reports `confidence = medium` with evidence like `"page seems to have rendered only partially"`, and `reconcile.py` escalates the row to manual review.

This is **expected behavior**, not a failure. Mitigations already in place:
- `minimum_wait_page_load_time=3.0` in `agent_1.py` forces a 3-second floor on page-load wait.
- The confidence rubric explicitly distinguishes "price found in a fully-rendered page" from "price found but page may have only partially rendered."

If you see a Dior-heavy batch with a manual escalation rate above ~40%, the network was likely slow during the run. Re-running those specific rows usually resolves them.

### 2. The terminal log is interleaved and unreadable

With `MAX_CONCURRENT = 3`, three independent agents print to the same stdout. You will see this kind of output:

```
======================================================================
[1/89]  Excel row 14  |  Dior / FRA
URL: https://www.dior.com/...
======================================================================
Row type: refresh_data

→ Agent (Claude) running...

======================================================================
[2/89]  Excel row 22  |  Chanel / USA
URL: https://www.chanel.com/...
======================================================================
Row type: refresh_data
  price_found = 2000.0  confidence = high  redirected = False   ← from [1/89]
→ Agent (Claude) running...

→ Decision: AUTO_REFRESH_SAME_PRICE  (62.3s)    ← from [1/89]
```

**Do not try to read the log linearly.** The final summary table at the end is the authoritative view; the row-by-row log is best-effort. If you must trace a single row, grep for its Excel row index (`Excel row 22`).

### 3. Multiple Chromium windows pop up on your screen

`browser-use` runs Chromium in **headed** (visible) mode by default. With `MAX_CONCURRENT = 3`, three Chromium windows will appear, layered on top of each other, scrolling autonomously. **Do not click them, do not close them, do not switch focus** — Playwright is driving them and any human interaction can derail the agent. Minimize them if they bother you; closing one kills the corresponding task.

### 4. Cookie banners, region selectors, and anti-bot interstitials

Luxury sites frequently display one of these before the product page renders, especially when the request originates from a region different from the URL's market (e.g., a French laptop opening a `/en_us/` URL):

- "Accept cookies" banner — agent prompt instructs it to click through.
- "You are visiting from X, continue to Y?" — agent prompt instructs it to stay on the original URL.
- Cloudflare / Akamai / PerimeterX block screens — agent returns `evidence = "BLOCKED: ..."` and the row is escalated.

Markets behind a geo-block (e.g., a `ko_kr` URL accessed from outside Korea) will sometimes never render and the agent will time out. These rows are the agent's natural failure mode and need either a VPN-equipped human or a re-run from a machine in the right region.

### 5. Anthropic per-minute rate limits

Anthropic enforces a per-minute token budget that depends on your account tier:
- **Tier 1** (default, no top-up): ~50K input + ~10K output tokens/minute.
- **Tier 2** (after ~$40 in spend): roughly 4× higher.

Each agent call uses ~3–5K input + ~200 output tokens. `MAX_CONCURRENT = 3` consumes ~15K input/min — well within Tier 1. **`MAX_CONCURRENT = 5` consumes ~25K input/min and is still safe on Tier 1, but risky on a freshly created account.** If you see HTTP 429 errors in the log, lower `MAX_CONCURRENT` and re-run.

### 6. The same URL can give different confidence levels on different runs

The agent is not deterministic. The same URL, run twice, can produce `confidence = high` once and `confidence = medium` the other time — typically because the page rendered differently between the two attempts (different network speed, different cookie state, different Cloudflare challenge outcome). **Do not treat a single low-confidence row as proof that the agent is wrong about that product.** Re-run before reporting an issue.

---

## ❌ Troubleshooting & Failure Modes

<details>
<summary><b>1. Playwright throws <code>Error: Only Archer/Mac-Arm64 is supported</code> during install</b></summary>
<br>
<b>Root Cause:</b> Architecture Mismatch. Your physical machine is an Apple Silicon Mac, but either your active Terminal application or the Python interpreter instance is locked under Intel (x86_64) translation.<br>
<b>Resolution:</b> Re-run <b>macOS Setup -> Step 1 through Step 3</b> to clear structural pollution and force-rebuild your runtime layer using the explicit <code>macos-aarch64</code> parameter.
</details>

<details>
<summary><b>2. Terminal shell stubbornly prefixes <code>(base)</code> even after explicit activation</b></summary>
<br>
<b>Root Cause:</b> Anaconda / Miniconda global shell hooks take visual priority in prompt layouts.<br>
<b>Resolution:</b> This is purely cosmetic. Run <code>which python</code> (macOS) or <code>where.exe python</code> (Windows). If the generated string points directly into your local repository's <code>.venv</code> path, your current execution thread is correctly sandboxed. You can safely ignore the Conda prefix visual bug.
</details>

<details>
<summary><b>3. Execution fails immediately with <code>No such file or directory (os error 2)</code> targeting <code>playwright</code></b></summary>
<br>
<b>Root Cause:</b> Missing path symmetry inside the <code>uv</code> runner ecosystem.<br>
<b>Resolution:</b> Ensure <code>playwright</code> is explicitly declared as a top-level requirement inside your <code>requirements.txt</code> file, and re-execute <code>uv pip install -r requirements.txt</code> to generate the required binary symlinks in the local environment's <code>bin/</code> path.
</details>

<details>
<summary><b>4. The script appears to hang for 30+ seconds after launch with no output</b></summary>
<br>
<b>Root Cause:</b> Playwright is downloading the Chromium binary on first use, or browser-use is performing a one-time initialization handshake with the Anthropic API.<br>
<b>Resolution:</b> Wait. First-launch overhead is normal. If nothing prints after 60 seconds, kill the process and re-run <code>uv run playwright install chromium</code> to confirm the browser binary is locally available.
</details>

<details>
<summary><b>5. The run finishes but <code>To_be_update_filled.xlsx</code> has a high manual-escalation rate (&gt;30%)</b></summary>
<br>
<b>Root Cause:</b> Almost always a JavaScript rendering issue (see Known Operational Issues §1). A slow network or a CPU-pressured machine causes the agent to read the DOM before client-side scripts have finished injecting prices. Less commonly, the brand mix in your input is heavy on Dior/Gucci, both of which have render delays even on good networks.<br>
<b>Resolution:</b> (a) Re-run the full file when the network is quieter. (b) Lower <code>MAX_CONCURRENT</code> from 3 to 2 to give each browser more CPU headroom. (c) Accept that ~20–30% manual review is the steady-state design target — the dual-agent pipeline was retired and the remaining single agent escalates conservatively by design.
</details>

<details>
<summary><b>6. Several rows fail with <code>❌ Row N failed with exception: ...</code></b></summary>
<br>
<b>Root Cause:</b> Per-row exceptions (Playwright timeouts, Anthropic transient 5xx, browser process crashes) are caught at the row boundary so one bad row doesn't abort the whole run. The row is logged and skipped — its <code>Remarks L1/L2</code> are left untouched in the output.<br>
<b>Resolution:</b> Grep the log for <code>❌ Row</code> to extract the affected Excel row indices. Either review those rows manually, or copy them into a small <code>To_be_update.xlsx</code> and re-run just that subset.
</details>

<details>
<summary><b>7. HTTP 429 or "rate_limit_error" appears in the log</b></summary>
<br>
<b>Root Cause:</b> Anthropic per-minute token budget exhausted. This is the single most common cause of mid-run failures when <code>MAX_CONCURRENT</code> is set too aggressively for a Tier 1 account.<br>
<b>Resolution:</b> Edit <code>run_demo.py</code> and lower <code>MAX_CONCURRENT</code> to 2 (or 1 in the worst case). Re-run. The crash-safe checkpointing means rows already completed before the rate-limit hit are preserved in the output file from the previous run — open it and confirm before restarting.
</details>

<details>
<summary><b>8. Output Excel exists but is locked / cannot be opened</b></summary>
<br>
<b>Root Cause:</b> The most common cause is that you have <code>To_be_update_filled.xlsx</code> open in Excel from a previous run, and the runner has flushed a checkpoint while Excel held a file lock. On Windows the runner will raise <code>PermissionError</code>; on macOS the write may silently fail.<br>
<b>Resolution:</b> Close the output file in Excel before running. As a hygiene practice, never open the output file while the run is still in progress — wait for the <code>✅ Output:</code> line, or at minimum close it again before the next checkpoint window.
</details>
