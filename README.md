# AI-agent-for-quant-team
```markdown
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
> Luxury brand e-commerce sites possess exceptionally dense and deeply nested HTML DOM structures (often exceeding tens of thousands of lines).
> 
> If your Mac Terminal or Python interpreter runs under Intel (x86_64) emulation mode via Rosetta 2, the CPU incurs massive overhead performing dynamic instruction translation during DOM tree parsing.
> 
> **Impact:** Processing a single product URL under emulation takes **4 to 5 minutes**.
> 
> By enforcing a **pure native Apple Silicon (aarch64/arm64)** execution space via this setup guide, DOM parsing efficiency increases 10x, reducing single-URL execution down to **20 to 40 seconds**.

---

## 🛠️ Environment Configuration Guide

To eliminate global dependency drift and avoid heavy, fragmented `Anaconda` environments, this project standardizes environment isolation and deterministic package synchronization using **`uv`**, a hyper-fast Python package manager written in Rust.

### 1. Apple Silicon (M1/M2/M3/M4) macOS Setup

#### Step 1: Verify Host Terminal Architecture
Open your native macOS Terminal or iTerm2 and execute:
```bash
arch
If it outputs x86_64 (⚠️ Action Required): Your terminal application is locked under Rosetta 2 emulation. Completely quit the terminal. Open Finder -> Applications, locate your terminal app icon, right-click and select Get Info. Uncheck the "Open using Rosetta" checkbox. Relaunch the terminal.

If it outputs arm64 (✅ Optimal): Your terminal environment is native. Proceed to the next step.

Step 2: Purge Conflicted Virtual Environments
Navigate to the repository root and destroy any pre-existing, poisoned virtual environments:

Bash
cd /path/to/your/agent_project
rm -rf .venv
Step 3: Provision a Native Apple Silicon Virtual Environment
Force uv to pull and isolate a pure ARM64 Python interpreter by explicitly targeting the aarch64 target:

Bash
uv venv --python cpython-3.11-macos-aarch64 .venv
Step 4: Activate Environment and Synchronize Dependencies
Bash
# Activate the isolated project environment
source .venv/bin/activate

# Install the exact dependency tree (Overrides global Anaconda overrides)
uv pip install -r requirements.txt
Step 5: Install Native ARM64 Browser Binaries
Since your isolated Python space is now verified aarch64, the Playwright automated driver utility will bypass translation layers and provision a native Apple Silicon compiled Chromium binary:

Bash
uv run playwright install chromium
2. Windows 11 / 10 Enterprise Setup
Windows hosts do not encounter architecture translation penalties, but must follow strict sandboxed isolation.

Step 1: Bootstrap the uv Toolchain via PowerShell
Open PowerShell (Do NOT use the legacy CMD prompt) and execute the official installer:

PowerShell
powershell -ExecutionPolicy ByPass -c "irm [https://astral.sh/uv/install.ps1](https://astral.sh/uv/install.ps1) | iex"
Once complete, restart your PowerShell window to register the environment variables, and verify with uv --version.

Step 2: Initialize and Isolate the Environment
PowerShell
# Navigate to project repository
cd C:\path\to\your\agent_project

# Force delete legacy env artifacts
Remove-Item -Recurse -Force .venv

# Bootstrap a clean Python 3.11 runtime environment
uv venv --python 3.11

# Activate the environment via execution policy wrapper
.venv\Scripts\Activate.ps1
Step 3: Sync Dependencies and Headless Browsers
Within the activated virtual environment ((.venv) should be visible in the prompt prefix), execute:

PowerShell
uv pip install -r requirements.txt
uv run playwright install chromium
📋 Standard Dependency Ledger (requirements.txt)
Ensure your root requirements.txt file is structured precisely as follows to maintain the optimized Single-Agent configuration footprint:

Plaintext
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
🏃‍♂️ Verification & Execution
🎯 The Golden Environment Sanity Check
Before initializing a large-scale automated data run, execute the following runtime assertion check inside your active virtual environment:

Bash
python -c "import platform; import sys; print('='*50); print('Python Runtime Path:', sys.executable); print('Host Machine Architecture:', platform.machine()); print('='*50)"
Expected Benchmark Outputs:

Apple Silicon Mac Host: Host Machine Architecture must return arm64.

Windows Host: Host Machine Architecture typically returns AMD64.

🚀 Launching the Reconciliation Job
Once the telemetry assertion above passes, configure your API key and initiate the core execution orchestration script:

Bash
# Set your Anthropic API Key
export ANTHROPIC_API_KEY="your-api-key-here"  # macOS/Linux
$env:ANTHROPIC_API_KEY="your-api-key-here"    # Windows PowerShell

# Run the orchestration script
python run_demo.py
❌ Troubleshooting & Failure Modes
1. Anti-Bot / CAPTCHA Blocking
Symptom: The browser agent hangs on a verification/Cloudflare page or fails to find product elements.

Mitigation: Luxury e-commerce platforms deploy strict anti-bot systems. Run Playwright in headed mode for initial authentication debugging, pass specialized user-agent strings, or integrate premium residential proxies within the browser-use browser configuration.

2. File Access / Excel Write Locks
Symptom: PermissionError: [Errno 13] Permission denied when exporting to Excel.

Mitigation: Ensure the target reconciliation Excel sheet (.xlsx) is closed on your local machine before running run_demo.py. pandas and openpyxl cannot write to files actively locked by Microsoft Excel.

3. API Rate Limiting (Claude 3.5 Sonnet)
Symptom: 429 Too Many Requests or context length exhaustion.

Mitigation: Optimize your agent's system prompts to reduce token usage per step. Implement token bucket rate-limiting wrappers if scanning hundreds of luxury URLs sequentially.

4. Headless Execution Inconsistencies
Symptom: The agent behaves correctly in headed mode but fails to extract elements in headless mode.

Mitigation: Adjust the browser configuration to simulate realistic viewports and disable headless flag if the target site filters out headless Chromium requests.
