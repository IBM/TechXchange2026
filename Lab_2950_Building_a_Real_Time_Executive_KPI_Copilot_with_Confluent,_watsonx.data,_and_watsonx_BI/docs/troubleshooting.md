# Troubleshooting Guide — Lab-2950

Fixes for issues we actually hit while building and validating this lab,
organized by step. Each entry lists the **symptom**, the **cause**, and the
**fix**.

---

## Step 0 / Setup

**`python3: command not found`** — Install Python 3.9+; or try `python`.

**`pip install` fails on confluent-kafka** — Upgrade pip
(`pip install --upgrade pip`). The producer needs the extras
`confluent-kafka[json,schemaregistry]` + `jsonschema` (already in
`producer/requirements.txt`).

---

## Step 1 — Topics

**"Topic already exists"** — Shared cluster collision. Prefix your topics
(`s07_orders`, …) and pass `TOPIC_PREFIX=s07_` to the producer.

---

## Step 2 — Schema Registry + producer

**`ERROR: Config file not found`** — Copy the template:
`cp config/client.properties.example config/client.properties` and fill it in.

**`ERROR: Schema Registry is not configured`** — You didn't add the two
`schema.registry.*` lines. Add the SR URL and `SR_KEY:SR_SECRET` (Step 2b/2c).

**`Delivery FAILED ... Authentication failed`** — Wrong cluster API key/secret,
or you used a **global/cloud** key instead of a **cluster-scoped** key. Create
the key from **inside the cluster**.

**`Delivery FAILED ... Unknown topic or partition`** — Topic name/prefix
mismatch. Confirm topic names match (including any `TOPIC_PREFIX`).

**Connection hangs / timeout** — Wrong `bootstrap.servers` (missing `:9092`) or
a corporate firewall blocking port 9092. Test on a non-corporate network.

**Schema Registry 401/403** — Wrong SR API key, or the key isn't for this
environment's Schema Registry. Regenerate on the Stream Governance page.

---

## Step 3 — Observe

**No messages in the UI** — The viewer only shows messages while open; click
**Jump to offset → latest** or wait. Confirm producer counters are climbing.

---

## Step 4 — Flink SQL

**`DESCRIBE payments` shows only `key`/`val` as BYTES** — The topic has **no
registered schema**. Root cause: the producer isn't using Schema Registry.
Re-check Step 2b/2c (SR URL + key), restart the producer, and confirm the banner
prints a Schema Registry URL. (Manual alternative: infer the schema in the topic
UI, but the producer-registered schema is the intended path.)

**`Column 'status' not found in any table`** — Same root cause as above: the
`payments` schema wasn't registered, so Flink can't see the `status` column.
Fix Schema Registry, then re-run.

**`SHOW TABLES;` doesn't list your topics** — The Flink workspace is attached to
a different environment/cluster. Reopen it against the correct env + cluster.

**Regional KPI: `SQL parse failed. Encountered "("`** — You tried to run the
inline-subquery version, or ran both statements at once. Use
`flink/04_kpi_regional_sales_trends.sql`: run the **`CREATE VIEW` first**, then
the **`CREATE TABLE AS`** — one statement at a time.

**`Only a single statement is supported at a time`** — This workspace runs one
statement per execution. Select and run each statement separately.

**KPI table created but `SELECT` returns nothing** — Windowed aggregates only
emit when a window closes (1 min; 5 min for regional). Keep the producer running
and wait.

**"failed creating table: table already exists" when resuming a KPI** — This is
the #1 gotcha. Confluent auto-stops idle Flink statements; the **table persists**
after the job stops, so re-running a `CREATE TABLE` (or old `CREATE TABLE AS
SELECT`) collides. **Fix:** the KPI files split CREATE from the job — **to
resume, run only the `INSERT INTO` statement** (skip the CREATE). If you edited
the schema or want a clean slate, `DROP TABLE <name>;` first, then run
CREATE + INSERT INTO again. (For the regional KPI, also re-create the view with
`CREATE VIEW IF NOT EXISTS sales_events ...` if it was dropped.)

