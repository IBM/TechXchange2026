#!/usr/bin/env python3
"""
Lab-2950 - Per-student artifact generator
==========================================
Generates prefixed, ready-to-run lab files for each student in a shared
Confluent + watsonx.data environment, so ~30 students don't collide.

For each student number NN it creates  students/sNN/  containing:
  - client.properties            (Confluent connection; fill secrets or pass via env)
  - flink/*.sql                  (KPI SQL with every table/topic prefixed sNN_)
  - kpi_to_native_iceberg.py     (Spark bridge writing to schema kpi_sNN)
  - README.txt                   (what this student runs, in order)

USAGE
  # generate s01..s30 with placeholder secrets:
  python tools/generate_student_files.py --count 30

  # generate a range:
  python tools/generate_student_files.py --start 1 --end 30

  # bake in the shared (non-secret) Confluent/Tableflow values so students only
  # add their own API keys:
  python tools/generate_student_files.py --count 30 \
      --bootstrap pkc-xxxxx.us-east-2.aws.confluent.cloud:9092 \
      --sr-url https://psrc-xxxxx.us-east-2.aws.confluent.cloud \
      --tf-region us-east-2 --tf-org <ORG_ID> --tf-env env-xxxxx \
      --cluster-id lkc-xxxxx --dest-catalog iceberg_catalog \
      --dest-bucket <YOUR_COS_BUCKET>

Notes
  - Secrets (API keys) are NOT required to generate; leave them as placeholders
    and have each student paste their own. If you pass them, the output folder
    will contain secrets - do NOT commit students/ to Git (it's git-ignored).
  - Run from the repo root (Lab-development/).
"""
import argparse
import os
import re
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent   # Lab-development/
FLINK_SRC = REPO / "flink"
OUT_ROOT = REPO / "students"

# Identifiers in the Flink SQL that must be prefixed per student.
# Source topics + the intermediate view + the 4 KPI output tables.
PREFIXABLE = [
    "orders", "payments", "customers", "shipments", "refunds",
    "sales_events",
    "kpi_revenue_per_minute", "kpi_order_throughput",
    "kpi_payment_failure_rate", "kpi_regional_sales_trends",
]

# Flink SQL files to prefix (skip the 04b fallback by default; include if asked)
FLINK_FILES = [
    "00_inspect_source_topics.sql",
    "01_kpi_revenue_per_minute.sql",
    "02_kpi_order_throughput.sql",
    "03_kpi_payment_failure_rate.sql",
    "04_kpi_regional_sales_trends.sql",
]


def prefix_sql(text: str, prefix: str) -> str:
    """Add `prefix` before each known identifier, respecting word boundaries.

    We only prefix identifiers in SQL code lines, not in `--` comment lines
    (prefixing comment prose looks confusing). Identifiers are sorted
    longest-first, and a negative lookbehind avoids double-prefixing.
    """
    compiled = [
        re.compile(rf"(?<![\w]){re.escape(ident)}(?![\w])")
        for ident in sorted(PREFIXABLE, key=len, reverse=True)
    ]

    def apply(segment: str) -> str:
        for pat, ident in zip(compiled, sorted(PREFIXABLE, key=len, reverse=True)):
            segment = pat.sub(prefix + ident, segment)
        return segment

    out_lines = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("--"):
            out_lines.append(line)                 # leave comments untouched
        elif "--" in line:                          # code + trailing comment
            code, _, comment = line.partition("--")
            out_lines.append(apply(code) + "--" + comment)
        else:
            out_lines.append(apply(line))
    return "\n".join(out_lines) + ("\n" if text.endswith("\n") else "")


CLIENT_PROPERTIES_TMPL = """# Confluent Cloud connection - Student {sid}
# Fill in your API keys (from your instructor slip). Topic prefix is {prefix}.
bootstrap.servers={bootstrap}
security.protocol=SASL_SSL
sasl.mechanisms=PLAIN
sasl.username={cluster_key}
sasl.password={cluster_secret}

schema.registry.url={sr_url}
schema.registry.basic.auth.user.info={sr_key}:{sr_secret}

acks=all
linger.ms=50
client.id=kpi-copilot-{sid}
"""

