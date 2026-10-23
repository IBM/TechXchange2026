---
name: ttm-forecasting
description: IBM Granite TTM forecasting skill — guides inference path selection (watsonx.ai native API vs local HuggingFace), generates service code, and optionally scaffolds a self-contained forecast dashboard.html for visualisation.
---

# Skill: TTM Time-Series Forecasting

## Description

Provides time-series forecasting capabilities using IBM Granite TTM (Tiny Time Mixer) for 96-step ahead predictions. This skill covers three inference paths — IBM watsonx.ai native serverless API, local HuggingFace pipeline, and mock/statistical fallback — and guides you to the right one based on your environment. It also scaffolds a self-contained `dashboard.html` for visualising forecast output when requested.

---

## When to Use

Use this skill when you need to:

- **Predict future values** in any time series
- **Temperature forecasting** for cold-chain logistics
- **Demand forecasting** for retail / supply chain
- **Energy consumption prediction** for utilities
- **Risk assessment** based on predicted threshold breaches
- **Build a forecast visualisation** (`dashboard.html`) from forecast API output

---

## Step 0 — Project Folder + Inference Path (Always Do This First)

### Project folder convention

**Always create a named project subfolder** before writing any files. Never drop service files into the workspace root.

```
<project_name>/          # e.g. stock_forecast/, cold_chain/, energy_monitor/
├── ttm_model.py         # IBM watsonx.ai API wrapper (Path 1) or local pipeline (Path 2)
├── forecasting_service.py
├── app.py               # Flask / FastAPI entry point
├── requirements.txt
├── .env.example         # credential template — never commit .env
└── README.md
```

Use a descriptive name derived from the use case (e.g. `stock_forecast` for financial data, `temp_monitor` for cold-chain). If the user's request implies adding TTM to an **existing** project, place files in the most logical existing subfolder rather than creating a new one.

### Inference path selection

Before writing any code, ask the user (or infer from context) which inference path applies. The three paths are mutually exclusive and have different prerequisites:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  PATH 1 — IBM watsonx.ai Native API  (RECOMMENDED for production)       │
│  Trigger : TTM_MODEL_ID is set in .env                                  │
│  Needs   : WML_API_KEY, WML_SPACE_ID, IBM_CLOUD_REGION                  │
│  Model   : ibm/granite-ttm-512-96-r2  (IBM SaaS hosted — no download)  │
│  Latency : ~1-2 s per call                                              │
│  Docker  : Single-stage, no model weights in image                      │
├─────────────────────────────────────────────────────────────────────────┤
│  PATH 2 — Local HuggingFace Pipeline  (macOS dev / air-gapped)          │
│  Trigger : USE_TTM_MODEL=True, TTM_MODEL_ID not set                     │
│  Needs   : granite-tsfm, torch, transformers installed                  │
│  Model   : ibm-granite/granite-timeseries-ttm-r2 (~2-3 GB download)    │
│  Latency : ~2-3 s on CPU after load; ~30-60 s first cold start          │
│  Docker  : 2-stage build (download on ARM, copy to AMD64 image)         │
├─────────────────────────────────────────────────────────────────────────┤
│  PATH 3 — Mock / Statistical Fallback  (development / CI only)          │
│  Trigger : TTM_MODEL_ID not set AND USE_TTM_MODEL=False                 │
│  Needs   : nothing extra                                                 │
│  Output  : Simulated sine-wave forecast — NOT suitable for production   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Decision guide

Ask these questions in order:

1. **Do you have an IBM Cloud account with WML enabled?**
   - Yes → use **Path 1**. Add `TTM_MODEL_ID`, `WML_API_KEY`, `WML_SPACE_ID`, `IBM_CLOUD_REGION` to `.env`.
   - No → continue to question 2.

2. **Are you on macOS / Linux dev machine and can install ~2-3 GB of model weights?**
   - Yes → use **Path 2**. Set `USE_TTM_MODEL=True` in `.env`, run `pip install granite-tsfm torch transformers`.
   - No → use **Path 3** (mock) for local dev/CI.

---

## Input Parameters

### Required

| Parameter | Type | Description |
|---|---|---|
| `historical_data` | `DataFrame` or list of `{"timestamp", "value"}` | Minimum 512 data points |

