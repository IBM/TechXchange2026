#!/usr/bin/env python3
"""
Real-Time Executive KPI Copilot - Event Generator
==================================================
IBM TechXchange 2026 - Lab-2950

This script simulates a live e-commerce business and streams five kinds of
business events into Confluent Cloud (Apache Kafka) topics:

    orders     -> a customer places an order
    payments   -> the order is paid for (may succeed or fail)
    customers  -> a new customer signs up
    shipments  -> a paid order gets shipped
    refunds    -> a customer requests a refund on an order

The events are CORRELATED so that downstream KPIs make sense:
    - A payment always references a real order_id and its amount.
    - A shipment always references a paid order.
    - A refund always references a real order.

You do NOT need to understand every line. In the lab you simply run:

    python event_generator.py

...and watch events flow into Kafka.

Prerequisites:
    pip install -r requirements.txt
    Copy  config/client.properties.example  ->  config/client.properties
    and fill in your Confluent Cloud bootstrap server + API key/secret.
"""

import json
import os
import random
import signal
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from confluent_kafka import Producer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.json_schema import JSONSerializer
from confluent_kafka.serialization import (
    MessageField,
    SerializationContext,
    StringSerializer,
)

# ---------------------------------------------------------------------------
# 1. Configuration
# ---------------------------------------------------------------------------
# We read Confluent Cloud connection settings from a properties file so that
# no secrets are hard-coded in the script. See config/client.properties.example
# ---------------------------------------------------------------------------

DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent / "config" / "client.properties"
)

# How many events (roughly) to emit per second across all topics.
# 4/sec is plenty to make the KPIs move while keeping Kafka/Flink usage (and
# cost) low in a shared 30-person lab. Override with EVENTS_PER_SECOND if you
# want more dramatic movement during a demo.
EVENTS_PER_SECOND = float(os.environ.get("EVENTS_PER_SECOND", "4"))

# Optional per-student prefix so many participants can share ONE Kafka cluster
# without topic-name collisions. Set TOPIC_PREFIX to match the topics you
# created in Confluent Cloud, e.g.:  TOPIC_PREFIX=s07_ python event_generator.py
# Leave empty ("") if each student has their own cluster (plain topic names).
TOPIC_PREFIX = os.environ.get("TOPIC_PREFIX", "")

# Topic names. These must match the topics you create in Confluent Cloud.
TOPIC_ORDERS = f"{TOPIC_PREFIX}orders"
TOPIC_PAYMENTS = f"{TOPIC_PREFIX}payments"
TOPIC_CUSTOMERS = f"{TOPIC_PREFIX}customers"
TOPIC_SHIPMENTS = f"{TOPIC_PREFIX}shipments"
TOPIC_REFUNDS = f"{TOPIC_PREFIX}refunds"

# Reference data used to make the simulated business feel realistic.
REGIONS = ["North America", "Europe", "Asia Pacific", "Latin America", "Middle East"]
PRODUCT_CATALOG = [
    ("SKU-1001", "Wireless Headphones", 79.99),
    ("SKU-1002", "Smart Watch", 199.99),
    ("SKU-1003", "Bluetooth Speaker", 49.99),
    ("SKU-1004", "Laptop Stand", 34.50),
    ("SKU-1005", "Mechanical Keyboard", 119.00),
    ("SKU-1006", "USB-C Hub", 42.25),
    ("SKU-1007", "4K Monitor", 349.99),
    ("SKU-1008", "Ergonomic Mouse", 59.95),
    ("SKU-1009", "Webcam 1080p", 89.00),
    ("SKU-1010", "Noise-Cancel Earbuds", 149.99),
]
PAYMENT_METHODS = ["credit_card", "debit_card", "paypal", "apple_pay", "bank_transfer"]

# Probabilities that control the "shape" of the business.
PAYMENT_FAILURE_RATE = 0.12   # ~12% of payments fail (drives payment-failure KPI)
REFUND_RATE = 0.05            # ~5% of paid orders eventually get refunded
NEW_CUSTOMER_RATE = 0.15      # 15% of events are new-customer signups


# ---------------------------------------------------------------------------
# 1b. JSON Schemas (one per event type / topic)
# ---------------------------------------------------------------------------
# We register a JSON Schema in Confluent Schema Registry for each topic. This
# is what lets Apache Flink (and Tableflow) see PROPER COLUMNS instead of raw
# bytes -- no manual "infer schema" clicking in the UI. Each schema lists the
# fields the corresponding event produces.
#
# Numbers use "type": "number" (maps to DOUBLE in Flink). Fields that can be
# null (e.g. a successful payment's failure_reason) allow ["string", "null"].
# ---------------------------------------------------------------------------

