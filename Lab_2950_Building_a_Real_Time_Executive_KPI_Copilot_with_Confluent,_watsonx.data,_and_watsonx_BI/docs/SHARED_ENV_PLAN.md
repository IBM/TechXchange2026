# Lab-2950 — Shared-Environment Plan (Who Does What)

Your environments are **shared** across all ~30 students:

- **1 Confluent Cloud account** (one environment + Kafka cluster) — shared.
- **1 IBM Cloud account** with **watsonx.data + COS** — shared; 30 student
  IDs/passwords (from the TechZone reservation) give login isolation.
- **1 IBM Cloud account** with **watsonx BI** — shared; same 30 IDs.

The student IDs isolate *logins*, not *resources* — everyone lands in the same
Kafka cluster and the same watsonx.data catalog. So the plan is: **you set up
shared pieces once and hand out per-student values; students do the per-student
work using a prefix.**

---

## The golden rule: every student gets a number `NN` (01–30)

Assign each student a two-digit number and a matching **prefix `sNN_`**. That
prefix is used for **Kafka topics, Flink KPI tables**, and the student's
**watsonx.data schema** (`kpi_sNN`). This is what prevents 30 people from
colliding in the shared cluster and catalog.

Example for student 07:
- Topics: `s07_orders`, `s07_payments`, … `s07_refunds`
- KPI tables: `s07_kpi_revenue_per_minute`, …
- Native schema: `iceberg_catalog.kpi_s07.*`

---

## A. Do ONCE (instructor) and share with students

### On Confluent Cloud (one time)
1. Create the **environment + Kafka cluster** (Basic) and enable **Stream
   Governance / Schema Registry**.
2. Enable **Flink** with a **compute pool** sized for ~30 × 4 statements
   (validate in a dry run; raise the max CFU if statements queue).
3. Ensure **Tableflow** is available on the environment.
4. **Pre-create, per student**, three API keys (or let students self-create if
   roles allow):
   - a **cluster (Kafka) API key** + secret,
   - a **Schema Registry API key** + secret,
   - a **Tableflow API key** + secret.
5. Note the **bootstrap server**, **Schema Registry URL**, the **Tableflow
   Iceberg REST Catalog endpoint** (region/org/env), and the **Kafka cluster
   ID** (`lkc-...`).

### On IBM watsonx.data (one time)
6. Provision a **Spark engine** and a **Presto engine**.
7. Register an **IBM COS bucket** as watsonx.data storage and **associate one
   Apache Iceberg catalog** (e.g. `iceberg_catalog`) with **BOTH** engines.
   (One shared catalog is fine — students isolate via their own **schema**
   `kpi_sNN`.)
8. Grant every **student ID** access to the watsonx.data instance, both engines,
   and the catalog.
9. Copy the **Presto connection JSON** (Configuration tab) — students paste this
   into watsonx BI. Note the **API key** source (TechZone reservation page).
10. Decide the **Spark-bridge delivery** (see section C) — pre-run it, or hand
    students a ready-to-submit job.

### On IBM watsonx BI (one time)
11. Confirm each student ID can open watsonx BI. (No service-to-service auth is
    required — the Presto connector uses the API key. Validated.)
12. (Optional) Build a **template dashboard** students can clone.

### Hand each student a slip with:
- Their **number `NN`** and prefix `sNN_`.
- Confluent **bootstrap server**, **Schema Registry URL**.
- Their **cluster / SR / Tableflow** API keys + secrets.
- **Tableflow REST catalog endpoint** + **Kafka cluster ID** (`lkc-...`).
- watsonx.data **Presto connection JSON** + **API key** (TechZone) + their
  **student ID/password**.
- The **GitHub repo URL**: `https://github.ibm.com/itz-content/txc-2026-lab-2950`.

---

## B. Students DO during the lab (per student, using their `sNN_` prefix)

| Step | Student action |
|------|----------------|
| 1 | Create their **5 prefixed topics** (`sNN_orders`, …) in the shared cluster |
| 2 | Fill `config/client.properties` (bootstrap, cluster key, SR url+key) and run `TOPIC_PREFIX=sNN_ python producer/event_generator.py` |
| 3 | Observe their events in their topics |
| 4 | In Flink, create their **4 prefixed KPI tables** (add `sNN_` to source + KPI table names in the SQL); leave them running |
| 5 | Enable **Tableflow** (Confluent storage, Iceberg) on their 4 KPI topics |
| 6 | Run/submit the **Spark bridge** writing to **their schema** `kpi_sNN` (see C), then query `iceberg_catalog.kpi_sNN.*` in Presto |
| 7 | In watsonx BI, create a connection (paste Presto JSON + API key), import `iceberg_catalog.kpi_sNN` tables, ask KPI questions |

Students always work inside **their prefix / their schema**, so 30 people share
the same cluster and catalog without stepping on each other.

---

## C. The Spark bridge — two delivery options (pick one)

The Spark bridge job needs several non-obvious configs. Choose based on
audience/time:

**Option 1 (recommended for beginners) — instructor pre-runs, students query.**
- You run the bridge for each student's KPI topics into their `kpi_sNN` schema
  (or run a single job that loops all prefixes) **before/at the start**.
- Students skip Step 6's submit and go straight to Presto + watsonx BI.
- Lowest failure surface; fits 90 minutes comfortably.

**Option 2 (advanced) — students submit the bridge themselves.**
- Give each student `kpi_to_native_iceberg.py` pre-filled with their prefix +
  `DEST_SCHEMA=kpi_sNN`, and the 4 Spark configs.
- They upload to COS and submit on the shared Spark engine.
- More faithful, but 30 concurrent Spark submits stress the engine and multiply
  the config-error surface.

> Whichever you choose, the **shared Spark + Presto engines** handle the load;
> just watch concurrency during the dry run.

---

## D. What is shared vs per-student (summary)

| Resource | Shared (once) | Per student |
|----------|---------------|-------------|
| Confluent environment, Kafka cluster, Flink pool, Schema Registry | ✅ | |
| Kafka topics | | ✅ `sNN_*` |
| Flink KPI statements/tables | | ✅ `sNN_kpi_*` |
| Tableflow enablement | | ✅ (on their topics) |
| Tableflow REST catalog + cluster-id namespace | ✅ (same for all) | |
| watsonx.data Spark + Presto engines | ✅ | |
| Iceberg catalog on COS | ✅ (one catalog) | ✅ schema `kpi_sNN` |
| watsonx BI connection + metrics/dashboard | | ✅ (their own) |
| API keys (cluster / SR / Tableflow), student IDs | | ✅ (issued per student) |

---

## E. Capacity & cost notes (shared account)

- **Flink**: ~30 × 4 = ~120 always-on statements. Size the compute pool; tell
  finished students to **stop their statements**.
- **watsonx.data engines**: shared Spark + Presto; watch concurrency. The Spark
  bridge is a short batch job — Option 1 (you run it) smooths the load.
- **Producer**: default ~4 events/sec each keeps Kafka/Flink light.
- Confirm the **Confluent promo** covers Flink + Tableflow; the two IBM Cloud
  accounts are funded separately (TechZone).

---

## F. Cleanup (end of session)

- Students: Ctrl+C producer; **stop their 4 Flink statements**; optionally drop
  their `kpi_sNN` schema and delete their `sNN_` topics.
- Instructor: stop/deprovision engines + Flink pool if temporary; revoke keys;
  tear down per cost policy.
