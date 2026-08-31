# Lab-2950 — Building a Real-Time Executive KPI Copilot
### Participant Guide (Step-by-Step)
**IBM TechXchange 2026 · Duration: ~90 minutes**

Welcome! In this lab you build a live pipeline that turns a stream of business
events into executive KPIs you can query and visualize — using Confluent Cloud,
Apache Flink, Tableflow, Apache Iceberg, IBM watsonx.data, and IBM watsonx BI.

No prior Kafka, Flink, or Spark experience is required. Follow each step in
order; every step has a ✅ checkpoint.

> This guide reflects the **validated** architecture. Some steps (Schema
> Registry, the Spark bridge job, the exact Spark configs) are not obvious —
> they are included because they are **required** for this stack to work.

---

## Architecture (what you will build)

```
 Python producer ──▶ Confluent Cloud (Kafka topics, JSON + Schema Registry)
                          │
                          ▼
                     Apache Flink  ── streaming KPI SQL (4 KPIs)
                          │  writes KPI results to new Kafka topics
                          ▼
                      Tableflow  ── materializes KPI topics as Apache Iceberg
                          │           (Confluent-managed storage)
                          ▼
        watsonx.data SPARK engine  ── "bridge" job:
                          │   reads Tableflow Iceberg (REST catalog)
                          │   writes NATIVE Iceberg tables on IBM COS
                          ▼
      iceberg_catalog.kpi.*  (native tables on IBM Cloud Object Storage)
                          │
                          ▼
        watsonx.data PRESTO engine ──▶ IBM watsonx BI
                                        (dashboards + natural-language Copilot)
```

### Why the Spark "bridge" step exists (important)
Tableflow stores Iceberg data in **Confluent-managed** storage, which watsonx BI
cannot read directly:
- watsonx BI connects to watsonx.data **only through Presto**.
- Presto **cannot** read Confluent-managed storage (no vended-credential
  support).
- The watsonx.data **Spark** engine **can** read it (via the Iceberg REST
  catalog), so we use Spark to copy the KPIs into **native** Iceberg tables on
  IBM Cloud Object Storage — which Presto (and therefore watsonx BI) **can**
  read.

This keeps the whole solution on **IBM storage** (no AWS/Azure/GCS bucket
needed).

| # | Step | Where |
|---|------|-------|
| 1 | Create Kafka topics | Confluent Cloud |
| 2 | Configure Schema Registry + run the Python producer | Laptop + Confluent Cloud |
| 3 | Observe events | Confluent Cloud |
| 4 | Compute 4 KPIs with Flink SQL | Confluent Cloud (Flink) |
| 5 | Enable Tableflow (Iceberg, Confluent storage) | Confluent Cloud |
| 6 | Run the Spark bridge → native Iceberg; query in Presto | watsonx.data |
| 7 | Build dashboards & ask questions | watsonx BI |

---

## Before you start

You need:
- [ ] **Confluent Cloud** access (shared environment) with a **Kafka cluster**.
- [ ] **IBM watsonx.data** (SaaS) access with a **Spark engine**, a **Presto
      engine**, and an **Iceberg catalog** (on IBM COS) associated with both.
- [ ] **IBM watsonx BI** access.
- [ ] The **lab GitHub repository** URL (from your instructor).
- [ ] On your laptop: **Python 3.9+** (`python3 --version`) and **Git**.

---

## Step 0 — Get the lab files

```bash
git clone github.ibm.com/itz-content/txc-2026-lab-2950
cd <REPO_FOLDER>/Lab-development
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r producer/requirements.txt
```

✅ **Checkpoint:** `pip install` completed without errors.

---

## Step 1 — Create the 5 Kafka topics

**Concept:** A topic is a named event stream. The producer writes 5 kinds of
events, one topic each.

1. Confluent Cloud → your **environment** → your **Kafka cluster** → **Topics**.
2. **Create topic** for each name below (Partitions = 1, **Create with
   defaults**, and **Skip** the "define a schema" prompt — the producer
   registers schemas for you in Step 2):

   `orders` · `payments` · `customers` · `shipments` · `refunds`

