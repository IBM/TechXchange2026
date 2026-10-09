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
      iceberg_catalog.kpi_sNN.*  (native tables on IBM Cloud Object Storage)
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

> **Numbering note:** this guide uses fine-grained **Steps 0–7**. The official
> lab guide (`.docx`) groups the same work into **Tasks 1–5**:
> Task 1 = Steps 1–3 · Task 2 = Step 4 · Task 3 = Step 5 · Task 4 = Step 6 ·
> Task 5 = Step 7 (Step 0 is one-time setup). Either numbering lands in the same
> place.

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
git clone https://github.com/IBM/TechXchange2026
cd "TechXchange2026/Lab_2950_Building_a_Real_Time_Executive_KPI_Copilot_with_Confluent,_watsonx.data,_and_watsonx_BI"
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r producer/requirements.txt
```

Then generate your personal, prefixed lab files (this is a shared environment,
so everything you create is namespaced to your student number `sNN`):

```bash
python tools/generate_student_files.py --me sNN      # e.g. --me s07
```

This writes `students/sNN/` with your prefixed Flink SQL, a `client.properties`
template, your Spark bridge, and a `README.txt`. Throughout this guide, wherever
you see a bare name like `orders` or `kpi_revenue_per_minute`, use **your**
prefixed version (`sNN_orders`, `sNN_kpi_revenue_per_minute`) and schema
`kpi_sNN`.

✅ **Checkpoint:** `pip install` completed and `students/sNN/` was generated.

---

## Step 1 — Create the 5 Kafka topics

**Concept:** A topic is a named event stream. The producer writes 5 kinds of
events, one topic each.

1. Confluent Cloud → your **environment** → your **Kafka cluster** → **Topics**.
2. **Create topic** for each name below (Partitions = 1, **Create with
   defaults**, and **Skip** the "define a schema" prompt — the producer
   registers schemas for you in Step 2):

   `sNN_orders` · `sNN_payments` · `sNN_customers` · `sNN_shipments` · `sNN_refunds`

> **Shared cluster:** replace `sNN` with your assigned student number (e.g.
> `s07_orders`), and use the same prefix everywhere later. Your generated files
> already use your prefix.

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
TOPIC_PREFIX=sNN_ python producer/event_generator.py
# e.g.  TOPIC_PREFIX=s07_ python producer/event_generator.py  (trailing _ matters)
```
The banner shows your bootstrap server, Schema Registry URL, topic prefix, and
topics, then a per-second status line with climbing counters. If you forgot to
fill in `config/client.properties`, the script stops immediately with a clear
message naming the values to replace.

✅ **Checkpoint:** Counters climb; no `Delivery FAILED`. Leave it running.

---

## Step 3 — Observe events in Kafka

