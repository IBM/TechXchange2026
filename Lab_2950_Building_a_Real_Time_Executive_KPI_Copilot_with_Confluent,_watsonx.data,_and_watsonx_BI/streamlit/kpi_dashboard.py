#!/usr/bin/env python3
"""
Real-Time Executive KPI Copilot - LIVE Streamlit dashboard (side track)
=======================================================================
IBM TechXchange 2026 - Lab-2950

A live operations screen that reads the four KPI Kafka topics directly from
Confluent Cloud and updates on a timer. This is the "real-time" complement to
the watsonx BI reports:

  - watsonx BI  -> governed reports + natural-language Copilot over a SNAPSHOT
                   of the KPIs (native Iceberg tables, refreshed by the Spark
                   bridge).
  - THIS app    -> a live, always-moving view straight off the Kafka KPI topics
                   (kpi_revenue_per_minute, kpi_order_throughput,
                   kpi_payment_failure_rate, kpi_regional_sales_trends).

HOW IT WORKS
  - A single background thread consumes the 4 KPI topics (from earliest, then
    tails live) and keeps a rolling in-memory store. The Streamlit page
    auto-refreshes every few seconds and just re-renders that store - it does
    NOT re-consume Kafka on every refresh, so Kafka usage stays ~= the
    producer's tiny volume regardless of refresh rate.

RUN
    pip install -r streamlit/requirements.txt
    # uses the SAME config/client.properties as the producer
    streamlit run streamlit/kpi_dashboard.py
    # with a per-student prefix:
    TOPIC_PREFIX=s07_ streamlit run streamlit/kpi_dashboard.py
"""
import json
import os
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st
from confluent_kafka import Consumer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.json_schema import JSONDeserializer
from confluent_kafka.serialization import MessageField, SerializationContext

try:
    from confluent_kafka.schema_registry.avro import AvroDeserializer
    _HAVE_AVRO = True
except Exception:
    _HAVE_AVRO = False

try:
    from streamlit_autorefresh import st_autorefresh
    _HAVE_AUTOREFRESH = True
except Exception:
    _HAVE_AUTOREFRESH = False

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
CONFIG_PATH = Path(os.environ.get(
    "KAFKA_CONFIG",
    Path(__file__).resolve().parent.parent / "config" / "client.properties",
))
TOPIC_PREFIX = os.environ.get("TOPIC_PREFIX", "")
REFRESH_SECONDS = int(os.environ.get("REFRESH_SECONDS", "5"))
MAX_ROWS_PER_TOPIC = 5000     # rolling in-memory cap per KPI topic

TOPICS = {
    "revenue":  f"{TOPIC_PREFIX}kpi_revenue_per_minute",
    "throughput": f"{TOPIC_PREFIX}kpi_order_throughput",
    "failure":  f"{TOPIC_PREFIX}kpi_payment_failure_rate",
    "regional": f"{TOPIC_PREFIX}kpi_regional_sales_trends",
}


def load_props(path: Path) -> dict:
    conf = {}
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            conf[k.strip()] = v.strip()
    return conf


# Producer-only keys in client.properties that a Consumer must NOT receive
# (they cause the Consumer to fail to construct -> silent "Waiting for data").
_PRODUCER_ONLY = {"acks", "linger.ms", "client.id", "compression.type",
                  "batch.size", "enable.idempotence", "retries",
                  "delivery.timeout.ms", "max.in.flight.requests.per.connection"}

# Keys the Consumer accepts from the properties file.
_CONSUMER_KEYS = {"bootstrap.servers", "security.protocol", "sasl.mechanisms",
                  "sasl.mechanism", "sasl.username", "sasl.password",
                  "ssl.endpoint.identification.algorithm"}


def split_conf(conf: dict):
    sr, kafka = {}, {}
    for k, v in conf.items():
        if k == "schema.registry.url":
            sr["url"] = v
        elif k == "schema.registry.basic.auth.user.info":
            sr["basic.auth.user.info"] = v
        elif k in _PRODUCER_ONLY:
            continue  # drop producer-only settings for the consumer
        elif k in _CONSUMER_KEYS:
            kafka[k] = v
        # anything else is ignored to keep the consumer config clean
    return kafka, sr


# ---------------------------------------------------------------------------
# Background consumer (started once, shared across Streamlit reruns)
# ---------------------------------------------------------------------------
# We stash the store + thread on st.session_state so a rerun reuses them.

def _make_store():
    store = {name: deque(maxlen=MAX_ROWS_PER_TOPIC) for name in TOPICS}
    store["_status"] = {"state": "starting", "error": None, "consumed": 0,
                        "last_topic": None}
    return store