> **Shared cluster?** If your instructor assigned a prefix (e.g. `s07_`), name
> the topics `s07_orders`, etc., and use the same prefix everywhere later.

✅ **Checkpoint:** All 5 topics listed under **Topics**.

---

## Step 2 — Schema Registry + run the producer

**Concept:** Flink can only turn a topic into columns if the topic has a
registered **schema**. Our producer uses Confluent's JSON Schema Serializer to
**auto-register** a schema per topic — so you skip manual UI schema inference.

### 2a — Create a Kafka (cluster) API key
1. In your **cluster**, open **API Keys** → **Add key** → **My account** →
   **Next**. Copy the **Key** and **Secret** (secret is shown once).
2. **Cluster settings** → copy the **Bootstrap server** (ends in `:9092`).

> Make sure the key is **cluster-scoped** (created inside the cluster), not a
> global/cloud key — a cloud key cannot produce data.

### 2b — Create a Schema Registry API key
1. Open your **environment** → **Stream Governance** (a.k.a. Schema Registry).
2. Copy the **API endpoint** URL (looks like
   `https://psrc-xxxxx.<region>.<provider>.confluent.cloud`).
3. Create a **Schema Registry API key** + secret on that page.

### 2c — Fill in your connection file
```bash
cp config/client.properties.example config/client.properties
```
Edit `config/client.properties` and set:
```
bootstrap.servers=<YOUR_BOOTSTRAP_SERVER>:9092
sasl.username=<CLUSTER_API_KEY>
sasl.password=<CLUSTER_API_SECRET>
schema.registry.url=https://psrc-xxxxx.<region>.<provider>.confluent.cloud
schema.registry.basic.auth.user.info=<SR_KEY>:<SR_SECRET>
```

### 2d — Run the producer
```bash
python producer/event_generator.py
# with a prefix:  TOPIC_PREFIX=s07_ python producer/event_generator.py
```
The banner shows your bootstrap server, Schema Registry URL, and topics, then a
per-second status line with climbing counters.

✅ **Checkpoint:** Counters climb; no `Delivery FAILED`. Leave it running.

---

## Step 3 — Observe events in Kafka

1. Confluent Cloud → **Topics → `orders` → Messages** → you see JSON messages.
2. Check **`payments`** — some have `"status": "failed"` (drives the failure
   KPI).

✅ **Checkpoint:** Live JSON visible in at least two topics.

---

## Step 4 — Compute KPIs with Flink SQL

**Concept:** Flink is a live SQL calculator over your streams.

1. Confluent Cloud → **Flink** → create/enter a **compute pool** (smallest size
   is fine) → **Open SQL workspace**. Set the workspace **catalog =
   environment** and **database = your cluster** so it sees your topics.
2. Confirm schemas are registered: run
   ```sql
   SHOW TABLES;
   DESCRIBE payments;    -- should list status, amount, region, ... (real columns)
   ```
   (If `DESCRIBE` shows only `key`/`val` as BYTES, the producer's schema didn't
   register — recheck Step 2b/2c.)

3. Create the 4 KPI tables. **Run one statement at a time** (this workspace
   runs a single statement per execution). Each KPI file now has a
   **CREATE TABLE IF NOT EXISTS** (run once) followed by an **INSERT INTO**
   (the continuous job):

   | File | Creates | Statements |
   |------|---------|-----------|
   | `flink/01_kpi_revenue_per_minute.sql`    | `kpi_revenue_per_minute`    | CREATE TABLE, then INSERT INTO |
   | `flink/02_kpi_order_throughput.sql`      | `kpi_order_throughput`      | CREATE TABLE, then INSERT INTO |
   | `flink/03_kpi_payment_failure_rate.sql`  | `kpi_payment_failure_rate`  | CREATE TABLE, then INSERT INTO |
   | `flink/04_kpi_regional_sales_trends.sql` | `kpi_regional_sales_trends` | CREATE VIEW, CREATE TABLE, then INSERT INTO |

