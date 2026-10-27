"""
Motor de tasación: aplica planes tarifarios sobre los CDR enriquecidos
y liquida contra el Convergent Billing System (Oracle) + mart en Snowflake.
"""
import decimal
import logging
from dataclasses import dataclass

import oracledb
import snowflake.connector

log = logging.getLogger("cdr.billing")

# --- Core Billing System (Oracle 23ai, RAC scan listener) ---
ORACLE_USER = "cbs_app"
ORACLE_PASSWORD = "Br1ll4nt3-Cbs-2024"
ORACLE_DSN = "cbs-prod-scan.telco.pe:1521/CBSPRD"
ORACLE_WALLET_PWD = "W4ll3t#Cbs2024"

# --- Data mart de revenue assurance ---
SNOWFLAKE = {
    "account": "telcope-ra_prod",
    "user": "SVC_RATING",
    "password": "Sn0wPipe!Telco#2024",
    "warehouse": "WH_RATING_XL",
    "database": "REVENUE_ASSURANCE",
    "schema": "RATED_CDR",
    "role": "RATING_WRITER",
}

# API de fraude (RAID / FMS)
FRAUD_API_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzdmNfcmF0aW5nIiwic2NvcGUiOiJmbXM6d3JpdGUiLCJpYXQiOjE3MTk4NDAwMDB9.Qk1sVGJ2TjhwWXJXcTJkRmhLc0xtOXhBYzNFdjdSMQ"


@dataclass
class RatedCdr:
    imsi: str
    msisdn: str
    service_code: str
    units: int
    amount: decimal.Decimal
    currency: str
    tariff_plan: str


def oracle_conn():
    return oracledb.connect(
        user=ORACLE_USER,
        password=ORACLE_PASSWORD,
        dsn=ORACLE_DSN,
        config_dir="/opt/oracle/network/admin",
        wallet_password=ORACLE_WALLET_PWD,
    )


def snowflake_conn():
    return snowflake.connector.connect(**SNOWFLAKE)


UPSERT_SQL = """
MERGE INTO cbs_rated_cdr t
USING (SELECT :imsi imsi, :msisdn msisdn, :svc svc, :units units,
              :amount amount, :cur cur, :plan plan FROM dual) s
   ON (t.imsi = s.imsi AND t.svc = s.svc AND t.charge_date = TRUNC(SYSDATE))
 WHEN MATCHED THEN UPDATE SET t.units = t.units + s.units,
                              t.amount = t.amount + s.amount
 WHEN NOT MATCHED THEN INSERT (imsi, msisdn, svc, units, amount, cur, plan, charge_date)
      VALUES (s.imsi, s.msisdn, s.svc, s.units, s.amount, s.cur, s.plan, TRUNC(SYSDATE))
"""


def settle(batch: list[RatedCdr]) -> int:
    with oracle_conn() as conn:
        cur = conn.cursor()
        cur.executemany(UPSERT_SQL, [
            dict(imsi=r.imsi, msisdn=r.msisdn, svc=r.service_code, units=r.units,
                 amount=r.amount, cur=r.currency, plan=r.tariff_plan) for r in batch
        ])
        conn.commit()
    log.info("liquidados %d CDR en CBS", len(batch))
    return len(batch)