def _consumer_loop(store, stop_flag, kafka_conf, sr_conf):
    status = store["_status"]
    try:
        consumer_conf = dict(kafka_conf)
        consumer_conf["group.id"] = f"kpi-dashboard-{int(time.time())}"
        consumer_conf["auto.offset.reset"] = "earliest"
        consumer_conf["enable.auto.commit"] = "false"
        consumer = Consumer(consumer_conf)
        consumer.subscribe(list(TOPICS.values()))
    except Exception as e:  # construction/subscribe failure -> surface it
        status["state"] = "error"
        status["error"] = f"Consumer init failed: {e!r}"
        return

    sr_client = SchemaRegistryClient(sr_conf) if sr_conf.get("url") else None
    # Flink/Tableflow write the KPI topics as AVRO (Schema Registry). The
    # producer's source topics were JSON. Build both and try Avro first, then
    # JSON, then raw JSON - so the dashboard works regardless of format.
    avro_deser = AvroDeserializer(schema_registry_client=sr_client) \
        if (sr_client and _HAVE_AVRO) else None
    json_deser = JSONDeserializer(schema_str=None, schema_registry_client=sr_client) \
        if sr_client else None
    topic_to_name = {v: k for k, v in TOPICS.items()}
    status["state"] = "running"

    while not stop_flag["stop"]:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            status["error"] = f"Kafka: {msg.error()}"
            continue
        topic = msg.topic()
        name = topic_to_name.get(topic)
        if not name:
            continue
        value = None
        raw = msg.value()
        ctx = SerializationContext(topic, MessageField.VALUE)
        # 1) Avro (what Flink writes)
        if value is None and avro_deser is not None:
            try:
                value = avro_deser(raw, ctx)
            except Exception:
                value = None
        # 2) JSON Schema
        if value is None and json_deser is not None:
            try:
                value = json_deser(raw, ctx)
            except Exception:
                value = None
        # 3) plain / header-stripped JSON
        if value is None:
            for attempt in (raw, raw[5:] if raw and len(raw) > 5 else None):
                if attempt is None:
                    continue
                try:
                    value = json.loads(attempt)
                    break
                except Exception:
                    continue
        if isinstance(value, dict):
            store[name].append(value)
            status["consumed"] += 1
            status["last_topic"] = topic
            status["error"] = None
        else:
            status["error"] = "could not decode message (tried Avro/JSON)"
    consumer.close()


def ensure_consumer():
    if "kpi_store" in st.session_state:
        return st.session_state["kpi_store"]
    conf = load_props(CONFIG_PATH)
    kafka_conf, sr_conf = split_conf(conf)
    store = _make_store()
    stop_flag = {"stop": False}
    t = threading.Thread(
        target=_consumer_loop,
        args=(store, stop_flag, kafka_conf, sr_conf),
        daemon=True,
    )
    t.start()
    st.session_state["kpi_store"] = store
    st.session_state["kpi_stop"] = stop_flag
    st.session_state["kpi_thread"] = t
    return store