> Notes learned in testing:
> - **Resumable pattern:** Confluent Cloud auto-stops idle statements. Because
>   CREATE TABLE is separate from the INSERT INTO job, **to resume you just
>   re-run the `INSERT INTO` statement** — no "table already exists" error. (A
>   one-shot `CREATE TABLE AS SELECT` fails on resume because the table persists
>   after the job stops.)
> - Money columns (`amount`) are `DOUBLE`; the SQL `CAST(... AS DECIMAL(12,2))`
>   for clean display. The `CREATE TABLE` schemas are declared explicitly to
>   match.
> - The regional KPI blends payments + refunds via a `CREATE VIEW`; run its
>   three statements in order.

4. Verify (wait for a window to close — 1 min, or 5 min for regional):
   ```sql
   SELECT * FROM kpi_revenue_per_minute;
   ```

✅ **Checkpoint:** `SHOW TABLES;` lists the 4 `kpi_*` tables and they return
rows. **Leave all 4 INSERT INTO statements running** (they feed Tableflow). To
resume a stopped KPI later, just re-run its `INSERT INTO`.

---

## Step 5 — Enable Tableflow (Iceberg on Confluent storage)

**Concept:** Tableflow materializes each KPI topic as an Apache Iceberg table.

For each of the 4 KPI topics (`kpi_revenue_per_minute`, `kpi_order_throughput`,
`kpi_payment_failure_rate`, `kpi_regional_sales_trends`):

1. **Topics** → click the KPI topic → **Tableflow** tab → **Enable Tableflow**.
2. Table format: **Iceberg**.
3. Storage: **Use Confluent storage** (managed — simplest, no bucket needed).
4. Wait until status = **Syncing** and records/bytes begin to appear.

Then gather (for Step 6):
- The **Tableflow Iceberg REST Catalog endpoint**:
  `https://tableflow.<REGION>.aws.confluent.cloud/iceberg/catalog/organizations/<ORG_ID>/environments/<ENV_ID>`
- A **Tableflow API key + secret**.
- Your **Kafka cluster ID** (`lkc-...`) — this is the Iceberg **namespace**.

> The 5-minute regional KPI needs a window to close before it has rows to sync.
> Give Tableflow several minutes with the producer + Flink running.

✅ **Checkpoint:** All 4 KPI topics show Tableflow **Syncing** with data.

See `docs/06_spark_bridge_watsonxdata.md` for the deep-dive on Steps 5–6.

---

## Step 6 — Bridge to native Iceberg + query in Presto (watsonx.data)

**Concept:** A Spark job in watsonx.data reads the Tableflow KPIs and writes
them as **native** Iceberg tables on IBM COS (so Presto — and watsonx BI — can
read them).

### 6a — Prepare the bridge script
> The only Spark job you run is **`spark/kpi_to_native_iceberg.py`**. The other
> two Spark files (`validate.py`, `read_tableflow.py`) are optional diagnostics
> — ignore them unless you need to debug the write or read path separately.

Open `spark/kpi_to_native_iceberg.py` and set the source values (Tableflow REST
`REGION`/`ORG_ID`/`ENV_ID`, API key/secret, `CLUSTER_ID`) and destination
(`DEST_CATALOG` = your Iceberg catalog, `DEST_SCHEMA` = `kpi`, `DEST_BUCKET` =
your COS bucket). Upload the file to your COS bucket, e.g.
`s3a://<bucket>/spark/kpi_to_native_iceberg.py`.

### 6b — Get your watsonx.data API key (base64)
Generate a watsonx.data API key (Profile → Profile and Settings → API Keys),
then compute the value for `spark.hadoop.wxd.apiKey`:
```bash
echo -n "ibmlhapikey_<YOUR_IBMCLOUD_USERID>:<YOUR_WXD_API_KEY>" | base64
```
Use it as `Basic <base64>`.