1. Confluent Cloud → **Topics → `sNN_orders` → Messages** → you see JSON messages.
2. Check **`sNN_payments`** — some have `"status": "failed"` (drives the failure
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
   DESCRIBE sNN_payments;  -- should list status, amount, region, ... (real columns)
   ```
   (A warning that the record **key** is BYTES/RAW is harmless. Only if the
   **value** columns show as BYTES did the producer's schema not register —
   recheck Step 2b/2c.)

3. Create the 4 KPI tables. **Run one statement at a time** (this workspace
   runs a single statement per execution). Each KPI file now has a
   **CREATE TABLE IF NOT EXISTS** (run once) followed by an **INSERT INTO**
   (the continuous job):

   | File | Creates | Statements |
   |------|---------|-----------|
   | `flink/01_kpi_revenue_per_minute.sql`    | `sNN_kpi_revenue_per_minute`    | CREATE TABLE, then INSERT INTO |
   | `flink/02_kpi_order_throughput.sql`      | `sNN_kpi_order_throughput`      | CREATE TABLE, then INSERT INTO |
   | `flink/03_kpi_payment_failure_rate.sql`  | `sNN_kpi_payment_failure_rate`  | CREATE TABLE, then INSERT INTO |
   | `flink/04_kpi_regional_sales_trends.sql` | `sNN_kpi_regional_sales_trends` | CREATE VIEW, CREATE TABLE, then INSERT INTO |

   (The copies in `students/sNN/flink/` already have your prefix applied.)

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
   SELECT * FROM sNN_kpi_revenue_per_minute;
   ```

✅ **Checkpoint:** `SHOW TABLES;` lists the 4 `sNN_kpi_*` tables and they return
rows. **Leave all 4 INSERT INTO statements running** (they feed Tableflow). To
resume a stopped KPI later, just re-run its `INSERT INTO`.

---

## Step 5 — Enable Tableflow (Iceberg on Confluent storage)

**Concept:** Tableflow materializes each KPI topic as an Apache Iceberg table.

For each of the 4 KPI topics (`sNN_kpi_revenue_per_minute`,
`sNN_kpi_order_throughput`, `sNN_kpi_payment_failure_rate`,
`sNN_kpi_regional_sales_trends`):

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

---

## Step 6 — Bridge to native Iceberg + query in Presto (watsonx.data)

**Concept:** A Spark job in watsonx.data reads the Tableflow KPIs and writes
them as **native** Iceberg tables on IBM COS (so Presto — and watsonx BI — can
read them).

### 6a — Prepare the bridge script
> The only Spark job you run is **your** `students/sNN/kpi_to_native_iceberg.py`
> (generated with your prefix in Step 0). The other two Spark files
> (`validate.py`, `read_tableflow.py`) are optional diagnostics — ignore them
> unless you need to debug the write or read path separately.

Log in to watsonx.data via the **App ID login URL from your TechZone
reservation** (NOT cloud.ibm.com directly). Open your generated
`students/sNN/kpi_to_native_iceberg.py` and confirm the source values (Tableflow
REST `REGION`/`ORG_ID`/`ENV_ID`, API key/secret, `CLUSTER_ID`) and destination
(`DEST_CATALOG` = `iceberg_catalog`, `DEST_SCHEMA` = `kpi_sNN`, `DEST_BUCKET` =
your COS bucket) are filled. Upload the file to your COS bucket and note its
object path, e.g. `s3a://<bucket>/kpi_to_native_iceberg.py`.

> The Iceberg catalog `iceberg_catalog` is already provisioned by your instructor
> on an IBM COS bucket and associated with both the Spark and Presto engines. You
> only need the bucket name (for the upload path) and the catalog name.

### 6b — Build the `spark.hadoop.wxd.apiKey` value (read carefully — most error-prone step)
1. `<userid>` is your **`studentNN@...techzone.com`** login (the same student ID
   you use for watsonx.data) — NOT a Confluent credential.
2. `<apikey>` is an **IBM Cloud IAM API key** — create one at **Manage → Access
   (IAM) → API keys → Create**. It is **NOT** the Confluent Tableflow key inside
   the bridge file; those are different credentials.
3. Base64-encode `ibmlhapikey_<userid>:<apikey>`:
   ```bash
   printf 'ibmlhapikey_%s:%s' '<userid>' '<iam_apikey>' | base64
   ```
4. The property value is the word `Basic`, one space, then that base64 string:
   `spark.hadoop.wxd.apiKey=Basic <base64-from-step-3>`

### 6c — Submit the Spark application
watsonx.data → **Infrastructure manager** → your **Spark engine** →
**Applications** → **Create application**:
- Application type: **Python**
- Application path: `s3a://<bucket>/kpi_to_native_iceberg.py`
- Spark version: **3.5**
- Application name: a **unique** name, e.g. `sNN-kpi-bridge`
- **Spark configuration properties** — enter these in the **"Spark
  configuration"** section, **NOT** any "environment variables" field. (These
  keys contain dots; as environment variables they fail with
  `spark-env.sh: ... not a valid identifier` and the bridge cannot authenticate.)

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

