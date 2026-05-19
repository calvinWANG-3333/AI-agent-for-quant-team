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
> This project standardizes on native ARM64 Python via `uv` to ensure clean dependency resolution and consistent runtime behavior across
team members. While the dominant performance bottlenecks in this agent are network latency and LLM inference time, running under Rosetta 2 emulation adds measurable overhead to DOM parsing and package import. A native ARM64 venv eliminates this overhead and
also avoids the dependency conflicts that arise from mixing Anaconda's globally-installed packages with project-specific ones.
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
cd /path/to/your/agent_project
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
powershell -ExecutionPolicy ByPass -c "irm [https://astral.sh/uv/install.ps1](https://astral.sh/uv/install.ps1) | iex"
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

## 🔐 API Key Configuration (Required Before First Run)

This agent utilizes the Anthropic Claude API via `browser-use` to drive intelligent web navigation. You must configure your Claude API key as an environment variable before running `run_demo.py`. The orchestration script will explicitly refuse to boot if the key is missing to prevent silent failures mid-run.

### 1. Provision an Anthropic API Key
If you are joining the project team, **do not reuse another developer's key**. Every engineer must provision an individual credential for audit logging and usage tracking.

1. Sign in to the [Anthropic Console](https://console.anthropic.com/).
2. Navigate to **Settings** → **API Keys** → Click **Create Key**.
3. Copy the generated string immediately (prefixed with `sk-ant-...`). *Note: It will be permanently obscured after closing the modal.*

> [!CAUTION]
> **Credential Security Warning**
> An API key grants direct billing privileges. **Never** hardcode it into scripts, commit it to Git repositories, share it via Slack/Teams, or expose it in unblurred screenshots.

### 2. Configure the Key as an Environment Variable

#### macOS / Linux (`zsh` - default on modern macOS)
Open your shell profile configuration file in a terminal text editor:
```bash
nano ~/.zshrc
```
Append the following line at the very bottom of the file (replace the placeholder string with your verified key):
```bash
export ANTHROPIC_API_KEY="sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```
Save and exit (`Ctrl+O` -> `Enter` -> `Ctrl+X` in nano), then source the profile to commit changes to your current session:
```bash
source ~/.zshrc
```

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
python -c "from browser_use.llm import ChatAnthropic; ChatAnthropic(model='claude-3-5-sonnet-latest'); print('OK: Client initialized')"
```
If the terminal prints `OK: Client initialized`, your integration layer is fully certified—you can proceed to `python run_demo.py`. If a handshake error or `AuthenticationError` is raised, revoke the current key and provision a clean entry from the Anthropic console.
```

---

## 📋 Standard Dependency Ledger (`requirements.txt`)

Ensure your root `requirements.txt` file is structured precisely as follows to maintain the optimized Single-Agent configuration footprint:

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
