# Lab-2950 — Real-Time Executive KPI Copilot
### with Confluent, IBM watsonx.data, and IBM watsonx BI
**IBM TechXchange 2026 · Hands-on Lab**

Turn a live stream of business events into continuously updated executive KPIs
you can query in SQL and visualize/ask in natural language — end-to-end on
Confluent + IBM technologies.

Stream **orders, payments, customers, shipments, refunds** into Kafka; compute
**revenue per minute, order throughput, payment failure rate, and regional sales
trends** with Apache Flink; materialize them as **Apache Iceberg** via
**Tableflow**; bridge them into native Iceberg on **IBM Cloud Object Storage**
with the **watsonx.data Spark** engine; then query with **Presto** and build
dashboards + a natural-language Copilot in **watsonx BI**.

---

## Architecture (validated)

```
 Python producer ─▶ Confluent Cloud: Kafka topics (JSON + Schema Registry)
                          │
                          ▼
                     Apache Flink ── 4 streaming KPI queries
                          │
                          ▼
                      Tableflow ── Iceberg tables (Confluent-managed storage)
                          │
                          ▼
        watsonx.data SPARK engine ── bridge job: read Tableflow (REST catalog)
                          │            → write NATIVE Iceberg on IBM COS
                          ▼
      iceberg_catalog.kpi.*  (native Iceberg on IBM Cloud Object Storage)
                          │
                          ▼
        watsonx.data PRESTO engine ─▶ IBM watsonx BI (dashboards + NL Copilot)
```

**Why the Spark bridge?** watsonx BI reads watsonx.data only via **Presto**, and
Presto cannot read Confluent-managed Tableflow storage (no vended credentials).
The watsonx.data **Spark** engine can, so it copies the KPIs into **native**
Iceberg on IBM COS — which Presto and watsonx BI can read. Everything stays on
**IBM storage** (no AWS/Azure/GCS bucket required). Details:
`docs/06_spark_bridge_watsonxdata.md`.

**Tech stack:** Confluent Cloud · Apache Kafka · Schema Registry · Apache Flink ·
Tableflow · Apache Iceberg · IBM watsonx.data (Spark + Presto) · IBM watsonx BI.

---

## Repository layout

```
Lab-development/
├── README.md                       ← you are here
├── producer/
│   ├── event_generator.py          simulates the business; JSON + Schema Registry
│   └── requirements.txt
├── config/
│   └── client.properties.example   copy to client.properties, add your keys
├── flink/
│   ├── 00_inspect_source_topics.sql
│   ├── 01_kpi_revenue_per_minute.sql
│   ├── 02_kpi_order_throughput.sql
│   ├── 03_kpi_payment_failure_rate.sql
│   ├── 04_kpi_regional_sales_trends.sql          (CREATE VIEW + CREATE TABLE AS)
│   └── 04b_kpi_regional_sales_trends_fallback.sql (alternate 3-statement version)
├── spark/
│   ├── kpi_to_native_iceberg.py(.example)  ⭐ THE production bridge job (run this)
│   ├── validate.py                 diagnostic only: proves Spark→native Iceberg→Presto
│   └── read_tableflow.py(.example) diagnostic only: proves Spark can read Tableflow
└── docs/
    ├── LAB_GUIDE.md                 ⭐ participant step-by-step (Steps 0–7)
    ├── Confluent_Tableflow_to_watsonx_data.md  standalone integration how-to (share this)
    ├── 05_tableflow_iceberg.md      Tableflow deep-dive
    ├── 06_spark_bridge_watsonxdata.md  Spark bridge + all the config gotchas
    ├── 07_watsonx_bi.md             watsonx BI connection + dashboard
    ├── troubleshooting.md           every real error + fix
    └── INSTRUCTOR_GUIDE.md          provisioning, delivery model, cost
```

> Sharing 3 accounts across ~30 students? See **`docs/SHARED_ENV_PLAN.md`** for
> exactly what to set up once vs. what each student does (per-student `sNN_`
> prefix + `kpi_sNN` schema).

---

## Quick start (participants)

1. Read **`docs/LAB_GUIDE.md`** — Steps 0–7.
2. `pip install -r producer/requirements.txt`
3. `cp config/client.properties.example config/client.properties` and fill in
   bootstrap server + cluster API key/secret + Schema Registry URL/key.
4. `python producer/event_generator.py`
5. Flink KPIs → Tableflow → Spark bridge → Presto → watsonx BI (per the guide).

## Quick start (instructors)

See **`docs/INSTRUCTOR_GUIDE.md`** — engines (Spark **and** Presto), Iceberg
catalog on IBM COS, per-student isolation, the
recommended delivery model, and cost control.

---

## The four KPIs

| KPI | Flink table → native table | Window | Business question |
|-----|----------------------------|--------|-------------------|
| Revenue per minute | `kpi_revenue_per_minute` | 1 min | Money collected each minute, by region |
| Order throughput | `kpi_order_throughput` | 1 min | Orders/min + average order value |
| Payment failure rate | `kpi_payment_failure_rate` | 1 min | % of payments failing |
| Regional sales trends | `kpi_regional_sales_trends` | 5 min | Net sales (revenue − refunds) by region |

Each Flink KPI is a continuously running statement; the Spark bridge writes them
to `iceberg_catalog.kpi.*` for Presto + watsonx BI.

---

## Requirements

- Python 3.9+; Git.
- Confluent Cloud (Kafka, Schema Registry, Flink, Tableflow).
- IBM watsonx.data (SaaS) with **Spark + Presto** engines and an Iceberg catalog
  on IBM COS.
- IBM watsonx BI.

## Security

`.gitignore` excludes real secrets: `config/client.properties`,
`spark/read_tableflow.py`, `spark/kpi_to_native_iceberg.py` (the filled-in Spark
files embed Tableflow API keys). Commit only the `.example` templates.

---

*IBM TechXchange 2026 — Lab-2950.*
