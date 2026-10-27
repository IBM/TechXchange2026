# Demo guide — Vault Radar on telco and banking pipelines

Two synthetic repos that mimic real workloads from a mobile operator and a
bank, seeded with **high and critical severity** risks plus a volume of
**PII**, spread out the way it happens in real life: code, config, IaC, CI/CD,
manifests, notebooks, logs, SQL dumps, test fixtures and git history.

> Credentials and personal data are fictitious. Private keys are pairs
> generated on the fly, not used in any system. AWS values are the example
> values from AWS's public documentation, and the PANs pass Luhn but do not
> correspond to issued cards.

---

## 1. Important note on severity

Vault Radar derives severity from two things: **the risk type** and, when it
can verify it, **whether the secret is active**. The secrets in this demo are
fake, so Radar will flag them as inactive or with unknown status. That may
cause some findings to show up one level lower than you would see with real
credentials.

To compensate, the demo relies on risk types whose base severity is high on
its own, regardless of validation:

- Private keys (RSA, EC, OpenSSH) — detected by structure, not by validation
- GCP service accounts with an embedded `private_key`
- Vault unseal keys and root tokens
- Terraform state with plaintext secrets
- Kubeconfig with an admin token and `client-key-data`
- Card PAN with CVV and expiration date in the same record
- Identity documents, passports and SSNs alongside name and date of birth

If your demo needs to guarantee verifiable critical findings, the only honest
way is to use real credentials from a throwaway account and rotate them when
you're done. It's worth telling the customer exactly that: it's more credible
than forcing the result.

---

## 2. The two repos

| | `telco-cdr-pipeline` | `corebank-payments-pipeline` |
|---|---|---|
| Domain | CDR mediation and rating | ISO 20022 payments + core CDC |
| Languages | Python, Java, Go, HCL, YAML, SQL | Java, Python, TypeScript, SQL, YAML |
| Pipeline | Kafka → S3 → Oracle CBS → Snowflake | Oracle → Debezium → Kafka → BigQuery |
| Regulation | OSIPTEL, Law 29733, 7-year retention | PCI-DSS v4.0, SBS 504-2021, UIF |
| Commits | 9 (two with secrets deleted from the tip) | 9 (two with secrets deleted from the tip) |
| PII records | 140 subscribers + 80 log lines | 160 KYC customers + 90 transactions + 75 log lines |

---

## 3. High and critical severity risks

### telco-cdr-pipeline

| Location | Risk |
|---|---|
| `deploy/gcp/bigquery-sa.json` | GCP service account with a **full RSA private key** |
| `deploy/terraform/terraform.tfstate` | State with RDS password, Confluent API key, Snowflake password and **IAM access key pair** in plaintext |
| `.ssh/id_rsa_ci` | RSA private key for the CI user |
| `config/ocs-client-mtls.key` | RSA private key for the mTLS client against the OCS |
| `config/kubeconfig-prod.yaml` | EKS ServiceAccount token with access to the production namespace |
| `.aws/credentials` | Three profiles with access keys, including a *breakglass* one with a session token |
| `.pgpass`, `.npmrc`, `.pypirc` | PostgreSQL passwords, npm and Nexus tokens |
| `scripts/rotate_certs.sh` | RSA private key embedded in the heredoc |
| `.env` | Confluent key/secret, AWS keys, Twilio SID+token, DSN with password, Slack webhook |
| `src/**` | SASL password, LDAP bind, keystore, HSS API key, fraud JWT, Snowflake password |
| `deploy/k8s/cdr-consumer.yaml` | `stringData` with four secrets, AWS keys in `env`, Grafana API key in a ConfigMap |
| `.github/workflows/deploy.yml` | GitHub PAT, Nexus token, registry password, AWS keys |
| **Git history** | `config/hotfix_ocs.py` (Vault token, OCS password) and `tmp/breakglass.env` + `tmp/ocs-root-ca.key` (**Vault root token and CA private key**) |

### corebank-payments-pipeline

| Location | Risk |
|---|---|
| `certs/swift-lau-signing.key` | SWIFT signing RSA private key |
| `certs/jwt-es256-signing.key` | EC private key for token signing |
| `certs/payments-client-key.pem` | RSA private key for the mTLS client |
| `deploy/ansible/files/id_ed25519_deploy` | **OpenSSH private key** for the deployment user |
| `config/gcp/datalake-sa.json` | GCP service account with private key |
| `config/kubeconfig-prod.yaml` | Cluster admin token + `client-key-data`, with `insecure-skip-tls-verify` |
| `config/application-prod.yml` | Oracle and PostgreSQL passwords, Kafka JAAS, **HSM PIN**, SWIFT API key, JWT signing key, SendGrid |
| `src/cdc/debezium-oracle-connector.json` | LogMiner password, **Vault token**, GCP service account JSON |
| `src/tokenization/pan_tokenizer.py` | Static AES key, HMAC pepper, **Stripe live key**, Azure client secret |
| `src/aml/sanctions_screening.ts` | Cosmos DB key, Dow Jones credentials, PagerDuty routing key |
| `deploy/helm/values-prod.yaml` | Full `env` block with passwords, Datadog API and App keys |
| `deploy/ansible/vars/prod.yml` | `ansible_become_pass`, Vault token, SYS password, F5 credentials |
| `.dockerconfigjson`, `.aws/credentials` | Base64 registry auth, two AWS profiles |
| **Git history** | `config/prod-secrets.env` and `tmp/dr-runbook.env` + `tmp/hsm-backup-signing.key` (**two Vault unseal keys, root token, HSM PIN, SWIFT LAU key and signing private key**) |

### PII

| File | Contents |
|---|---|
| `telco/data/abonados_muestra_prod.csv` | 140 records: MSISDN, IMSI, IMEI, DNI, name, email, date of birth, address, IP and auto-debit card |
| `telco/data/export_facturacion_2024Q2.json` | 60 records with the same structure |
| `telco/logs/mediation-prod-2024-07-02.log` | Subscriber PII and PANs in error lines, plus startup credentials |
| `telco/notebooks/churn_analysis.ipynb` | PII in the **cell output**, not just in the code |
| `bank/data/clientes_kyc_extraccion.csv` | 160 customers: name, DNI, passport, SSN, date of birth, address, CCI, IBAN, **PAN + expiration + CVV**, PEP flag, balance |
| `bank/test/fixtures/pain001_payloads.json` | 90 transactions with full debtor details and card data |
| `bank/db/migrations/V8__seed_kyc_data.sql` | 70 `INSERT` statements with PII and card data |
| `bank/logs/payments-orchestrator-2024-07-05.log` | PAN and CVV in error traces, passport and date of birth in AML alerts |
| Git history (both) | Extracts of those same CSVs under `tmp/`, deleted from the tip |

The `V8__seed_kyc_data.sql` and notebook cases are the most uncomfortable for a
bank: this isn't a poorly stored secret, it's a production extract that made it
into version control. Rotating doesn't fix it.

---
