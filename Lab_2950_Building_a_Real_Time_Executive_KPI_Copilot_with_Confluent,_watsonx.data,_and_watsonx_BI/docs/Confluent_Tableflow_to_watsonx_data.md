# Integrating Confluent Tableflow with IBM watsonx.data
### A field-tested, self-contained how-to

This guide explains how to get Confluent Cloud data (via **Tableflow → Apache
Iceberg**) into **IBM watsonx.data** so it can be queried by **Presto** and used
by **IBM watsonx BI** — using only **IBM Cloud Object Storage** (no
AWS/Azure/GCS bucket).

It is written to stand on its own. Every step and configuration here was
validated end-to-end (IBM TechXchange Lab-2950). Where a setting is non-obvious,
a **Why** note explains the failure it prevents.

---

## TL;DR — the one thing to understand

Tableflow (with **Confluent-managed storage**) exposes your data as Apache
Iceberg through an **Iceberg REST catalog** that uses **remote-signed / vended
credentials**. Because of how the engines authenticate:

- **watsonx BI → watsonx.data works only through Presto.**
- **Presto cannot read Confluent-managed storage** (no vended-credential
  support).
- **The watsonx.data Spark engine *can* read it** — so you use a small **Spark
  "bridge" job** to read the Tableflow tables and **write them as NATIVE Iceberg
  tables on IBM COS**. Presto (and therefore watsonx BI) reads those native
  tables.

```
Confluent Tableflow (Iceberg REST, Confluent-managed S3)
    │  read by watsonx.data SPARK engine (remote signing)
    ▼
Spark bridge job  ──writes native Iceberg──▶  IBM Cloud Object Storage
    ▼
iceberg_catalog.<schema>.*   ──read by watsonx.data PRESTO──▶  watsonx BI
```

> **Do not** try to point Presto directly at Tableflow — it will fail with
> HTTP 403. The Spark bridge is the supported path, and it keeps all data on
> **IBM storage**.

---

## Prerequisites

### Confluent Cloud
- A Kafka cluster with one or more **topics that have data and a registered
  schema** (Tableflow needs a schema to materialize columns).
- **Tableflow enabled** on those topics using **"Use Confluent storage"**
  (Iceberg format).
- The **Iceberg REST Catalog endpoint** (Tableflow tab), format:
  `https://tableflow.<REGION>.aws.confluent.cloud/iceberg/catalog/organizations/<ORG_ID>/environments/<ENV_ID>`
- A **Tableflow API key + secret**.
- Your **Kafka cluster ID** (`lkc-...`) — this is the Iceberg **namespace**.

### IBM watsonx.data (SaaS)
- A **Spark engine** running. Either:
  - Apache Gluten accelerated Spark 3.5 (needs two extra configs — see below), or
  - a plain **native** (non-Gluten) Spark engine (simplest — no Gluten configs).
- A **Presto engine** running.
- An **Apache Iceberg catalog** (e.g. `iceberg_catalog`) backed by an **IBM COS
  bucket**, **associated with BOTH** the Spark and Presto engines.
- A **watsonx.data API key** (Profile → Profile and Settings → API Keys) and
  your **IBM Cloud user id / email**.

---

## Step 1 — Enable Tableflow (Confluent Cloud)

For each topic you want in watsonx.data:
1. **Topics** → select topic → **Tableflow** tab → **Enable Tableflow**.
2. Table format: **Iceberg**.
3. Storage: **Use Confluent storage**.
4. Wait until status shows **Syncing** and records/bytes appear.

> **Why not IBM COS here?** Tableflow bring-your-own-storage supports only
> AWS S3 / Azure / GCS — **not** IBM COS. So we use Confluent-managed storage
> and bridge to IBM COS with Spark (Step 3).

> **"Syncing but 0 bytes"?** Materialization lag. Keep producing data; wait
> several minutes. Windowed/aggregated topics only emit when a window closes.

---

## Step 2 — Register the destination catalog (watsonx.data)

If you don't already have an Iceberg catalog on IBM COS:

1. **Infrastructure manager → Add component → Storage → IBM Cloud Object
   Storage.**
2. Provide bucket name, region, endpoint, and **HMAC** access/secret keys
   (COS → Service credentials with the HMAC option).
3. Enable **Associate Catalog** → Catalog type **Apache Iceberg** → name it
   (e.g. `iceberg_catalog`).
4. **Associate the catalog with BOTH engines**: Infrastructure manager → select
   the **Spark** engine → Associate catalog; repeat for the **Presto** engine.

> **Why both?** Spark writes the native tables; Presto reads them for BI. Both
> engines must see the catalog.

---

## Step 3 — Run the Spark bridge job

