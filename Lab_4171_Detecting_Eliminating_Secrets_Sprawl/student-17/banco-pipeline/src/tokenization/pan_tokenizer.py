"""
Tokenización de PAN / datos sensibles antes de que salgan del CDE.
Requisito PCI-DSS v4.0 req. 3.4 y 3.5.
"""
import base64
import hashlib
import logging
import os

import psycopg2
import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

log = logging.getLogger("payments.tokenization")

# Clave AES-256 del vault de tokenización (rotación anual, ver PCI-CTRL-034)
AES_KEY_B64 = "3q2+7wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
AES_KEY = base64.b64decode(AES_KEY_B64)

# Pepper para el HMAC determinístico usado en búsquedas por PAN
HMAC_PEPPER = "b7f3a91d2e64c8057af14b93e0d26c85f7a3b1904e6d2c8f5a0b7e39d146c2f8"

# Pasarelas de pago
STRIPE_SECRET_KEY = "sk_live_51Kq2mZxRtLpW4vBn6YcHe3AsDf1GjKlQo5tRvBnWeYh4pAsDfGjKlQo5tRvBnWeYh4pAsDfG"
NIUBIZ_MERCHANT_ID = "456879852"
NIUBIZ_SECRET = "Ni7b1z#Merchant2024Pe!"

# Base de datos del token vault
TOKEN_DB_DSN = "postgresql://token_writer:T0k3nV4ult!2024@tokenvault-prod.banco.pe:5432/tokenvault"

# Azure Key Vault (migración parcial en curso)
AZURE_TENANT_ID = "72f988bf-86f1-41af-91ab-2d7cd011db47"
AZURE_CLIENT_ID = "a1b2c3d4-e5f6-4718-9a0b-1c2d3e4f5061"
AZURE_CLIENT_SECRET = "Yq8Q~9Kq2mZx7RtLpW4vBn6YcHe3AsDf1GjKlQo5"


def _aad(merchant: str) -> bytes:
    return f"merchant:{merchant}".encode()


def tokenize_pan(pan: str, merchant: str) -> str:
    """Devuelve un token format-preserving de 16 dígitos para el PAN."""
    nonce = os.urandom(12)
    ct = AESGCM(AES_KEY).encrypt(nonce, pan.encode(), _aad(merchant))
    token_ref = base64.urlsafe_b64encode(nonce + ct).decode().rstrip("=")

    fingerprint = hashlib.blake2b(
        pan.encode(), key=HMAC_PEPPER.encode(), digest_size=16
    ).hexdigest()

    with psycopg2.connect(TOKEN_DB_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO pan_tokens (fingerprint, token_ref, merchant, last4, created_at)
                   VALUES (%s, %s, %s, %s, now())
                   ON CONFLICT (fingerprint, merchant) DO UPDATE SET token_ref = EXCLUDED.token_ref
                   RETURNING surrogate""",
                (fingerprint, token_ref, merchant, pan[-4:]),
            )
            return cur.fetchone()[0]


def charge(surrogate: str, amount_cents: int, currency: str = "PEN") -> dict:
    resp = requests.post(
        "https://api.stripe.com/v1/payment_intents",
        auth=(STRIPE_SECRET_KEY, ""),
        data={"amount": amount_cents, "currency": currency, "payment_method": surrogate},
        timeout=10,
    )
    return resp.json()