### Optional

| Parameter | Default | Notes |
|---|---|---|
| `frequency` | `"1min"` | Must be **lowercase**: `1min`, `5min`, `15min`, `1h`, `1d`. Uppercase variants break the TTM API. |
| `context_length` | `512` | Points fed to the model window |
| `prediction_length` | `96` | Fixed by the TTM model |
| `threshold` | `None` | Critical threshold for risk scoring |
| `cargo_type` | `None` | Passed to OpenScale payload logging when governance is active |

---

## Output Format

```json
{
  "predictions": [
    {"timestamp": "2024-01-01T00:00:00", "value": 2.5},
    {"timestamp": "2024-01-01T00:01:00", "value": 2.6}
  ],
  "model": "ibm/granite-ttm-512-96-r2",
  "inference_path": "native_api",
  "context_length": 512,
  "prediction_length": 96,
  "frequency": "1min",
  "risk_assessment": {
    "risk_score": 45,
    "time_to_breach": 72,
    "breach_probability": 0.35,
    "action": "MONITOR"
  },
  "metadata": {
    "inference_time_ms": 1450,
    "governance_logged": true
  }
}
```

`inference_path` will be one of: `"native_api"` | `"local_pipeline"` | `"mock"`.

---

## Path 1 — watsonx.ai Native API

### .env setup

```dotenv
# Activate native API path — this takes priority over USE_TTM_MODEL
TTM_MODEL_ID=ibm/granite-ttm-512-96-r2
WML_SPACE_ID=<your-wml-deployment-space-guid>
WML_API_KEY=<your-ibm-cloud-api-key>
IBM_CLOUD_REGION=us-south          # or eu-gb, eu-de, jp-tok, au-syd

# These must remain False / unset when using the native path
USE_TTM_MODEL=False
CONTEXT_LENGTH=512
PREDICTION_LENGTH=96
FREQUENCY=1min                     # MUST be lowercase
```

### How to get credentials

1. **WML_API_KEY** — IBM Cloud console → Manage → Access (IAM) → API keys → Create
2. **WML_SPACE_ID** — Watson Studio → Deployments → Spaces → your space → copy GUID from URL
3. **IBM_CLOUD_REGION** — match the region of your WML instance (check the service URL)

### Routing logic (from `ttm_model.py`)

```python
def forecast(self, historical_data):
    if self._ttm_model_id:                    # PATH 1 — native API
        return self.score_via_native_api(historical_data)
    if not self.model_loaded or not self.pipeline:
        raise RuntimeError("Model not loaded")
    # PATH 2 — local pipeline
    return self._run_local_pipeline(historical_data)
```

`is_loaded()` returns `True` immediately when `TTM_MODEL_ID` is set — no model download, no warmup wait.

### IAM token refresh

Tokens expire after ~1 hour. The wrapper refreshes automatically:

```python
if time.time() >= self._token_expiry - 60:   # refresh 60 s before expiry
    self._refresh_iam_token()
```

Never hardcode a bearer token. Always let `_refresh_iam_token()` fetch from `https://iam.cloud.ibm.com/identity/token`.

### Native API payload structure

```python
payload = {
    "model_id": "ibm/granite-ttm-512-96-r2",
    "space_id": WML_SPACE_ID,
    "schema": {
        "timestamp_column": "timestamp",
        "target_columns":   ["temperature"],   # column name in data dict
        "freq":             "1min",            # lowercase only
    },
    "parameters": {"prediction_length": 96},
    "data": {
        "timestamp":   ["2024-01-01T00:00:00", ...],   # ISO-8601 strings
        "temperature": [2.5, 2.6, 2.4, ...],           # 512 floats
    },
}
```

Response shape: `{"results": [{"temperature": [...96 floats...], "timestamp": [...]}]}`

---

## Path 2 — Local HuggingFace Pipeline

### .env setup

```dotenv
USE_TTM_MODEL=True
TTM_MODEL_ID=                       # leave empty — triggers local path
TTM_MODEL_PATH=ibm-granite/granite-timeseries-ttm-r2
TTM_MODEL_REVISION=main
CONTEXT_LENGTH=512
PREDICTION_LENGTH=96
FREQUENCY=1min
DEVICE=cpu                          # or cuda
```

