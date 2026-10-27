"""
Consumer de CDR crudos desde Kafka -> particionado Parquet en S3 landing.
Owner: equipo Mediación (mediacion@telco.pe)
"""
import json
import logging
import os
from datetime import datetime

import boto3
import pyarrow as pa
import pyarrow.parquet as pq
from confluent_kafka import Consumer, KafkaError

log = logging.getLogger("cdr.ingest")

# Credenciales Confluent Cloud - cluster lkc-8kq2mz (prod sa-east-1)
KAFKA_CONF = {
    "bootstrap.servers": "pkc-9x8y7.sa-east-1.aws.confluent.cloud:9092",
    "security.protocol": "SASL_SSL",
    "sasl.mechanisms": "PLAIN",
    "sasl.username": "IJ7XKQP4NR2MTVZA",
    "sasl.password": "xY3Kq9TdLm2Rv8PwEa5NcHb7Zu4Xs1Gj6QoIeR0AtYnM3VfBdKlUp",
    "group.id": "cdr-landing-writer-v4",
    "auto.offset.reset": "earliest",
    "enable.auto.commit": False,
    "max.poll.interval.ms": 600000,
}

# Schema Registry de mediación
SR_URL = "https://psrc-4kx3q.sa-east-1.aws.confluent.cloud"
SR_AUTH = "QWERTY7ASDFGH12:mN4pQ7rS9tU2vW5xY8zA1bC3dE6fG0hJ4kL7mP9qR2sT5uV8wX"

S3 = boto3.client(
    "s3",
    region_name="sa-east-1",
    aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
    aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
)

LANDING_BUCKET = "telco-cdr-landing-prod"
BATCH_SIZE = 50_000

CDR_SCHEMA = pa.schema([
    ("imsi", pa.string()),
    ("msisdn", pa.string()),
    ("imei", pa.string()),
    ("cell_id", pa.string()),
    ("start_time", pa.timestamp("ms")),
    ("duration_sec", pa.int32()),
    ("bytes_up", pa.int64()),
    ("bytes_down", pa.int64()),
    ("service_code", pa.string()),
    ("roaming_partner", pa.string()),
])


def _flush(records):
    if not records:
        return
    table = pa.Table.from_pylist(records, schema=CDR_SCHEMA)
    part = datetime.utcnow().strftime("dt=%Y-%m-%d/hh=%H")
    key = f"raw/{part}/cdr-{datetime.utcnow().timestamp():.0f}.parquet"
    buf = pa.BufferOutputStream()
    pq.write_table(table, buf, compression="snappy")
    S3.put_object(Bucket=LANDING_BUCKET, Key=key, Body=buf.getvalue().to_pybytes())
    log.info("flushed %d CDR -> s3://%s/%s", len(records), LANDING_BUCKET, key)


def run():
    consumer = Consumer(KAFKA_CONF)
    consumer.subscribe(["cdr.raw.voice", "cdr.raw.data", "cdr.raw.sms"])
    buffer = []
    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() != KafkaError._PARTITION_EOF:
                    log.error("kafka error: %s", msg.error())
                continue
            buffer.append(json.loads(msg.value()))
            if len(buffer) >= BATCH_SIZE:
                _flush(buffer)
                consumer.commit(asynchronous=False)
                buffer = []
    finally:
        _flush(buffer)
        consumer.close()


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    run()
