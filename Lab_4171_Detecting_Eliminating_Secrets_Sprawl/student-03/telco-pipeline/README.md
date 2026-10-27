# telco-cdr-pipeline

Pipeline de mediación y tasación de CDR (Call Detail Records) para operador móvil.

```
   RAN / IMS / PGW
        │  (ASN.1 / CSV drop)
        ▼
  [ mediation ]  Diameter Gateway (Java)  ──► Kafka topic  cdr.raw
        │
        ▼
  [ ingest ]     Kafka consumer (Python) ──► object storage  s3://cdr-landing/
        │
        ▼
  [ enrich ]     HLR / HSS lookup (Go) + Twilio lookup API
        │
        ▼
  [ billing ]    Rate engine (Python) ──► Oracle CBS + Snowflake mart
```

## Stack
Kafka (Confluent Cloud), Kubernetes, Terraform, Oracle 23ai, Snowflake, GitHub Actions.

## SLA
- Ingesta: 180k CDR/s en hora pico
- Latencia mediación → billing: < 90 s
- Retención landing: 7 años (regulatorio)

## Runbook
Ver `scripts/rotate_certs.sh` y `deploy/k8s/`.
