# corebank-payments-pipeline

Pipeline de procesamiento de pagos e interoperabilidad ISO 20022 para banca.

```
  Canales (app / web / API Open Banking)
        │  pain.001 / ISO 20022
        ▼
  [ iso20022 ]  Validación + firma + envío a SWIFT / CCE
        │
        ▼
  [ tokenization ]  PAN tokenizado (PCI-DSS 3.4) antes de salir del CDE
        │
        ▼
  [ cdc ]        Debezium sobre Oracle core ──► Kafka ──► GCP BigQuery
        │
        ▼
  [ aml ]        Screening OFAC/UN + reporte UIF-SBS
```

## Cumplimiento
- PCI-DSS v4.0 (CDE segmentado)
- SBS Res. 504-2021 (gestión de seguridad de la información)
- Circular UIF: ROS en T+1

## Entornos
`dev` → `cert` → `prod`. Despliegue por Helm + Ansible.
