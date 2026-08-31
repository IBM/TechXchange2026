# Instructor / Setup Guide — Lab-2950
### Building a Real-Time Executive KPI Copilot

For the **lab owner / instructor**. Covers provisioning, the proven
architecture, the delivery model for 30 participants, and cost control.

> This guide reflects the **validated** design. The path from Tableflow to
> watsonx BI is not the "obvious" one — read section 5 (Architecture decisions)
> before provisioning, it will save you hours.

---

## 1. Environments

| Environment | Purpose | Sharing model |
|-------------|---------|---------------|
| **Confluent Cloud** (1 account) | Kafka topics, Schema Registry, Flink, Tableflow | Shared across all ~30 students |
| **IBM Cloud account #1** | **watsonx.data + COS** (Spark + Presto engines, Iceberg catalog) | Shared; 30 TechZone student IDs |
| **IBM Cloud account #2** | **watsonx BI** | Shared; same 30 student IDs |

> The 30 student IDs (from the TechZone reservation) isolate **logins**, not
> **resources** — everyone shares one Kafka cluster and one watsonx.data
> catalog. Isolation is achieved with a **per-student prefix `sNN_`** and a
> per-student watsonx.data **schema `kpi_sNN`**.
>
> **See `docs/SHARED_ENV_PLAN.md`** for the full "who does what once vs.
> per-student" breakdown — read it before the event.


No separate shared backend is required; the GitHub repo supplies all artifacts.

---

## 2. Proven end-to-end architecture

```
Python producer → Kafka (+ Schema Registry) → Flink (4 KPIs)
   → Tableflow (Iceberg, Confluent-managed storage)
   → watsonx.data SPARK bridge job (reads Tableflow REST catalog,
                                    writes NATIVE Iceberg on IBM COS)
   → iceberg_catalog.kpi.*  → watsonx.data PRESTO → watsonx BI
```

Full technical detail: `docs/06_spark_bridge_watsonxdata.md`.

---

## 3. Confluent Cloud setup (shared)

**Recommended: one shared Basic cluster + one shared Flink pool + per-student
prefixes.**