### Install dependencies

```bash
pip install "granite-tsfm[notebooks]==0.3.3" torch transformers
```

### Loading sequence (preserve this exactly)

```python
from tsfm_public import TinyTimeMixerForPrediction, TimeSeriesForecastingPipeline

model = TinyTimeMixerForPrediction.from_pretrained(
    TTM_MODEL_PATH,
    revision=TTM_MODEL_REVISION
)
pipeline = TimeSeriesForecastingPipeline(
    model=model,
    timestamp_column="timestamp",
    id_columns=["id"],
    target_columns=["value"],
    context_length=CONTEXT_LENGTH,
    prediction_length=PREDICTION_LENGTH,
    freq=FREQUENCY,
    device=DEVICE,
)
```

**Do not** use `AutoModel.from_pretrained()` as a shortcut — it misses TTM-specific config and fails silently on Apple Silicon.

### Inference output normalisation

TTM pipeline outputs vary by TSFM version. Always normalise defensively:

```python
raw = pipeline(context_data)
# raw may be: dict, DataFrame, Series, ndarray, or nested list

if isinstance(raw, dict):
    raw = raw.get("prediction") or raw.get("forecast") or list(raw.values())[0]

if isinstance(raw, pd.DataFrame):
    col = next((c for c in ["value_prediction","prediction","forecast","value"]
                if c in raw.columns), None)
    raw = raw[col].values if col else raw.iloc[:, 0].values

arr = np.asarray(raw, dtype=float).flatten()
arr = arr[np.isfinite(arr)]          # strip NaN / Inf
arr = arr[:PREDICTION_LENGTH]        # truncate to horizon
```

### Docker 2-stage build (for OpenShift AMD64)

When bundling the local model into a container image:

```dockerfile
# Stage 1 — download model on native arch (e.g. ARM Mac)
FROM python:3.11-slim AS model-downloader
RUN pip install "granite-tsfm[notebooks]==0.3.3"
RUN python -c "from tsfm_public import TinyTimeMixerForPrediction; \
    TinyTimeMixerForPrediction.from_pretrained('ibm-granite/granite-timeseries-ttm-r2', \
    cache_dir='/cache')"

# Stage 2 — final AMD64 image
FROM --platform=linux/amd64 python:3.11-slim
COPY --from=model-downloader /cache /app/.cache/huggingface
ENV HF_HOME=/app/.cache/huggingface
```

> ⚠️ First build downloads ~2-3 GB. Use `--cache-from` in CI to avoid re-downloading on every build.
> For production, **Path 1 (native API) is strongly preferred** — it eliminates the large image entirely.

---

## Path 3 — Mock Fallback

Triggered automatically when neither `TTM_MODEL_ID` nor `USE_TTM_MODEL=True` is set. Returns a sine-wave-based simulated forecast. Use only in local dev / CI — never in production or demos.

---

## Governance / OpenScale Payload Logging

When `GOVERNANCE_PAYLOAD_LOGGING=true` and `governance/artifacts/deployment.json` contains valid OpenScale IDs, every native API call logs a payload record in a **fire-and-forget daemon thread** — forecast latency is never affected.

### What gets logged

| Field | Source |
|---|---|
| `temp_mean`, `temp_std`, `temp_min`, `temp_max` | Summary stats of the 512-point context window |
| `critical_threshold` | Passed from `forecasting_service.py` via `kwargs` |
| `cargo_type` | Passed from `forecasting_service.py` via `kwargs` |
| `predicted_temp_mean` | `mean(96-step forecast)` |

### Activating governance

```bash
cd governance/setup
python provision.py    # writes subscription_id and payload_data_set_id to deployment.json
```

Until `provision.py` has run, logging is silently skipped — it never blocks the service.

### Passing cargo context to the logger

```python
# In forecasting_service.py — set before calling forecast()
self.ttm_model._last_cargo_type         = cargo_type
self.ttm_model._last_critical_threshold = critical_threshold
predicted_temps = self.ttm_model.forecast(ttm_input)
```

---

## Fleet Concurrent Forecasting

The fleet endpoint (`forecast_fleet_optimization`) runs all 10 per-truck TTM calls in parallel using `ThreadPoolExecutor`. When adding new truck IDs or extending the fleet, adjust `FLEET_WORKERS` and `PER_TRUCK_TIMEOUT`:

```python
PER_TRUCK_TIMEOUT = 8        # seconds — one TTM native API round-trip
FLEET_WORKERS     = min(10, len(trucks))

with ThreadPoolExecutor(max_workers=FLEET_WORKERS) as pool:
    future_map = {pool.submit(_forecast_one, t['truckId']): t['truckId'] for t in trucks}
```

Each worker is independent — a timeout on one truck does not fail the others. Timed-out trucks fall back to the current-temp-vs-threshold heuristic.

---

## Cargo Temperature Normalisation

The simulation can push truck temperatures to extremes (e.g. +29 °C for a frozen-cargo truck). Before building the TTM context window, clamp to a realistic operating range:

```python
_CARGO_BASE = {
    'frozen_foods':                        -21.0,
    'temperature_sensitive_vaccines':      -15.0,
    'fresh_produce':                         6.0,
    'dairy_products':                        5.0,
    'pharmaceuticals':                       5.0,
}
cargo_base = _CARGO_BASE.get(cargo_type, telemetry_temp)

if abs(telemetry_temp - cargo_base) > 10:
    current_temp = critical_threshold + 2.0   # incident: slight breach margin
else:
    current_temp = telemetry_temp
```

This prevents garbage context windows from reaching the TTM model and keeps OpenScale drift monitoring meaningful.

---

## Dashboard Visualisation — `dashboard.html`

When the user asks to **visualise forecast output** or **build a dashboard**, scaffold a self-contained `dashboard.html` using the following pattern. The file must work by opening it directly in a browser — no server required.

### When to generate `dashboard.html`

Generate it when the user says any of:
- "build a dashboard", "visualise the forecast", "show me the chart", "create a forecast UI"
- "I want to see the predictions", "plot the temperature forecast"