> **Confirm it was YOUR job that ran.** The Spark application list is **shared**
> across all students on this engine. Run **your** uniquely-named app pointing at
> **your** uploaded `kpi_to_native_iceberg.py` — never re-run an app you did not
> create. "Finished" alone is not proof: open the run **log** and confirm it
> bridged **your** cluster and tables into **your** schema (e.g.
> `... lkc-<yours> ... sNN_kpi_revenue_per_minute -> iceberg_catalog.kpi_sNN...
> wrote N rows`). If the log shows a different cluster/schema, you ran the wrong
> application and `kpi_sNN` will be empty.

### 6d — Verify in Presto (SQL workspace)
Switch engine to **Presto** and run:
```sql
SHOW SCHEMAS IN iceberg_catalog;             -- you should see kpi_sNN
SHOW TABLES IN iceberg_catalog.kpi_sNN;      -- your 4 sNN_kpi_* tables
SELECT * FROM iceberg_catalog.kpi_sNN.sNN_kpi_revenue_per_minute
ORDER BY window_start DESC LIMIT 20;
```

✅ **Checkpoint:** The 4 KPI tables appear in `iceberg_catalog.kpi_sNN` and
Presto returns rows. (Re-run the Spark job any time to refresh the snapshot.)

---

## Step 7 — Import KPIs & ask questions in watsonx BI

**Concept:** watsonx BI connects to watsonx.data via **Presto**, imports the
native KPI tables, and answers natural-language questions about them.

> Validated with just the Presto connection details + an API key — **no
> service-to-service authorization needed**, even across two different IBM Cloud
> accounts.

1. **Launch watsonx BI and get the connection JSON + API key:**
   - Open watsonx BI from its **TechZone App ID login URL in a SEPARATE browser**
     (or a separate profile / private window) from the one used for
     watsonx.data — the two services are on different TechZone accounts and
     sharing one browser causes a session/account clash.
   - In the **watsonx.data console → Configuration** tab, copy the **watsonx.data
     Presto connection details (JSON)** — it contains host, port, instance
     ID/name, CRN, and engine details in one blob.
   - Get your **API key** from the **TechZone reservation page** for this
     environment.
2. watsonx BI → **Data and Metrics** → **Create metrics** (name it, e.g.
   `KPI Copilot`) → **Add data** → **New connection** → **IBM watsonx.data
   Presto**.
3. **Paste the JSON** into the form; set **Username** = `ibmlhapikey_<userid>`
   (your `studentNN@...techzone.com`), **Password** = the API key, **SSL
   enabled** (+ certificate if requested). **Test connection** → **Create**.
4. Import **`iceberg_catalog` → `kpi_sNN`** → the 4 KPI tables.
5. Open the **conversation** and ask: *"What is our total revenue in the last 10
   minutes?"*, *"Which region has the highest net sales?"*, *"Is our payment
   failure rate increasing?"* (Optionally build a dashboard: revenue line chart,
   net-revenue bar by region, failure-rate tile.)

✅ **Checkpoint:** The KPI tables are imported and the Copilot answers a
question. 🎉

---

## You did it!

You built an end-to-end real-time operational intelligence pipeline, entirely
on Confluent + IBM technologies.

### Clean up (please do this)
- **Ctrl+C** the producer.
- **Stop the 4 Flink statements** (Flink workspace → Flink statements → Stop).
- Optionally: disable Tableflow, drop the `iceberg_catalog.kpi_sNN` tables, delete
  topics — if your instructor asks.

### Refresh the KPIs later
Re-run the Spark bridge (Step 6c) — it uses `createOrReplace`, so it refreshes
the native tables with the latest Tableflow snapshot.

### Troubleshooting
See `docs/troubleshooting.md` — it lists every error we hit during development
and its fix.
