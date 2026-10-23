# Lab 0 — Environment Setup

**Duration:** 10 minutes  
**Goal:** Clone the repo, fill in credentials, install Bob modes, and validate the fleet backend before the lab begins.

> **Python version:** This lab requires **Python 3.12**. Python 3.13 is not supported (`pydantic-core` build fails). Run `python3 --version` before starting — if you see 3.13, install Python 3.12 via `pyenv` or `brew install python@3.12`.

---

## Overview

| # | Task | Step |
|---|---|---|
| 1 | Clone the lab repository | [Step 1](#step-1--clone-the-repository) |
| 2 | Fill in environment variables | [Step 2](#step-2--fill-in-environment-variables) |
| 3 | Start the Fleet Backend | [Step 3](#step-3--start-the-fleet-backend) |
| 4 | Install Bob modes | [Step 4](#step-4--install-bob-modes) |
| 5 | Validate watsonx Orchestrate access | [Step 5](#step-5--validate-watsonx-orchestrate-access) |

---

## Step 1 — Clone the Repository

```bash
git clone https://github.ibm.com/shanmsel/lab-2752-reusable-agentic-patterns
cd lab-2752-reusable-agentic-patterns
```

Open the `lab-2752-reusable-agentic-patterns` folder in IBM Bob IDE as your workspace root.

---

## Step 2 — Fill in Environment Variables

Two `.env` files need credentials before the services will start.

### 2a — Fleet Backend

```bash
cp 01-fleet-backend/.env.example 01-fleet-backend/.env
```

Open `01-fleet-backend/.env` and set:

```env
# watsonx Orchestrate — provided by instructor
WATSONX_ORCHESTRATE_URL=https://<your-tenant>.ai.ibm.com
WATSONX_ORCHESTRATE_API_KEY=<your-ibm-cloud-api-key>

# Leave these blank for now — you will fill them in Lab 3
WATSONX_ORCHESTRATE_AGENT_WEATHER=
WATSONX_ORCHESTRATE_AGENT_STATION=
WATSONX_ORCHESTRATE_AGENT_ROUTE=
WATSONX_ORCHESTRATE_AGENT_DECISION=
WATSONX_ORCHESTRATE_AGENT_NOTIFICATION=
```

### 2b — Forecast Service

```bash
cp 02-forecast-service/.env.example 02-forecast-service/.env
```

Open `02-forecast-service/.env` and set:

```env
FLEETOPS_API_BASE_URL=http://localhost:8085
USE_TTM_MODEL=False        # False = mock/instant startup. True = real Granite TTM-R2 via WML.
# WML credentials only needed if USE_TTM_MODEL=True:
# WML_SPACE_ID=<provided by instructor>
# WML_API_KEY=<provided by instructor>
# IBM_CLOUD_REGION=us-south
```

> **`USE_TTM_MODEL=False`** means the forecast service starts in under 5 seconds with no model download. Set to `True` only if your instructor has provided WML credentials and you want the real IBM Granite TTM-R2 model.

---

## Step 3 — Start the Fleet Backend

```bash
cd 01-fleet-backend
python3.12 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8085 --reload
```

> **Use `python3.12`** — not `python3` (which may resolve to 3.13 on some machines).

✅ **Success:** You see `Uvicorn running on http://127.0.0.1:8085` in the terminal.  
Open `http://localhost:8085/docs` — the Swagger UI should load with all endpoints listed.

---

## Step 4 — Install Bob Modes

Two specialist Bob modes are pre-bundled in this repository under `bob-modes-skills/`.

> Run these commands from the **repo root** (`lab-2752-reusable-agentic-patterns/`), not from inside a sub-folder.

### 4a — TTM Forecasting Mode (used in Lab 2)

```bash
mkdir -p .bob
cp bob-modes-skills/ttm-forecast/custom_modes.yaml .bob/custom_modes.yaml
cp -r bob-modes-skills/ttm-forecast/skills .bob/skills
```

### 4b — FleetOps Agent Builder Mode (used in Lab 3)

> Install this **after** Lab 2 so both modes coexist.

```bash
cat bob-modes-skills/agent-modes/custom_modes.yaml >> .bob/custom_modes.yaml
cp -r bob-modes-skills/agent-modes/rules-fleetops-agent-builder .bob/rules-fleetops-agent-builder
```

Restart Bob: `Cmd+Shift+P` → **Bob: Restart** (or close and reopen IBM Bob IDE).

Verify both modes appear in the mode selector (bottom-left of the Bob chat panel):
- 🔮 TTM Forecasting
- 🚛 FleetOps Agent Builder

---

## Step 5 — Validate watsonx Orchestrate Access

1. Open your watsonx Orchestrate tenant URL in a browser (provided by instructor).
2. Sign in with your IBM ID.
3. Confirm you can see **Build → Agents** in the left navigation.

> You will not create any agents until Lab 3. This step is access validation only.

---

## Validation Checklist

Before moving to Lab 1, confirm **all** items are checked:

- [ ] Repository cloned and open in IBM Bob IDE
- [ ] `01-fleet-backend/.env` filled with Orchestrate URL + API key
- [ ] `02-forecast-service/.env` filled (`USE_TTM_MODEL=False`)
- [ ] Fleet backend running on Python 3.12 — `http://localhost:8085/docs` loads
- [ ] Bob restarted — 🔮 TTM Forecasting mode visible in mode selector
- [ ] Bob restarted — 🚛 FleetOps Agent Builder mode visible in mode selector
- [ ] watsonx Orchestrate tenant accessible in browser

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `cp: fleetops-backend/.env.example: No such file or directory` | Use the correct paths: `01-fleet-backend/.env.example` and `02-forecast-service/.env.example` |
| `Failed building wheel for pydantic-core` | You are on Python 3.13 — install Python 3.12 and re-create the venv: `python3.12 -m venv venv` |
| `ModuleNotFoundError: No module named 'governance'` | You cloned the wrong branch. This lab uses `main` of `lab-2752-reusable-agentic-patterns` — re-clone and confirm you are in that repo, not `smart-cold-chain` |
| Fleet backend fails on other `import` error | Confirm venv is active (`which python` shows the venv path) and re-run `pip install -r requirements.txt` |
| Bob mode not appearing | Confirm `.bob/custom_modes.yaml` exists at repo root. Run `Bob: Restart`. |
| watsonx Orchestrate login fails | Confirm tenant URL and IBM ID with your instructor. Trial access must be pre-provisioned. |

---

**[→ Lab 1: Explore the Fleet Backend](../01-fleet-backend/README.md)**