SCHEMA_ORDERS = json.dumps({
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "OrderEvent",
    "type": "object",
    "properties": {
        "event_type":   {"type": "string"},
        "order_id":     {"type": "string"},
        "customer_id":  {"type": "string"},
        "region":       {"type": "string"},
        "product_sku":  {"type": "string"},
        "product_name": {"type": "string"},
        "unit_price":   {"type": "number"},
        "quantity":     {"type": "number"},
        "amount":       {"type": "number"},
        "currency":     {"type": "string"},
        "order_ts":     {"type": "string"},
    },
})

SCHEMA_PAYMENTS = json.dumps({
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "PaymentEvent",
    "type": "object",
    "properties": {
        "event_type":     {"type": "string"},
        "payment_id":     {"type": "string"},
        "order_id":       {"type": "string"},
        "customer_id":    {"type": "string"},
        "region":         {"type": "string"},
        "amount":         {"type": "number"},
        "currency":       {"type": "string"},
        "payment_method": {"type": "string"},
        "status":         {"type": "string"},
        "failure_reason": {"type": ["string", "null"]},
        "payment_ts":     {"type": "string"},
    },
})

SCHEMA_CUSTOMERS = json.dumps({
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "CustomerEvent",
    "type": "object",
    "properties": {
        "event_type":     {"type": "string"},
        "customer_id":    {"type": "string"},
        "region":         {"type": "string"},
        "signup_channel": {"type": "string"},
        "created_at":     {"type": "string"},
    },
})

SCHEMA_SHIPMENTS = json.dumps({
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "ShipmentEvent",
    "type": "object",
    "properties": {
        "event_type":  {"type": "string"},
        "shipment_id": {"type": "string"},
        "order_id":    {"type": "string"},
        "customer_id": {"type": "string"},
        "region":      {"type": "string"},
        "carrier":     {"type": "string"},
        "status":      {"type": "string"},
        "shipped_ts":  {"type": "string"},
    },
})

SCHEMA_REFUNDS = json.dumps({
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "RefundEvent",
    "type": "object",
    "properties": {
        "event_type":  {"type": "string"},
        "refund_id":   {"type": "string"},
        "order_id":    {"type": "string"},
        "customer_id": {"type": "string"},
        "region":      {"type": "string"},
        "amount":      {"type": "number"},
        "currency":    {"type": "string"},
        "reason":      {"type": "string"},
        "refund_ts":   {"type": "string"},
    },
})

# Map each topic to its schema so we can build one serializer per topic.
TOPIC_SCHEMAS = {
    TOPIC_ORDERS:    SCHEMA_ORDERS,
    TOPIC_PAYMENTS:  SCHEMA_PAYMENTS,
    TOPIC_CUSTOMERS: SCHEMA_CUSTOMERS,
    TOPIC_SHIPMENTS: SCHEMA_SHIPMENTS,
    TOPIC_REFUNDS:   SCHEMA_REFUNDS,
}


# ---------------------------------------------------------------------------
# 2. In-memory state
# ---------------------------------------------------------------------------
# We keep small lists of recent customers and paid orders so later events can
# reference earlier ones (payments -> orders, refunds -> orders, etc.).
# ---------------------------------------------------------------------------

known_customers = []   # list of customer_id
paid_orders = []       # list of dicts: {order_id, customer_id, region, amount}
_running = True


