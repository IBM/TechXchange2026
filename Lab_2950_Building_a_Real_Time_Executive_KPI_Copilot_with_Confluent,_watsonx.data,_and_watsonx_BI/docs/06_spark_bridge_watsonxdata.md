# Step 6 Deep-Dive: Spark Bridge → Native Iceberg → Presto (watsonx.data)

This is the most technical step. It documents exactly how the watsonx.data
**Spark** engine reads the Confluent Tableflow KPIs and writes them as **native**
Apache Iceberg tables on IBM Cloud Object Storage — which the **Presto** engine
(and watsonx BI) can then read. Every configuration here was validated during
lab development; the "why" notes explain the non-obvious parts.

---

## Why this step is necessary

```
Tableflow (Confluent-managed S3)  ──Spark reads (REST catalog, vended creds)──▶
    Spark bridge job  ──writes native Iceberg on IBM COS──▶
        iceberg_catalog.kpi.*  ──Presto reads──▶  watsonx BI
```

- **watsonx BI → watsonx.data is Presto-only.** No Spark connector exists.
- **Presto cannot read Confluent-managed storage** (no vended-credential /
  remote-signing support).
- **Spark can read it**, so Spark copies the data into a **native** Iceberg
  table on IBM COS. Presto reads native tables fine → watsonx BI works.
- Net result: **all data lands on IBM storage**; no AWS/Azure/GCS bucket needed.

---

## Prerequisites (one-time, instructor or student)

1. A watsonx.data **Spark engine** (Apache Gluten accelerated Spark 3.5 is what
   we tested) — **running**.
2. A watsonx.data **Presto engine** — **running**.
3. An **Apache Iceberg catalog** (e.g. `iceberg_catalog`) backed by an **IBM COS
   bucket**, **associated with BOTH** the Spark and Presto engines.
   - Register via Infrastructure manager → Add component → Storage → IBM Cloud
     Object Storage → provide bucket + region + endpoint + HMAC access/secret →
     enable **Associate Catalog** (type **Apache Iceberg**).
4. Tableflow enabled on the 4 KPI topics (Step 5), with the REST catalog
   endpoint + Tableflow API key + cluster ID in hand.

---

## The bridge job

File: `spark/kpi_to_native_iceberg.py` (template:
`spark/kpi_to_native_iceberg.py.example`).

It:
1. Registers the Tableflow **Iceberg REST catalog** as a Spark catalog alias
   `tableflow` (with remote signing).
2. Reads each KPI table's **business columns** (dropping Tableflow's internal
   `$$topic`, `$$offset`, `$$raw-value`, … metadata columns).
3. Writes each as a native Iceberg table into `iceberg_catalog.kpi.*` on IBM COS
   using `createOrReplace()` (idempotent full refresh).

### Fill in the placeholders (top of the file)
- Source (Tableflow): `REGION`, `ORG_ID`, `ENV_ID`, `TABLEFLOW_APIKEY`,
  `TABLEFLOW_SECRET`, `CLUSTER_ID`.
- Destination: `DEST_CATALOG` (e.g. `iceberg_catalog`), `DEST_SCHEMA` (`kpi`),
  `DEST_BUCKET` (your COS bucket).

> This file contains a real API key/secret when filled in, so it is
> **git-ignored**. Commit only the `.example` template.

---

## Submitting the job (UI, no curl/VS Code)

Upload the `.py` to COS (e.g. `s3a://<bucket>/spark/kpi_to_native_iceberg.py`),
then: Infrastructure manager → **Spark engine** → **Applications** →
**Create application**:

- Application type: **Python**
- Application path: `s3a://<bucket>/spark/kpi_to_native_iceberg.py`
- Spark version: **3.5**
- **Spark configuration properties** (all four required):

  | Key | Value | Purpose |
  |-----|-------|---------|
  | `spark.hadoop.wxd.apiKey` | `Basic <base64>` | Auth Spark to IBM COS (read .py, write native tables) |
  | `spark.hadoop.fs.s3a.endpoint.region` | `us-east-2` | Native reader region (avoids HTTP 301) |
  | `spark.gluten.sql.columnar.batchscan` | `false` | Force JVM Iceberg scan (avoids HTTP 403) |
  | `spark.gluten.sql.columnar.filescan` | `false` | Same as above |