---

## Step 5 — Tableflow

**Syncing but 0 bytes / no data** — Materialization lag. Keep producer + Flink
running; verify fresh rows in Flink (`SELECT * FROM kpi_...`); wait ~10–15 min.
The 5-minute regional KPI takes longest.

**Can't find REST endpoint / API key** — REST endpoint is on the Tableflow tab;
create the Tableflow API key in the environment's API-keys / Tableflow area.

**Don't use custom IBM COS storage** — Tableflow BYOS supports only
AWS/Azure/GCS, not IBM COS. Use **Confluent-managed storage** and the Spark
bridge (Step 6).

---

## Step 6 — Spark bridge (watsonx.data)

**`ParseException ... Syntax error at or near '<'`** — The `.py` still has
`<YOUR_...>` placeholders. Fill them in, re-upload to COS, re-submit.

**`WatsonxBasicSignatureCredentials: Please provide valid api key`** (fails while
downloading the `.py`) — Missing/blank `spark.hadoop.wxd.apiKey`. Set it to
`Basic <base64>` where base64 =
`echo -n "ibmlhapikey_<userid>:<apikey>" | base64`.

**`HTTP 301 ... Failed to get metadata for S3 object`** — The native reader used
the wrong S3 region. Add `spark.hadoop.fs.s3a.endpoint.region=<region>` (e.g.
`us-east-2`) and optionally `spark.hadoop.fs.s3a.endpoint=s3.<region>.amazonaws.com`.

**`HTTP 403 Access denied` on a `.parquet`** — The Gluten/Velox native reader
can't use Tableflow's vended credentials. Add
`spark.gluten.sql.columnar.batchscan=false` and
`spark.gluten.sql.columnar.filescan=false` (forces JVM Iceberg scan), or run on a
plain native (non-Gluten) Spark engine.

**`Cannot call methods on a stopped SparkContext`** (at the very end) —
Harmless. Gluten's fallback-report listener firing after `spark.stop()`. Your
data was already written.

**`GlutenFallbackReporter: Validation failed ... FallbackByUserOptions`** —
Expected/intended: it's the scan falling back to the JVM reader. Not an error.

**`[SCHEMA_NOT_FOUND]` on write** — The destination catalog/schema isn't right
or the catalog isn't associated with the Spark engine. Confirm `DEST_CATALOG`
and that the Iceberg catalog is associated with the Spark engine; the job
creates `DEST_SCHEMA` automatically.

**Presto: `SHOW TABLES IN iceberg_catalog.kpi` is empty** — Bridge didn't write,
or the catalog isn't associated with the **Presto** engine. Re-run the bridge;
associate the catalog with Presto; refresh the schema.

**`CREATE DATABASE ... LOCATION` conflicts** — If the location clause errors,
drop the `LOCATION` and let the catalog manage the path.

---

## Step 7 — watsonx BI

**Connection test fails** — Verify the pasted Presto connection JSON / engine
details (engine hostname without `:port`, engine ID, engine port), the **SSL
certificate**, and that the **API key** (from the TechZone reservation page) is
current. Note: **s2s authorization was NOT required** in our validated run
(API-key connection works, even across two IBM Cloud accounts); only investigate
s2s if profiling specifically fails.

**BI shows no data but Presto has rows** — Re-check the connection's engine
details; confirm you added the `iceberg_catalog.kpi` tables to the metrics
model. Re-run the Spark bridge if the native tables are stale/empty.

---

## General

**Everything was working, now it's empty after a break** — You stopped the
producer/Flink. New Kafka data flows only while the producer runs; new KPIs
compute only while the Flink statements run. Restart the producer, ensure the 4
Flink statements are running, wait for Tableflow to sync, then re-run the Spark
bridge to refresh the native tables.

Still stuck? Note the **step**, the **exact error text**, and which **engine**
(Spark vs Presto), and flag an instructor.
