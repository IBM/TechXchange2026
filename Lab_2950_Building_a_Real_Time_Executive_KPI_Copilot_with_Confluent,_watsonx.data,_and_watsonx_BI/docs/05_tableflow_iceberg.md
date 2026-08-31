# Step 5 Deep-Dive: Tableflow → Apache Iceberg (Confluent-managed storage)

Expands on **Step 5** of the participant guide. Read together with
`docs/06_spark_bridge_watsonxdata.md`, which covers how watsonx.data consumes
the Tableflow data.

## What Tableflow does

Tableflow reads a Kafka topic and continuously materializes it as an **Apache
Iceberg** table (Parquet data + Iceberg metadata) in object storage, and
exposes an **Iceberg REST Catalog** so external engines can read it.

```
Flink KPI topic  ──Tableflow──▶  Iceberg table + REST catalog
(kpi_revenue…)                    (Confluent-managed S3 storage)
```

## Storage choice for this lab: Confluent-managed

When enabling Tableflow you can pick **"Use Confluent storage"** (managed) or
**"Configure custom storage"** (bring-your-own bucket). **This lab uses
Confluent-managed storage.**

### Important facts we confirmed during development
- **Tableflow bring-your-own-storage supports only AWS S3 / Azure / GCS.** It
  does **NOT** support IBM Cloud Object Storage (even though COS is
  S3-compatible). So you cannot make Tableflow write directly into IBM COS.
- Therefore we use **Confluent-managed storage**, and later use a **Spark
  bridge** (Step 6) to copy the data into IBM COS as native Iceberg tables.
- Confluent-managed storage exposes an **Iceberg REST Catalog** that vends
  temporary (remote-signed) credentials. Only engines that support remote
  signing can read it — the watsonx.data **Spark** engine can; **Presto
  cannot**.

## Enabling Tableflow (per KPI topic)

Enable on the 4 KPI output topics (not the raw source topics):
`kpi_revenue_per_minute`, `kpi_order_throughput`, `kpi_payment_failure_rate`,
`kpi_regional_sales_trends`.

1. **Topics** → select the KPI topic → **Tableflow** tab → **Enable Tableflow**.
2. Table format: **Iceberg**.
3. Storage: **Use Confluent storage**.
4. Wait for **Syncing** and rising records/bytes.

## The connection details you need next (Step 6)

- **REST Catalog endpoint** (contains region, org, env):
  `https://tableflow.<REGION>.aws.confluent.cloud/iceberg/catalog/organizations/<ORG_ID>/environments/<ENV_ID>`
- **Tableflow API key + secret** (create in the Tableflow / API keys area).
- **Kafka cluster ID** (`lkc-...`) — this is the Iceberg **namespace** that
  contains the KPI tables.

## "Syncing but no data / 0 bytes"?

This is usually **materialization lag**, not an error:
- Tableflow only writes **committed, closed-window** KPI rows.
- The 1-minute KPIs need a minute to close; the **5-minute regional KPI needs 5
  minutes**.
- The first Parquet commit can take several minutes after enabling.

Fix: keep the **producer running** and the **Flink statements running**, verify
`SELECT * FROM kpi_revenue_per_minute;` returns fresh rows in Flink, then wait
~10–15 minutes and recheck the Tableflow tab.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Tableflow stuck "Provisioning" | Managed storage still initializing | Wait; retry enable |
| Syncing but 0 bytes | No closed-window data yet | Keep producer+Flink running; wait for windows to close |
| Can't find REST endpoint / API key | Looking in the wrong place | Tableflow tab / environment API-keys area |
| watsonx.data Spark read gets HTTP 403/301 | Storage auth/region | See `docs/06_spark_bridge_watsonxdata.md` |

> Do **not** try to point watsonx.data directly at Confluent-managed storage via
> Presto — it will fail (Presto has no vended-credential support). The Spark
> bridge in Step 6 is the supported path.