def df_of(store, name, ts_col):
    rows = list(store[name])
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    if ts_col in df.columns:
        df[ts_col] = pd.to_datetime(df[ts_col], errors="coerce")
        df = df.sort_values(ts_col)
    return df


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
def main():
    st.set_page_config(page_title="Real-Time KPI Copilot (Live)",
                       page_icon="📈", layout="wide")

    if not CONFIG_PATH.exists():
        st.error(f"Config not found at {CONFIG_PATH}. Copy "
                 f"config/client.properties.example to config/client.properties "
                 f"and fill in your Confluent details.")
        st.stop()

    store = ensure_consumer()

    if _HAVE_AUTOREFRESH:
        st_autorefresh(interval=REFRESH_SECONDS * 1000, key="kpi_refresh")

    st.title("📈 Real-Time Executive KPI Copilot — Live")
    st.caption(
        f"Live from Confluent KPI topics"
        f"{' (prefix ' + TOPIC_PREFIX + ')' if TOPIC_PREFIX else ''} · "
        f"auto-refresh every {REFRESH_SECONDS}s · "
        f"updated {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC"
    )

    # Consumer status banner (helps diagnose "Waiting for data").
    status = store.get("_status", {})
    if status.get("state") == "error":
        st.error(f"Consumer error: {status.get('error')}")
    else:
        st.caption(
            f"consumer: {status.get('state','?')} · "
            f"messages consumed: {status.get('consumed',0)} · "
            f"last topic: {status.get('last_topic') or '—'}"
            + (f" · note: {status.get('error')}" if status.get('error') else "")
        )
        st.caption("Topics: " + ", ".join(TOPICS.values()))
    if not _HAVE_AUTOREFRESH:
        st.info("Install streamlit-autorefresh for automatic updates, or use "
                "the Rerun button / browser refresh.")

    rev = df_of(store, "revenue", "window_start")
    thr = df_of(store, "throughput", "window_start")
    fail = df_of(store, "failure", "window_start")
    reg = df_of(store, "regional", "window_start")

    # How many recent minutes to display (keeps the charts compact).
    win = st.sidebar.slider("Minutes to display", 5, 120, 30, step=5)
    chart_h = 260  # fixed chart height so the page doesn't stretch

    def dedup(df):
        """De-duplicate to the latest value per (window_start, region) -
        INSERT INTO can re-emit a window multiple times as it updates."""
        if df.empty or "window_start" not in df.columns:
            return df
        keys = [c for c in ("window_start", "region") if c in df.columns]
        return df.drop_duplicates(subset=keys, keep="last") if keys else df

    def recent(df):
        """dedup + keep only rows within the display window."""
        df = dedup(df)
        if df.empty or "window_start" not in df.columns:
            return df
        cutoff = df["window_start"].max() - pd.Timedelta(minutes=win)
        return df[df["window_start"] >= cutoff]

    # Full (deduped) frames for cumulative "since inception" totals.
    rev_all, thr_all, fail_all, reg_all = dedup(rev), dedup(thr), dedup(fail), dedup(reg)
    # Windowed frames for the charts + latest-window metrics.
    rev, thr, fail, reg = recent(rev), recent(thr), recent(fail), recent(reg)

    # --- Since-inception (cumulative) metrics ---
    st.markdown("**Since inception** (all data consumed this session)")
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("Total revenue",
              f"${rev_all['revenue_usd'].sum():,.0f}" if not rev_all.empty else "—")
    t2.metric("Total orders",
              f"{int(thr_all['order_count'].sum()):,}" if not thr_all.empty else "—")
    t3.metric("Overall payment failure %",
              (f"{100.0 * fail_all['failed_payments'].sum() / fail_all['total_payments'].sum():.1f}%"
               if (not fail_all.empty and fail_all['total_payments'].sum() > 0) else "—"))
    t4.metric("Total net revenue",
              f"${reg_all['net_revenue_usd'].sum():,.0f}" if not reg_all.empty else "—")

    # --- Latest-window metrics ---
    st.markdown("**Latest window**")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Revenue (latest min, all regions)",
              f"${rev.groupby('window_start')['revenue_usd'].sum().iloc[-1]:,.0f}"
              if not rev.empty else "—")
    c2.metric("Orders (latest min)",
              f"{int(thr.groupby('window_start')['order_count'].sum().iloc[-1])}"
              if not thr.empty else "—")
    c3.metric("Payment failure % (latest min)",
              f"{fail.groupby('window_start')['failure_rate_pct'].mean().iloc[-1]:.1f}%"
              if not fail.empty else "—")
    c4.metric("Net revenue (latest 5-min, all regions)",
              f"${reg.groupby('window_start')['net_revenue_usd'].sum().iloc[-1]:,.0f}"
              if not reg.empty else "—")

    st.divider()

    # --- charts ---
    left, right = st.columns(2)
    with left:
        st.subheader("Revenue per minute")
        if not rev.empty:
            pivot = rev.pivot_table(index="window_start", columns="region",
                                    values="revenue_usd", aggfunc="sum").fillna(0)
            st.line_chart(pivot, height=chart_h)
        else:
            st.write("Waiting for data…")

        st.subheader("Payment failure rate (%)")
        if not fail.empty:
            fpivot = fail.pivot_table(index="window_start", columns="region",
                                      values="failure_rate_pct", aggfunc="mean")
            st.line_chart(fpivot, height=chart_h)
        else:
            st.write("Waiting for data…")

    with right:
        st.subheader("Orders per minute")
        if not thr.empty:
            tpivot = thr.pivot_table(index="window_start", columns="region",
                                     values="order_count", aggfunc="sum").fillna(0)
            st.line_chart(tpivot, height=chart_h)
        else:
            st.write("Waiting for data…")

        st.subheader("Net revenue by region (latest 5-min window)")
        if not reg.empty:
            latest = reg[reg["window_start"] == reg["window_start"].max()]
            st.bar_chart(latest.set_index("region")["net_revenue_usd"],
                         height=chart_h)
        else:
            st.write("Waiting for data…")

    with st.expander("Latest revenue rows"):
        st.dataframe(rev.tail(20), use_container_width=True)


if __name__ == "__main__":
    main()