### 6c — Submit the Spark application
watsonx.data → **Infrastructure manager** → your **Spark engine** →
**Applications** → **Create application**:
- Application type: **Python**
- Application path: `s3a://<bucket>/spark/kpi_to_native_iceberg.py`
- Spark version: **3.5**
- **Spark configuration properties** (all four are required):

  | Key | Value |
  |-----|-------|
  | `spark.hadoop.wxd.apiKey` | `Basic <base64 from 6b>` |
  | `spark.hadoop.fs.s3a.endpoint.region` | `<REGION>` (e.g. `us-east-2`) |
  | `spark.gluten.sql.columnar.batchscan` | `false` |
  | `spark.gluten.sql.columnar.filescan` | `false` |

> Why these configs (all discovered during testing):
> - `wxd.apiKey` — authenticates Spark to your IBM COS (read the .py + write
>   native tables).
> - `fs.s3a.endpoint.region` — the native reader needs the region or it hits
>   Tableflow's S3 with an HTTP **301** redirect.
> - `gluten...batchscan/filescan = false` — the Gluten/Velox native reader
>   cannot use Tableflow's vended credentials (HTTP **403**); disabling
>   columnar scan makes Spark fall back to the JVM reader, which works.

Submit → wait for **Finished**.

### 6d — Verify in Presto (SQL workspace)
Switch engine to **Presto** and run:
```sql
SHOW TABLES IN iceberg_catalog.kpi;
SELECT * FROM iceberg_catalog.kpi.kpi_revenue_per_minute
ORDER BY window_start DESC LIMIT 20;
```

✅ **Checkpoint:** The 4 KPI tables appear in `iceberg_catalog.kpi` and Presto
returns rows. (Re-run the Spark job any time to refresh the snapshot.)

---

## Step 7 — Import KPIs & ask questions in watsonx BI

**Concept:** watsonx BI connects to watsonx.data via **Presto**, imports the
native KPI tables, and answers natural-language questions about them.

> Validated with just the Presto connection details + an API key — **no
> service-to-service authorization needed**, even across two different IBM Cloud
> accounts.

1. **Get the connection JSON + API key:**
   - In the **watsonx.data console → Configuration** tab, copy the **watsonx.data
     Presto connection details (JSON)** — it contains host, port, instance
     ID/name, CRN, and engine details in one blob.
   - Get your **API key** from the **TechZone reservation page** for this
     environment.
2. watsonx BI → **Data and Metrics** → **Create metrics** (name it, e.g.
   `KPI Copilot`) → **Add data** → **New connection** → **IBM watsonx.data
   Presto**.
3. **Paste the JSON** into the form; set **Username** = `ibmlhapikey_<email>`,
   **Password** = the API key, **SSL enabled** (+ certificate if requested).
   **Test connection** → **Create**.
4. Import **`iceberg_catalog` → `kpi`** → the 4 KPI tables.
5. Open the **conversation** and ask: *"What is our total revenue in the last 10
   minutes?"*, *"Which region has the highest net sales?"*, *"Is our payment
   failure rate increasing?"* (Optionally build a dashboard: revenue line chart,
   net-revenue bar by region, failure-rate tile.)

✅ **Checkpoint:** The KPI tables are imported and the Copilot answers a
question. 🎉

Full details: `docs/07_watsonx_bi.md`.

---

## You did it!

You built an end-to-end real-time operational intelligence pipeline, entirely
on Confluent + IBM technologies.

### Clean up (please do this)
- **Ctrl+C** the producer.
- **Stop the 4 Flink statements** (Flink workspace → Flink statements → Stop).
- Optionally: disable Tableflow, drop the `iceberg_catalog.kpi` tables, delete
  topics — if your instructor asks.

### Refresh the KPIs later
Re-run the Spark bridge (Step 6c) — it uses `createOrReplace`, so it refreshes
the native tables with the latest Tableflow snapshot.

### Troubleshooting
See `docs/troubleshooting.md` — it lists every error we hit during development
and its fix.