Use the provided `kpi_to_native_iceberg.py` as a template (or the generic
`bridge_tableflow_to_native.py` pattern below). It:
1. Registers the Tableflow Iceberg REST catalog as a Spark catalog `tableflow`.
2. Reads the desired table(s), selecting only the business columns (dropping
   Tableflow's internal `$$topic`, `$$offset`, `$$raw-value`, … metadata).
3. Writes native Iceberg tables into `iceberg_catalog.<schema>` on IBM COS via
   `createOrReplace()` (idempotent full refresh).

### 3a — Fill in the script values
- Source: `REGION`, `ORG_ID`, `ENV_ID`, `TABLEFLOW_APIKEY`, `TABLEFLOW_SECRET`,
  `CLUSTER_ID`.
- Destination: `DEST_CATALOG` (e.g. `iceberg_catalog`), `DEST_SCHEMA`,
  `DEST_BUCKET` (your COS bucket).

> The filled-in file contains a real API key — **do not commit it**. Keep a
> placeholder `.example` in Git and git-ignore the real one.

### 3b — Upload the script to COS
e.g. `s3a://<your-bucket>/spark/bridge.py`.

### 3c — Compute the COS auth value
```bash
echo -n "ibmlhapikey_<YOUR_IBMCLOUD_USERID>:<YOUR_WXD_API_KEY>" | base64
```
Use it as `Basic <base64>` for `spark.hadoop.wxd.apiKey`.

### 3d — Submit (UI, no curl/VS Code needed)
Infrastructure manager → **Spark engine** → **Applications** → **Create
application**:
- Application type: **Python**
- Application path: `s3a://<your-bucket>/spark/bridge.py`
- Spark version: **3.5**
- **Spark configuration properties**:

  | Key | Value | Purpose / Why |
  |-----|-------|---------------|
  | `spark.hadoop.wxd.apiKey` | `Basic <base64>` | Auth Spark to IBM COS (read .py + write native tables). Without it: `Please provide valid api key`. |
  | `spark.hadoop.fs.s3a.endpoint.region` | `<REGION>` (e.g. `us-east-2`) | Native S3 reader region. Without it: **HTTP 301**. |
  | `spark.gluten.sql.columnar.batchscan` | `false` | **Gluten engine only.** Forces JVM Iceberg scan. Without it: **HTTP 403** (Velox can't do vended creds). |
  | `spark.gluten.sql.columnar.filescan` | `false` | Same as above. |

> **On a plain native (non-Gluten) Spark engine**, omit the two
> `spark.gluten.*` configs — there's no Velox offload, so the JVM reader (which
> honors remote signing) is used automatically.

Submit → wait for **Finished**.

### Harmless log messages (ignore)
- `Cannot call methods on a stopped SparkContext` at the end — Gluten's
  post-run listener after `spark.stop()`; data is already written.
- `GlutenFallbackReporter: Validation failed ... FallbackByUserOptions` — the
  intended scan fallback.
- `OAuth2Manager ... missing oauth2-server-uri` — informational.

---

## Step 4 — Verify in Presto

watsonx.data SQL workspace → engine = **Presto**:
```sql
SHOW SCHEMAS IN iceberg_catalog;
SHOW TABLES IN iceberg_catalog.<schema>;
SELECT * FROM iceberg_catalog.<schema>.<table> LIMIT 20;
```
You should see clean business columns (no `$$` metadata). This confirms the data
is now BI-ready.

---

## Step 5 — (Optional) Connect watsonx BI

watsonx BI reads watsonx.data via **Presto**. In our validated run this needed
**only** the Presto connection details + an API key — **no service-to-service
authorization**, even with watsonx.data and watsonx BI in **two different IBM
Cloud accounts** (the connector uses an explicit API key, so it connects as a
normal client).

Proven flow:
1. In the **watsonx.data console → Configuration** tab, copy the **Presto
   connection details as JSON** (host, port, instance ID/name, CRN, engine
   details — all in one blob).
2. Get the **API key** (in a TechZone-provisioned environment, from the
   **TechZone reservation page**; otherwise an IAM API key).
3. watsonx BI → **Data and Metrics → Create metrics → Add data → New connection
   → IBM watsonx.data Presto**. **Paste the JSON**, set username
   `ibmlhapikey_<email>`, password = the API key, SSL enabled. **Test → Create**.
4. Import the `iceberg_catalog.<schema>` tables, then ask KPI questions in the
   conversation experience.

---

## Generic bridge script (reference)

Minimal, reusable version. Replace the placeholders and the
`TABLES` mapping with your topic names + the columns you want to keep.

```python
from pyspark.sql import SparkSession

# --- Source: Confluent Tableflow (fill these in) ---------------------------
REGION           = "us-east-2"
ORG_ID           = "<YOUR_ORG_ID>"
ENV_ID           = "<YOUR_ENV_ID>"
TABLEFLOW_APIKEY = "<TF_KEY>"
TABLEFLOW_SECRET = "<TF_SECRET>"
CLUSTER_ID       = "<lkc-xxxxx>"          # Kafka cluster id = Iceberg namespace

# --- Destination: native Iceberg on IBM COS --------------------------------
DEST_CATALOG = "iceberg_catalog"
DEST_SCHEMA  = "kpi"
DEST_BUCKET  = "<YOUR_COS_BUCKET>"

# topic -> list of business columns to keep (drop $$... metadata)
TABLES = {
    "my_topic_1": ["col_a", "col_b", "col_c"],
    # "my_topic_2": [...],
}

REST_URI = (f"https://tableflow.{REGION}.aws.confluent.cloud/iceberg/catalog/"
            f"organizations/{ORG_ID}/environments/{ENV_ID}")

spark = (SparkSession.builder.appName("tableflow-to-native-iceberg")
    .enableHiveSupport()
    .config("spark.sql.catalog.tableflow", "org.apache.iceberg.spark.SparkCatalog")
    .config("spark.sql.catalog.tableflow.type", "rest")
    .config("spark.sql.catalog.tableflow.uri", REST_URI)
    .config("spark.sql.catalog.tableflow.credential", f"{TABLEFLOW_APIKEY}:{TABLEFLOW_SECRET}")
    .config("spark.sql.catalog.tableflow.io-impl", "org.apache.iceberg.aws.s3.S3FileIO")
    .config("spark.sql.catalog.tableflow.rest-metrics-reporting-enabled", "false")
    .config("spark.sql.catalog.tableflow.s3.remote-signing-enabled", "true")
    .config("spark.sql.catalog.tableflow.client.region", REGION)
    .config("spark.sql.catalog.tableflow.s3.region", REGION)
    .config("spark.hadoop.fs.s3a.endpoint.region", REGION)
    .config("spark.hadoop.fs.s3a.endpoint", f"s3.{REGION}.amazonaws.com")
    # Gluten engine only (harmless on native Spark):
    .config("spark.gluten.sql.columnar.batchscan", "false")
    .config("spark.gluten.sql.columnar.filescan", "false")
    .getOrCreate())

spark.sql(f"CREATE DATABASE IF NOT EXISTS {DEST_CATALOG}.{DEST_SCHEMA} "
          f"LOCATION 's3a://{DEST_BUCKET}/{DEST_SCHEMA}/'")

for table, cols in TABLES.items():
    src = f"tableflow.`{CLUSTER_ID}`.{table}"
    dst = f"{DEST_CATALOG}.{DEST_SCHEMA}.{table}"
    df = spark.sql(f"SELECT {', '.join(cols)} FROM {src}")
    df.writeTo(dst).using("iceberg").createOrReplace()
    print(f"wrote {spark.table(dst).count()} rows -> {dst}")

spark.stop()
```

Submit it with the same four Spark configuration properties from Step 3d.

---

## requirements / environment notes

- **No local Python packages needed** to run the bridge — it executes on the
  watsonx.data Spark engine (Spark 3.5, Iceberg + AWS bundle are already on the
  engine). You only need a text editor and access to the COS bucket + the
  watsonx.data console.
- If you develop/lint the script locally, `pyspark==3.5.*` is enough for syntax;
  you cannot actually run it locally against watsonx.data.
- **Region**: use your **Confluent** cluster region for all region configs (the
  Tableflow data bucket lives there).
- **Refreshing data**: re-run the bridge; `createOrReplace` overwrites the native
  tables with the latest Tableflow snapshot. (This is a batch snapshot, not
  continuous streaming.)

---

## Error → fix cheat sheet

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Please provide valid api key` (on `.py` fetch) | Missing `wxd.apiKey` | Set `spark.hadoop.wxd.apiKey=Basic <base64>` |
| `HTTP 301 Failed to get metadata for S3 object` | Native reader wrong region | `spark.hadoop.fs.s3a.endpoint.region=<region>` |
| `HTTP 403 Access denied` on `.parquet` | Velox can't do vended creds | `spark.gluten.sql.columnar.batchscan=false` + `filescan=false` (or use native Spark engine) |
| `ParseException ... '<'` | Placeholders not filled | Replace `<...>` before uploading |
| `SHOW TABLES` empty in Presto | Catalog not associated to Presto / bridge didn't write | Associate catalog to Presto; re-run bridge |
| Presto can't read Tableflow directly | By design (no vended creds) | Use the Spark bridge; never point Presto at Tableflow |
| watsonx BI connection test fails | Wrong Presto JSON/engine details or stale API key | Re-check pasted JSON, engine host/ID/port, SSL cert, and API key (s2s auth NOT required) |

---

## Why this design (summary for reviewers)

- **All data on IBM storage** (IBM COS) — no reliance on AWS/Azure/GCS buckets,
  which matters for an all-IBM story.
- **Supported connectors only**: Spark reads Tableflow (documented by IBM),
  Presto reads native Iceberg, watsonx BI reads Presto.
- **The Spark bridge is required** because Tableflow-managed storage +
  vended credentials are incompatible with Presto's reader; Spark is the only
  watsonx.data engine that can read it, so it materializes BI-ready native
  tables.

*Validated for IBM TechXchange 2026 · Lab-2950.*