### Template structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>TTM Forecast Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
  <style>
    body { margin: 0; font-family: -apple-system, "Segoe UI", sans-serif;
           background: #f7f8fa; color: #1f2328; }
    header { background: #1f2328; color: #fff; padding: 16px 24px;
             display: flex; align-items: center; gap: 12px; }
    header h1 { margin: 0; font-size: 18px; font-weight: 600; }
    .badge { background: #3b82d4; color: #fff; font-size: 11px;
             padding: 2px 8px; border-radius: 4px; }
    .cards { display: flex; gap: 16px; padding: 20px 24px 0; flex-wrap: wrap; }
    .card { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px;
            padding: 16px 20px; min-width: 160px; }
    .card .label { font-size: 11px; color: #57606a; text-transform: uppercase;
                   letter-spacing: .05em; }
    .card .value { font-size: 24px; font-weight: 700; margin-top: 4px; }
    .card .value.risk-high   { color: #dc2626; }
    .card .value.risk-medium { color: #d97706; }
    .card .value.risk-low    { color: #16a34a; }
    #chart { width: 100%; height: 420px; padding: 24px; box-sizing: border-box; }
    footer { text-align: center; font-size: 11px; color: #57606a;
             border-top: 1px solid #e5e7eb; padding: 12px; margin-top: 16px; }
  </style>
</head>
<body>

<header>
  <h1>TTM Forecast Dashboard</h1>
  <span class="badge" id="pathBadge">native api</span>
  <span style="margin-left:auto;font-size:13px;color:#9ca3af" id="metaLine"></span>
</header>

<div class="cards">
  <div class="card">
    <div class="label">Risk Score</div>
    <div class="value" id="riskScore">—</div>
  </div>
  <div class="card">
    <div class="label">Action</div>
    <div class="value" style="font-size:16px" id="riskAction">—</div>
  </div>
  <div class="card">
    <div class="label">Time to Breach</div>
    <div class="value" id="timeToBreach">—</div>
  </div>
  <div class="card">
    <div class="label">Predictions</div>
    <div class="value" id="predCount">—</div>
  </div>
</div>

<div id="chart"></div>

<footer>Made with IBM Bob · IBM Granite TTM · ibm/granite-ttm-512-96-r2</footer>

<script>
// ── Paste your forecast API response here ────────────────────────────────────
const FORECAST = /* INJECT_FORECAST_JSON */ null;
// ─────────────────────────────────────────────────────────────────────────────

// Or fetch from the live API:
// const FORECAST = await fetch('/api/forecast/temperature-breach/TRUCK-001')
//                        .then(r => r.json());

function renderDashboard(data) {
  if (!data) {
    document.getElementById('chart').innerHTML =
      '<p style="padding:40px;color:#57606a">Paste your forecast JSON into the FORECAST variable above.</p>';
    return;
  }

  const preds  = data.predictions || [];
  const risk   = data.risk_assessment || {};
  const meta   = data.metadata || {};
  const path   = data.inference_path || 'unknown';

  // Cards
  const score = risk.risk_score ?? '—';
  const scoreEl = document.getElementById('riskScore');
  scoreEl.textContent = typeof score === 'number' ? score + '%' : score;
  scoreEl.className = 'value ' +
    (score > 70 ? 'risk-high' : score > 40 ? 'risk-medium' : 'risk-low');

  document.getElementById('riskAction').textContent   = risk.action || '—';
  document.getElementById('timeToBreach').textContent =
    risk.time_to_breach != null ? risk.time_to_breach + ' min' : '—';
  document.getElementById('predCount').textContent    = preds.length;
  document.getElementById('pathBadge').textContent    = path.replace('_', ' ');
  document.getElementById('metaLine').textContent     =
    `${data.frequency || ''} · ${data.context_length || 512} ctx · ` +
    `${meta.inference_time_ms != null ? meta.inference_time_ms + ' ms' : ''}`;

  // Chart
  const timestamps = preds.map(p => p.timestamp.replace('T', ' ').slice(0, 16));
  const values     = preds.map(p => parseFloat(p.value.toFixed(3)));
  const threshold  = data.threshold ?? null;

  const series = [{
    name: 'Forecast', type: 'line', data: values,
    smooth: true, symbol: 'none',
    lineStyle: { color: '#3b82d4', width: 2 },
    areaStyle: { color: 'rgba(59,130,212,0.08)' },
  }];

  if (threshold !== null) {
    series.push({
      name: 'Threshold', type: 'line',
      data: new Array(values.length).fill(threshold),
      symbol: 'none',
      lineStyle: { color: '#dc2626', type: 'dashed', width: 1.5 },
    });
  }

  const chart = echarts.init(document.getElementById('chart'));
  chart.setOption({
    backgroundColor: '#ffffff',
    tooltip: { trigger: 'axis', formatter: params =>
      params.map(p => `${p.seriesName}: <b>${p.value}</b>`).join('<br>') },
    legend: { top: 8, right: 16, textStyle: { fontSize: 12 } },
    grid: { left: 56, right: 20, top: 40, bottom: 60 },
    xAxis: {
      type: 'category', data: timestamps, boundaryGap: false,
      axisLabel: { rotate: 30, fontSize: 11, color: '#57606a' },
      axisLine: { lineStyle: { color: '#e5e7eb' } },
    },
    yAxis: {
      type: 'value', name: 'Value',
      nameTextStyle: { color: '#57606a', fontSize: 11 },
      axisLabel: { color: '#57606a', fontSize: 11 },
      splitLine: { lineStyle: { color: '#f3f4f6' } },
    },
    series,
  });
  window.addEventListener('resize', () => chart.resize());
}

renderDashboard(FORECAST);
</script>
</body>
</html>
```

### How to wire it to the live API

Replace the `FORECAST = null` stub with a `fetch` call pointing at the forecast-backend:

```javascript
// Inject live data — call from forecast-backend running on port 5001
fetch('http://localhost:5001/api/forecast/temperature-breach/TRUCK-001')
  .then(r => r.json())
  .then(renderDashboard);
```

Or pass `--truck-id` and query from the command line to generate a static snapshot:

```bash
curl http://localhost:5001/api/forecast/temperature-breach/TRUCK-001 \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d, indent=2))"
# Paste the output into the FORECAST variable in dashboard.html
```

### File location convention

Place the generated `dashboard.html` at:
```
<project_name>/dashboard.html            # standalone new project
forecast-backend/dashboard.html          # existing per-service visualisation
FleetOps/public/forecast-dashboard.html  # embedded in an existing main UI
```

Always place it **inside the project subfolder** created in Step 0 — never at the workspace root.

---

## Risk Assessment Algorithm

```python
risk_score = int(
    0.5 * temperature_risk +   # forecast-based (TTM prediction vs threshold)
    0.3 * weather_risk +       # external weather data
    0.2 * value_risk           # cargo $ value normalised to 0-100
)
```

| Score | Level | Action |
|---|---|---|
| > 70 | CRITICAL | Immediate intervention — reroute to nearest station |
| 40–70 | WARNING | Monitor closely — prepare contingency plan |
| < 40 | NORMAL | Continue normal operations |

---

## Dependencies

### For Path 1 (native API) — minimal

```txt
requests>=2.31.0
pandas>=2.1.0
numpy>=1.26.0,<2.0.0
python-dotenv>=1.0.0
# Governance (optional — only if OpenScale logging is active)
ibm-cloud-sdk-core>=3.18.0
ibm-watson-openscale>=3.1.8
```

### For Path 2 (local pipeline) — full

```txt
torch>=2.4.0
transformers>=4.41.0
granite-tsfm>=0.2.0           # or "granite-tsfm[notebooks]==0.3.3" for full install
requests>=2.31.0
pandas>=2.1.0
numpy>=1.26.0,<2.0.0
```

### System requirements

| Requirement | Path 1 | Path 2 |
|---|---|---|
| RAM | 512 MB | 4–8 GB |
| Disk | minimal | ~2–3 GB model cache |
| GPU | not needed | optional (CUDA for faster inference) |
| Internet | IBM Cloud endpoint | HuggingFace Hub (first download only) |

---

## Troubleshooting

### `WML_API_KEY is not set` (Path 1)
Add `WML_API_KEY=<key>` to `.env`. For OpenShift, put it in the Secret — never in the ConfigMap.

### `401 Unauthorized` from native API
IAM token expired or `WML_SPACE_ID` is wrong. Verify the space GUID matches the region in `IBM_CLOUD_REGION`.

### `FREQUENCY` env var breaks the TTM model
Must be **lowercase** — `1min`, not `1MIN` or `1Min`. Uppercase variants are silently accepted by dotenv but rejected by the TTM API schema validator.

### Granite TTM loads inconsistently (Path 2)
Use the TSFM-first loading path (`TinyTimeMixerForPrediction.from_pretrained()` + `TimeSeriesForecastingPipeline`). Do not use `AutoModel.from_pretrained()` — it bypasses TTM-specific config on Apple Silicon.

### `AutoConfig.from_pretrained()` fails with `trust_remote_code`
Add `trust_remote_code=True` explicitly:
```python
from transformers import AutoConfig
config = AutoConfig.from_pretrained(TTM_MODEL_PATH, trust_remote_code=True)
```

### Pipeline returns unexpected shape (Path 2)
See the normalisation block in the **Path 2** section above. Always flatten to a strict 1-D `float` numpy array and strip `NaN`/`Inf` before risk scoring or JSON serialisation.

### `JSON serialization fails — NaN in response`
Use a `safe_float` helper before building the response:
```python
def safe_float(v):
    f = float(v)
    return f if np.isfinite(f) else None
```

### OpenScale payload logging silently skipped
`governance/artifacts/deployment.json` either doesn't exist or has no `payload_data_set_id`. Run `python governance/setup/provision.py` to populate it.

### Fleet endpoint is slow (>15 s)
All 10 per-truck forecasts must run concurrently. Check that `ThreadPoolExecutor` is being used with `FLEET_WORKERS = min(10, len(trucks))`. If a worker is blocking, increase `PER_TRUCK_TIMEOUT` (default 8 s).

---

## Version History

| Version | Date | Changes |
|---|---|---|
| 2.0.0 | 2025-07 | Added Path 1 (watsonx.ai native API), IAM token refresh, OpenScale logging, concurrent fleet forecasting, cargo normalisation, dashboard.html scaffold |
| 1.0.0 | 2024-01 | Initial release — local HuggingFace pipeline only |

## Author

**IBM Bob** — Smart Cold Chain Solution Team

## License

IBM Granite TTM is available under Apache 2.0. The `ibm-watson-openscale` SDK is Apache 2.0.