### The `wxd.apiKey` value
```bash
echo -n "ibmlhapikey_<YOUR_IBMCLOUD_USERID>:<YOUR_WXD_API_KEY>" | base64
```
Prefix the result with `Basic ` in the property value.

---

## Why each config exists (hard-won lessons)

These were each discovered by hitting a real failure:

1. **`spark.hadoop.wxd.apiKey`** — Without it the job fails immediately with
   `WatsonxBasicSignatureCredentials: Please provide valid api key` while just
   trying to download the `.py` from COS. Required for any COS read/write.

2. **`spark.hadoop.fs.s3a.endpoint.region`** — The Tableflow data bucket is in
   `us-east-2`. The native (Velox) S3 reader does **not** inherit the Iceberg
   catalog's region, so it hit the wrong endpoint and returned **HTTP 301**
   ("Failed to get metadata for S3 object"). Setting the region fixes it.

3. **`spark.gluten.sql.columnar.batchscan/filescan = false`** — This is the big
   one. The **Gluten/Velox native C++ S3 reader cannot perform the Iceberg REST
   catalog's remote signing / vended credentials**, so it got **HTTP 403 Access
   denied** on the Parquet data files (even though `SHOW TABLES` worked via the
   Java client). Disabling Gluten's columnar **scan** offload makes the Iceberg
   scan fall back to the **JVM** reader, which honors remote signing. Gluten
   still accelerates other operators.

> Alternative to the Gluten configs: run on a **plain native (non-Gluten)
> Spark engine** — it has no Velox offload, so the JVM reader is used and remote
> signing works. Either approach is valid.

### Harmless warnings you can ignore
- `Cannot call methods on a stopped SparkContext` at the very end — Gluten's
  post-run fallback-report listener firing after `spark.stop()`. Your data is
  already written.
- `GlutenFallbackReporter: Validation failed ... FallbackByUserOptions` on the
  BatchScan — this is the **intended** scan fallback, not an error.
- `OAuth2Manager ... missing oauth2-server-uri` — informational.

---

## Verify in Presto

Switch the SQL workspace engine to **Presto**:
```sql
SHOW SCHEMAS IN iceberg_catalog;
SHOW TABLES IN iceberg_catalog.kpi;
SELECT * FROM iceberg_catalog.kpi.kpi_revenue_per_minute
ORDER BY window_start DESC LIMIT 20;
```
You should see the 4 KPI tables with clean business columns (no `$$` columns).

---

## Refreshing the data

The bridge takes a **snapshot**. Re-run the Spark application to refresh the
native tables with the latest Tableflow data (`createOrReplace` overwrites).
For a live demo, re-run it shortly before showing watsonx BI so the numbers are
current.

> Design note: this snapshot/batch approach is intentional for a 90-minute lab.
> A continuous/streaming refresh is possible but heavier and costlier; not
> recommended for the shared lab.

---

## Troubleshooting quick table

| Error in Spark log | Meaning | Fix |
|--------------------|---------|-----|
| `Please provide valid api key` (on `.py` fetch) | Missing/blank `wxd.apiKey` | Add `spark.hadoop.wxd.apiKey=Basic <base64>` |
| `HTTP 301 ... Failed to get metadata for S3 object` | Wrong S3 region for native reader | `spark.hadoop.fs.s3a.endpoint.region=<region>` |
| `HTTP 403 Access denied` on `.parquet` | Velox can't do vended creds | Set the two `spark.gluten...scan=false` configs (or use native Spark engine) |
| `ParseException ... '<'` | Placeholders not replaced in the .py | Fill `<...>` values before uploading |
| Presto: `SHOW TABLES IN iceberg_catalog.kpi` empty | Bridge didn't write / catalog not associated to Presto | Re-run bridge; associate catalog to Presto engine |