README_TMPL = """Student {sid}  (prefix: {prefix}, watsonx.data schema: kpi_{sid})
================================================================

Run these in order. Everything you create is namespaced to you, so you won't
collide with other students in the shared environment.

1. TOPICS (Confluent Cloud):
   Create 5 topics: {prefix}orders, {prefix}payments, {prefix}customers,
   {prefix}shipments, {prefix}refunds  (Partitions=1, skip schema prompt).

2. PRODUCER (your laptop, from the repo root):
   - Put this folder's client.properties into config/client.properties
     (fill your API keys first), OR pass values via env.
   - pip install -r producer/requirements.txt
   - TOPIC_PREFIX={prefix} python producer/event_generator.py

3. FLINK (Confluent Cloud > Flink SQL workspace):
   Run the SQL files in flink/ here, one statement at a time. They are already
   prefixed with {prefix}. For 04_kpi_regional_sales_trends.sql run the
   CREATE VIEW first, then the CREATE TABLE AS. Leave all statements running.

4. TABLEFLOW (Confluent Cloud):
   Enable Tableflow (Iceberg, Use Confluent storage) on your 4 KPI topics:
   {prefix}kpi_revenue_per_minute, {prefix}kpi_order_throughput,
   {prefix}kpi_payment_failure_rate, {prefix}kpi_regional_sales_trends.

5. SPARK BRIDGE (watsonx.data) - if your instructor asks you to run it:
   Upload kpi_to_native_iceberg.py here to COS and submit on the Spark engine
   with these Spark configuration properties:
     spark.hadoop.wxd.apiKey = Basic <base64 of ibmlhapikey_<userid>:<apikey>>
     spark.hadoop.fs.s3a.endpoint.region = <REGION>
     spark.gluten.sql.columnar.batchscan = false
     spark.gluten.sql.columnar.filescan  = false
   It writes to schema kpi_{sid}.

6. PRESTO (watsonx.data SQL workspace):
   SHOW TABLES IN {dest_catalog}.kpi_{sid};
   SELECT * FROM {dest_catalog}.kpi_{sid}.{prefix}kpi_revenue_per_minute
   ORDER BY window_start DESC LIMIT 20;

7. watsonx BI:
   New connection > IBM watsonx.data Presto > paste the Presto JSON + your API
   key. Import {dest_catalog}.kpi_{sid} tables and ask KPI questions.
"""


def gen_bridge(prefix: str, sid: str, args) -> str:
    """Produce a bridge job filled with this student's prefix + schema."""
    # KPI table -> business columns (must match the Flink KPI schemas)
    kpi_cols = {
        "kpi_revenue_per_minute":
            ["window_start", "window_end", "region", "successful_payments", "revenue_usd"],
        "kpi_order_throughput":
            ["window_start", "window_end", "region", "order_count",
             "gross_order_value_usd", "avg_order_value_usd"],
        "kpi_payment_failure_rate":
            ["window_start", "window_end", "region", "total_payments",
             "failed_payments", "failure_rate_pct"],
        "kpi_regional_sales_trends":
            ["window_start", "window_end", "region", "orders_paid",
             "unique_customers", "revenue_usd", "refund_count", "refund_usd",
             "net_revenue_usd"],
    }
    tables_py = "{\n"
    for t, cols in kpi_cols.items():
        col_repr = ", ".join(f'"{c}"' for c in cols)
        tables_py += f'    "{prefix}{t}": [{col_repr}],\n'
    tables_py += "}"

    return f'''"""
Spark bridge for student {sid} (prefix {prefix}) - writes to schema kpi_{sid}.
Reads the student's prefixed Tableflow KPI topics and writes native Iceberg
tables into {args.dest_catalog}.kpi_{sid} on IBM COS (for Presto + watsonx BI).

Submit on the watsonx.data Spark engine with these Spark configuration props:
  spark.hadoop.wxd.apiKey            = Basic <base64 of ibmlhapikey_<userid>:<apikey>>
  spark.hadoop.fs.s3a.endpoint.region= {args.tf_region}
  spark.gluten.sql.columnar.batchscan= false
  spark.gluten.sql.columnar.filescan = false
"""
from pyspark.sql import SparkSession

REGION           = "{args.tf_region}"
ORG_ID           = "{args.tf_org}"
ENV_ID           = "{args.tf_env}"
TABLEFLOW_APIKEY = "{args.tf_key}"
TABLEFLOW_SECRET = "{args.tf_secret}"
CLUSTER_ID       = "{args.cluster_id}"          # Kafka cluster id = Iceberg namespace

DEST_CATALOG = "{args.dest_catalog}"
DEST_SCHEMA  = "kpi_{sid}"
DEST_BUCKET  = "{args.dest_bucket}"

TABLES = {tables_py}

REST_URI = (f"https://tableflow.{{REGION}}.aws.confluent.cloud/iceberg/catalog/"
            f"organizations/{{ORG_ID}}/environments/{{ENV_ID}}")

spark = (SparkSession.builder.appName("bridge-{sid}")
    .enableHiveSupport()
    .config("spark.sql.catalog.tableflow", "org.apache.iceberg.spark.SparkCatalog")
    .config("spark.sql.catalog.tableflow.type", "rest")
    .config("spark.sql.catalog.tableflow.uri", REST_URI)
    .config("spark.sql.catalog.tableflow.credential", f"{{TABLEFLOW_APIKEY}}:{{TABLEFLOW_SECRET}}")
    .config("spark.sql.catalog.tableflow.io-impl", "org.apache.iceberg.aws.s3.S3FileIO")
    .config("spark.sql.catalog.tableflow.rest-metrics-reporting-enabled", "false")
    .config("spark.sql.catalog.tableflow.s3.remote-signing-enabled", "true")
    .config("spark.sql.catalog.tableflow.client.region", REGION)
    .config("spark.sql.catalog.tableflow.s3.region", REGION)
    .config("spark.hadoop.fs.s3a.endpoint.region", REGION)
    .config("spark.hadoop.fs.s3a.endpoint", f"s3.{{REGION}}.amazonaws.com")
    .config("spark.gluten.sql.columnar.batchscan", "false")
    .config("spark.gluten.sql.columnar.filescan", "false")
    .getOrCreate())

spark.sql(f"CREATE DATABASE IF NOT EXISTS {{DEST_CATALOG}}.{{DEST_SCHEMA}} "
          f"LOCATION 's3a://{{DEST_BUCKET}}/{{DEST_SCHEMA}}/'")

for table, cols in TABLES.items():
    src = f"tableflow.`{{CLUSTER_ID}}`.{{table}}"
    dst = f"{{DEST_CATALOG}}.{{DEST_SCHEMA}}.{{table}}"
    df = spark.sql(f"SELECT {{', '.join(cols)}} FROM {{src}}")
    df.writeTo(dst).using("iceberg").createOrReplace()
    print(f"wrote {{spark.table(dst).count()}} rows -> {{dst}}")

spark.stop()
'''