def now_iso():
    """Return the current UTC time as an ISO-8601 string (KPI-friendly)."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# 3. Config loader
# ---------------------------------------------------------------------------

def load_producer_config(config_path: Path) -> dict:
    """Read a Java-style .properties file into a dict.

    Returns ALL keys found. In main() we split these into (a) Kafka producer
    settings and (b) Schema Registry settings (the keys that start with
    'schema.registry.').
    """
    if not config_path.exists():
        sys.exit(
            f"\nERROR: Config file not found at {config_path}\n"
            f"Copy config/client.properties.example to config/client.properties\n"
            f"and fill in your Confluent Cloud connection details.\n"
        )
    conf = {}
    with open(config_path, "r", encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            conf[key.strip()] = value.strip()
    return conf


def split_configs(conf: dict):
    """Separate Kafka producer config from Schema Registry config.

    Schema Registry keys in the properties file:
        schema.registry.url
        schema.registry.basic.auth.user.info   (format: SR_KEY:SR_SECRET)
    Everything else is treated as Kafka producer config.
    """
    sr_conf = {}
    kafka_conf = {}
    for key, value in conf.items():
        if key == "schema.registry.url":
            sr_conf["url"] = value
        elif key == "schema.registry.basic.auth.user.info":
            sr_conf["basic.auth.user.info"] = value
        else:
            kafka_conf[key] = value
    return kafka_conf, sr_conf


# ---------------------------------------------------------------------------
# 4. Event factories - each returns (topic, key, value_dict)
# ---------------------------------------------------------------------------

def make_customer_event():
    customer_id = f"CUST-{uuid.uuid4().hex[:8]}"
    known_customers.append(customer_id)
    # keep the list bounded so memory stays flat during long runs
    if len(known_customers) > 5000:
        del known_customers[: len(known_customers) - 5000]
    event = {
        "event_type": "customer_signup",
        "customer_id": customer_id,
        "region": random.choice(REGIONS),
        "signup_channel": random.choice(["web", "mobile_app", "partner", "referral"]),
        "created_at": now_iso(),
    }
    return TOPIC_CUSTOMERS, customer_id, event


def make_order_event():
    # If we have no customers yet, create one implicitly.
    if not known_customers:
        return make_customer_event()

    customer_id = random.choice(known_customers)
    sku, name, unit_price = random.choice(PRODUCT_CATALOG)
    quantity = random.randint(1, 4)
    amount = round(unit_price * quantity, 2)
    region = random.choice(REGIONS)
    order_id = f"ORD-{uuid.uuid4().hex[:10]}"

    event = {
        "event_type": "order_placed",
        "order_id": order_id,
        "customer_id": customer_id,
        "region": region,
        "product_sku": sku,
        "product_name": name,
        "unit_price": unit_price,
        "quantity": quantity,
        "amount": amount,
        "currency": "USD",
        "order_ts": now_iso(),
    }
    # Stash a lightweight version so a payment can reference it next.
    _pending_orders.append(
        {"order_id": order_id, "customer_id": customer_id, "region": region, "amount": amount}
    )
    if len(_pending_orders) > 2000:
        del _pending_orders[: len(_pending_orders) - 2000]
    return TOPIC_ORDERS, order_id, event


def make_payment_event():
    # A payment must reference an order we just placed.
    if not _pending_orders:
        return make_order_event()

    order = _pending_orders.pop(random.randrange(len(_pending_orders)))
    failed = random.random() < PAYMENT_FAILURE_RATE
    status = "failed" if failed else "success"
    event = {
        "event_type": "payment",
        "payment_id": f"PAY-{uuid.uuid4().hex[:10]}",
        "order_id": order["order_id"],
        "customer_id": order["customer_id"],
        "region": order["region"],
        "amount": order["amount"],
        "currency": "USD",
        "payment_method": random.choice(PAYMENT_METHODS),
        "status": status,
        "failure_reason": random.choice(
            ["insufficient_funds", "card_declined", "network_error", "fraud_hold"]
        )
        if failed
        else None,
        "payment_ts": now_iso(),
    }
    # Only successful payments become shippable / refundable orders.
    if not failed:
        paid_orders.append(order)
        if len(paid_orders) > 2000:
            del paid_orders[: len(paid_orders) - 2000]
    return TOPIC_PAYMENTS, order["order_id"], event


def make_shipment_event():
    if not paid_orders:
        return make_payment_event()
    order = random.choice(paid_orders)
    event = {
        "event_type": "shipment",
        "shipment_id": f"SHP-{uuid.uuid4().hex[:10]}",
        "order_id": order["order_id"],
        "customer_id": order["customer_id"],
        "region": order["region"],
        "carrier": random.choice(["UPS", "FedEx", "DHL", "USPS", "Local"]),
        "status": random.choice(["label_created", "in_transit", "delivered"]),
        "shipped_ts": now_iso(),
    }
    return TOPIC_SHIPMENTS, order["order_id"], event


def make_refund_event():
    if not paid_orders:
        return make_payment_event()
    order = random.choice(paid_orders)
    event = {
        "event_type": "refund",
        "refund_id": f"REF-{uuid.uuid4().hex[:10]}",
        "order_id": order["order_id"],
        "customer_id": order["customer_id"],
        "region": order["region"],
        "amount": order["amount"],
        "currency": "USD",
        "reason": random.choice(
            ["defective", "not_as_described", "changed_mind", "late_delivery"]
        ),
        "refund_ts": now_iso(),
    }
    return TOPIC_REFUNDS, order["order_id"], event


# Orders that have been placed but not yet paid.
_pending_orders = []


def pick_next_event():
    """Weighted random selection of which kind of event to emit next."""
    roll = random.random()
    if roll < NEW_CUSTOMER_RATE:
        return make_customer_event()
    # The remaining probability is split across the transactional events.
    # Orders are most common; payments follow orders; shipments/refunds are rarer.
    sub = random.random()
    if sub < 0.40:
        return make_order_event()
    elif sub < 0.75:
        return make_payment_event()
    elif sub < 0.90:
        return make_shipment_event()
    else:
        return make_refund_event()


# ---------------------------------------------------------------------------
# 5. Delivery callback + main loop
# ---------------------------------------------------------------------------

def delivery_report(err, msg):
    """Called once per message to confirm delivery (or report an error)."""
    if err is not None:
        sys.stderr.write(f"Delivery FAILED for {msg.topic()}: {err}\n")


def handle_sigint(signum, frame):
    global _running
    _running = False
    print("\nStopping event generator (flushing remaining messages)...")


def main():
    signal.signal(signal.SIGINT, handle_sigint)

    config_path = Path(os.environ.get("KAFKA_CONFIG", DEFAULT_CONFIG_PATH))
    conf = load_producer_config(config_path)
    kafka_conf, sr_conf = split_configs(conf)

    if "url" not in sr_conf:
        sys.exit(
            "\nERROR: Schema Registry is not configured.\n"
            "Add these two lines to config/client.properties:\n"
            "  schema.registry.url=https://psrc-xxxxx.region.provider.confluent.cloud\n"
            "  schema.registry.basic.auth.user.info=SR_KEY:SR_SECRET\n"
            "See config/client.properties.example for details.\n"
        )

    producer = Producer(kafka_conf)

    # One Schema Registry client, shared by all serializers.
    sr_client = SchemaRegistryClient(sr_conf)

    # Build one JSON serializer per topic. Registering these schemas is what
    # makes Flink see proper columns automatically (no UI inference needed).
    # to_dict is a passthrough because our events are already plain dicts.
    def _identity(obj, ctx):
        return obj

    value_serializers = {
        topic: JSONSerializer(schema_str, sr_client, _identity)
        for topic, schema_str in TOPIC_SCHEMAS.items()
    }
    key_serializer = StringSerializer("utf_8")

    print("=" * 70)
    print("  Real-Time Executive KPI Copilot - Event Generator")
    print("  IBM TechXchange 2026 - Lab-2950")
    print("=" * 70)
    print(f"  Bootstrap servers : {kafka_conf.get('bootstrap.servers', '(missing!)')}")
    print(f"  Schema Registry   : {sr_conf.get('url', '(missing!)')}")
    print(f"  Target rate       : ~{EVENTS_PER_SECOND} events/second")
    print(f"  Topic prefix      : {TOPIC_PREFIX or '(none)'}")
    print(f"  Topics            : {TOPIC_ORDERS}, {TOPIC_PAYMENTS}, "
          f"{TOPIC_CUSTOMERS}, {TOPIC_SHIPMENTS}, {TOPIC_REFUNDS}")
    print("  Registering schemas on first message per topic...")
    print("  Press Ctrl+C to stop.")
    print("=" * 70)

    interval = 1.0 / EVENTS_PER_SECOND if EVENTS_PER_SECOND > 0 else 0.1
    sent = 0
    counts = {t: 0 for t in
              (TOPIC_ORDERS, TOPIC_PAYMENTS, TOPIC_CUSTOMERS, TOPIC_SHIPMENTS, TOPIC_REFUNDS)}
    last_report = time.time()

    while _running:
        topic, key, value = pick_next_event()
        try:
            # Serialize the value against this topic's registered JSON Schema.
            ctx = SerializationContext(topic, MessageField.VALUE)
            value_bytes = value_serializers[topic](value, ctx)
            key_bytes = key_serializer(
                str(key), SerializationContext(topic, MessageField.KEY)
            )
            producer.produce(
                topic=topic,
                key=key_bytes,
                value=value_bytes,
                callback=delivery_report,
            )
            counts[topic] += 1
            sent += 1
        except BufferError:
            # Local queue is full; let librdkafka catch up.
            producer.poll(0.5)
            continue

        # Serve delivery callbacks without blocking.
        producer.poll(0)

        # Print a compact status line once per second.
        if time.time() - last_report >= 1.0:
            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] "
                f"sent={sent:>6}  "
                f"orders={counts[TOPIC_ORDERS]}  "
                f"payments={counts[TOPIC_PAYMENTS]}  "
                f"customers={counts[TOPIC_CUSTOMERS]}  "
                f"shipments={counts[TOPIC_SHIPMENTS]}  "
                f"refunds={counts[TOPIC_REFUNDS]}"
            )
            last_report = time.time()

        time.sleep(interval)

    print("Flushing...")
    producer.flush(10)
    print(f"Done. Total events sent: {sent}")


if __name__ == "__main__":
    main()
