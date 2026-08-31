# Live KPI Dashboard (Streamlit) — optional side track

A real-time operations screen that reads the four KPI Kafka topics **directly**
from Confluent Cloud and updates on a timer. This is the "live" complement to
the watsonx BI experience in the main lab.

```
Confluent KPI topics ──▶ background consumer thread (rolling in-memory store)
   (kpi_revenue_per_minute, …)          │
                                Streamlit UI (auto-refresh ~5s)
```

## How it differs from watsonx BI

| | watsonx BI (main lab) | This Streamlit app (side track) |
|---|-----------------------|--------------------------------|
| Data source | Native Iceberg **snapshot** (via Presto) | **Live** Kafka KPI topics |
| Freshness | As of the last Spark bridge run | Continuously updating |
| Purpose | Governed reports + NL Copilot | Live ops screen / demo |
| Runs on | watsonx BI (browser) | Presenter's laptop (`streamlit run`) |

The two are complementary — keep watsonx BI as the governed/AI story; use this
for the visceral "watch the numbers move" moment.

## Prerequisites

- The lab pipeline is producing KPIs: **producer running** + the **4 Flink KPI
  statements running** (so the `kpi_*` Kafka topics have data). Tableflow /
  watsonx are **not** required for this dashboard.
- `config/client.properties` filled in (same file the producer uses —
  bootstrap, cluster API key, Schema Registry URL + key).

## Run

```bash
pip install -r streamlit/requirements.txt
streamlit run streamlit/kpi_dashboard.py
# per-student prefixed topics:
TOPIC_PREFIX=s07_ streamlit run streamlit/kpi_dashboard.py
# change refresh cadence (seconds):
REFRESH_SECONDS=3 streamlit run streamlit/kpi_dashboard.py
```

Open the URL Streamlit prints (usually http://localhost:8501). The page
backfills recent KPI history on launch, then keeps updating live.

## What it shows

- Top metrics: latest revenue/min, orders/min, payment-failure %, net revenue.
- Revenue per minute (by region), Orders per minute, Payment failure rate,
  and Net revenue by region (latest 5-min window).

## Notes

- **Cost:** a single long-lived consumer tails the KPI topics; the browser
  refresh only re-renders the in-memory data (it does not re-read Kafka), so
  Confluent usage stays ~= the producer's small volume regardless of refresh
  rate.
- **Auth:** uses your existing cluster API key (consuming is allowed). No new
  credentials needed.
- **Positioning:** optional / instructor-demo. Not a required student step.
- **Empty charts?** Ensure the producer and the 4 Flink KPI statements are
  running; the 5-minute regional KPI needs a window to close before it appears.