def main():
    ap = argparse.ArgumentParser(description="Generate per-student lab files.")
    ap.add_argument("--count", type=int, help="number of students (s01..sNN)")
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--end", type=int)
    ap.add_argument("--bootstrap", default="<BOOTSTRAP_SERVER>:9092")
    ap.add_argument("--sr-url", default="<SCHEMA_REGISTRY_URL>")
    ap.add_argument("--tf-region", default="<REGION>")
    ap.add_argument("--tf-org", default="<ORG_ID>")
    ap.add_argument("--tf-env", default="<ENV_ID>")
    ap.add_argument("--cluster-id", default="<lkc-xxxxx>")
    ap.add_argument("--dest-catalog", default="iceberg_catalog")
    ap.add_argument("--dest-bucket", default="<YOUR_COS_BUCKET>")
    # secrets (optional; left as placeholders by default)
    ap.add_argument("--tf-key", default="<TF_KEY>")
    ap.add_argument("--tf-secret", default="<TF_SECRET>")
    args = ap.parse_args()

    if args.count:
        start, end = 1, args.count
    elif args.end:
        start, end = args.start, args.end
    else:
        ap.error("provide --count N (or --start/--end)")

    if OUT_ROOT.exists():
        print(f"Note: {OUT_ROOT} exists; files will be overwritten.")
    OUT_ROOT.mkdir(exist_ok=True)

    for n in range(start, end + 1):
        sid = f"s{n:02d}"
        prefix = f"{sid}_"
        sdir = OUT_ROOT / sid
        (sdir / "flink").mkdir(parents=True, exist_ok=True)

        # client.properties
        (sdir / "client.properties").write_text(CLIENT_PROPERTIES_TMPL.format(
            sid=sid, prefix=prefix, bootstrap=args.bootstrap,
            cluster_key="<CLUSTER_API_KEY>", cluster_secret="<CLUSTER_API_SECRET>",
            sr_url=args.sr_url, sr_key="<SR_KEY>", sr_secret="<SR_SECRET>"))

        # prefixed flink SQL
        for fname in FLINK_FILES:
            src = (FLINK_SRC / fname).read_text()
            (sdir / "flink" / fname).write_text(prefix_sql(src, prefix))

        # bridge job
        (sdir / "kpi_to_native_iceberg.py").write_text(gen_bridge(prefix, sid, args))

        # readme
        (sdir / "README.txt").write_text(README_TMPL.format(
            sid=sid, prefix=prefix, dest_catalog=args.dest_catalog))

    total = end - start + 1
    print(f"Generated {total} student folder(s) under {OUT_ROOT}")
    print("Reminder: students/ is git-ignored; do not commit generated secrets.")


if __name__ == "__main__":
    main()