1. One **environment** + one **Basic Kafka cluster** (first eCKU free; ample for
   30 students' light traffic).
2. Enable **Stream Governance / Schema Registry** on the environment — the
   producer auto-registers JSON schemas (required for Flink to see columns).
3. Enable **Flink** with one shared **compute pool**. Each student runs **4**
   always-on KPI statements (the regional KPI is a `CREATE VIEW` + one
   `CREATE TABLE AS`). Size the pool for ~30 × 4 concurrent statements; validate
   in a dry run.
4. Per-student isolation: assign a **prefix** (`s01_`…`s30_`). The producer
   accepts `TOPIC_PREFIX` (no code edit); students add the same prefix to topic
   and KPI table names in the Flink SQL.
5. **Enable Tableflow** with **Confluent-managed storage** (Iceberg). Do **not**
   attempt bring-your-own IBM COS — Tableflow BYOS supports only AWS/Azure/GCS,
   not IBM COS.

Pre-create per-student **cluster API keys** + **Schema Registry API keys** (or
let students self-create if roles allow). Also create per-student **Tableflow
API keys** for the REST catalog.

---

## 4. IBM watsonx.data setup

1. Provision **both** engine types:
   - A **Spark engine** (Apache Gluten accelerated Spark 3.5 works; a plain
     native Spark engine also works and avoids the Gluten scan-fallback config).
   - A **Presto engine** (watsonx BI connects through this).
2. Register an **IBM Cloud Object Storage** bucket as watsonx.data storage and
   **associate an Apache Iceberg catalog** (e.g. `iceberg_catalog`) with **both**
   the Spark and Presto engines. This bucket also serves as the Spark engine's
   home/log bucket needs (use a real COS bucket, not the IBM-managed one, for
   logs).
3. **Student IDs**: create per-student IBM Cloud IAM users; grant access to the
   watsonx.data instance, both engines, and the catalog. For isolation, use a
   **per-student schema** in the shared catalog (e.g. `kpi_s01`) or a per-student
   catalog — match this to the Confluent prefix scheme. The Spark bridge's
   `DEST_SCHEMA` maps a student's KPIs into their own schema.
4. Note the **Spark engine ID**, **instance CRN**, and **region** — students
   need these (or the UI submit form) for the bridge job.
5. **watsonx BI connection**: the BI **IBM watsonx.data Presto** connector needs
   only the Presto connection JSON + an API key. In our validated run **no
   service-to-service authorization was required**, even with watsonx.data and
   watsonx BI in **two different IBM Cloud accounts** (the API key makes BI a
   normal client). If profiling specifically fails, s2s auth (watsonx.data
   `s2s_auth`) is the fallback to check.

---

## 5. Architecture decisions (read this — hard-won)

These are the non-obvious constraints we validated. They drive the whole design:

1. **watsonx BI → watsonx.data is Presto-only.** No Spark connector exists.
2. **Presto cannot read Confluent-managed Tableflow storage** (no vended /
   remote-signed credentials). So Presto cannot read Tableflow directly.
3. **The Spark engine CAN read Tableflow** (Iceberg REST catalog + remote
   signing) — but the **Gluten/Velox native reader cannot**. The Iceberg scan
   must fall back to the JVM reader via
   `spark.gluten.sql.columnar.batchscan=false` and `...filescan=false` (or use a
   plain native Spark engine).
4. The Spark native reader also needs `spark.hadoop.fs.s3a.endpoint.region` set
   or it hits Tableflow's S3 with an HTTP 301.
5. **Tableflow cannot write to IBM COS** (BYOS = AWS/Azure/GCS only).
6. Therefore the **Spark bridge** (read Tableflow → write native Iceberg on IBM
   COS) is mandatory; the native tables are what Presto and watsonx BI consume.
   This also keeps all data on **IBM storage** (good optics; no hyperscaler
   bucket needed).

---

## 6. Delivery model for 30 participants (recommended)

The full Spark-bridge path took many non-obvious configs to get right. For a
90-minute lab, minimize per-student failure surface:

**Recommended — instructor pre-runs the Spark bridge; students do everything
else.**
- Students: create topics, run the producer, observe events, author the Flink
  KPIs, enable Tableflow, then **query the native tables in Presto** and **build
  the watsonx BI dashboard**.
- Instructor: pre-provision the Iceberg catalog + engines, provide the Presto
  connection JSON + API key,
  and either (a) pre-run the Spark bridge so `iceberg_catalog.kpi.*` already
  exists, or (b) provide a ready-to-submit bridge app with the 4 Spark configs
  pre-filled so students click "Submit" once.
- This keeps the fragile Spark configs off the critical path for beginners while
  still exposing the full architecture conceptually.

**Advanced option** — students run the bridge themselves using
`docs/06_spark_bridge_watsonxdata.md`. Only do this with a longer session or a
technical audience.

---

## 7. GitHub repository (shared artifacts)

Publish `Lab-development/` to the lab repo. Layout:

```
Lab-development/
├── README.md
├── producer/            event_generator.py (+ requirements.txt)
├── config/              client.properties.example
├── flink/               00..04 KPI SQL (+ 04b fallback)
├── spark/               validate.py, read_tableflow.py(.example),
│                        kpi_to_native_iceberg.py(.example)
└── docs/                LAB_GUIDE.md, 05_tableflow_iceberg.md,
                         06_spark_bridge_watsonxdata.md, 07_watsonx_bi.md,
                         troubleshooting.md, INSTRUCTOR_GUIDE.md
```

**Never commit real credentials.** `.gitignore` excludes
`config/client.properties`, `spark/read_tableflow.py`, and
`spark/kpi_to_native_iceberg.py` (the filled-in Spark files carry Tableflow API
keys). Students copy the `.example` files and fill their own values.

---

## 8. Pre-conference dry run checklist

- [ ] Producer connects (with a `TOPIC_PREFIX`), streams to all 5 topics
- [ ] Schema Registry auto-registers schemas; Flink `DESCRIBE` shows columns
- [ ] All 4 Flink KPI tables create and emit rows (regional = view + CTAS)
- [ ] Confirm each student = 4 always-on statements
- [ ] Tableflow syncs all 4 KPI topics (managed storage)
- [ ] Spark bridge finishes; `iceberg_catalog.kpi.*` visible in Presto
- [ ] watsonx BI connects (Presto connector + API key; no s2s auth needed) and renders a chart
- [ ] Time the full run — fits in ~90 min with buffer
- [ ] Confirm the Confluent promo covers Flink + Tableflow (see §9)

---

## 9. Budget & cost control (~$1,500 Confluent promo)

- **Flink CFU-minutes** are the main Confluent cost — 4 always-on statements per
  student. Stop them promptly.
- **Basic** Kafka cluster; tiny data volume. Producer default is ~4 events/sec.
- **Tableflow** — small per-topic + per-GB.
- **watsonx.data** Spark/Presto bill when running — stop engines when idle;
  the Spark bridge is a short batch job.
- Dev-phase rules: stop Flink statements daily; pause the compute pool when
  idle; set a billing alert; verify the promo covers Flink + Tableflow.
- The **IBM Cloud accounts (watsonx.data, watsonx BI)** are separate from the
  Confluent promo — confirm their own funding.

---

## 10. Cleanup after the session

- Students: Ctrl+C producer; **stop the 4 Flink statements**; (optional) drop
  `iceberg_catalog.kpi` tables, disable Tableflow, delete topics.
- Instructor: stop/deprovision Spark + Presto engines and the Flink pool if
  temporary; revoke student IDs; tear down per cost policy.
