"""IBM Vault (HashiCorp Vault / AppRole) client utility.

A single, reusable VaultClient that handles AppRole authentication, token
caching, expiry refresh, and KV v2 secret fetching.  Any module that needs
secrets from Vault imports `get_vault_client()` — a factory that returns
`None` when Vault is not configured, allowing graceful env-var fallback.

Environment variables consumed:
    VAULT_ADDR        Full URL of the Vault server (e.g. https://host:8200)
    VAULT_ROLE_ID     AppRole role_id
    VAULT_SECRET_ID   AppRole secret_id
    VAULT_REQUIRED    If "true", any fetch failure raises RuntimeError instead
                      of returning None.  Recommended for production / OpenShift.
"""
import os
import time
import logging
import sys

import hvac
import hvac.exceptions

logger = logging.getLogger(__name__)

# Number of seconds before token expiry at which we proactively re-authenticate
_TOKEN_REFRESH_BUFFER_SECS = 60


class VaultClient:
    """HashiCorp Vault client with AppRole auth and KV v2 support.

    Designed to be generic: pass any mount_point + path to fetch_secret().
    Token is cached in memory and refreshed automatically on expiry or 403.
    """

    def __init__(
        self,
        addr: str | None = None,
        role_id: str | None = None,
        secret_id: str | None = None,
        tls_verify: str | None = None,
    ) -> None:
        self._addr = addr or os.environ.get("VAULT_ADDR", "")
        self._role_id = role_id or os.environ.get("VAULT_ROLE_ID", "")
        self._secret_id = secret_id or os.environ.get("VAULT_SECRET_ID", "")
        # tls_verify: resolved value from caller (config.yaml) or env var fallback
        _tls_raw = tls_verify or os.environ.get("VAULT_TLS_VERIFY", "true")
        self._tls_verify = _tls_raw.lower() != "false"
        self._vault_required = os.environ.get("VAULT_REQUIRED", "").lower() == "true"

        self._client: hvac.Client | None = None
        self._token_acquired_at: float = 0.0
        self._token_lease_duration: int = 0

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _authenticate(self) -> None:
        """Perform AppRole login and store the client token."""
        logger.info("Authenticating with Vault via AppRole at %s", self._addr)
        client = hvac.Client(url=self._addr, verify=self._tls_verify)
        response = client.auth.approle.login(
            role_id=self._role_id,
            secret_id=self._secret_id,
        )
        client.token = response["auth"]["client_token"]
        self._token_acquired_at = time.monotonic()
        self._token_lease_duration = response["auth"].get("lease_duration", 3600)
        self._client = client
        logger.info(
            "Vault AppRole login successful — token lease %ss (masked: ***)",
            self._token_lease_duration,
        )
        sys.stdout.flush()

    def _is_token_valid(self) -> bool:
        """Return True if a token exists and has not entered its refresh window."""
        if self._client is None or not self._client.token:
            return False
        elapsed = time.monotonic() - self._token_acquired_at
        remaining = self._token_lease_duration - elapsed
        return remaining > _TOKEN_REFRESH_BUFFER_SECS

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_secret(self, mount_point: str, path: str) -> dict | None:
        """Fetch a KV v2 secret and return its data dict.

        Args:
            mount_point: Vault KV v2 engine mount (e.g. "logisticsv2").
            path:        Secret path within the mount (e.g. "webmethods").

        Returns:
            Dict of secret key/value pairs, or None if unavailable and
            VAULT_REQUIRED is not set.

        Raises:
            RuntimeError: If VAULT_REQUIRED=true and the fetch fails for any reason.
        """
        try:
            if not self._is_token_valid():
                self._authenticate()

            response = self._client.secrets.kv.v2.read_secret_version(
                mount_point=mount_point,
                path=path,
                raise_on_deleted_version=True,
            )
            data: dict = response["data"]["data"]
            logger.info(
                "Vault secret fetched — mount=%s path=%s keys=%s",
                mount_point,
                path,
                list(data.keys()),
            )
            sys.stdout.flush()
            return data

        except hvac.exceptions.Forbidden:
            # Token was accepted at login but lacks read permission — re-auth once
            logger.warning("Vault Forbidden on %s/%s — re-authenticating", mount_point, path)
            try:
                self._authenticate()
                response = self._client.secrets.kv.v2.read_secret_version(
                    mount_point=mount_point,
                    path=path,
                    raise_on_deleted_version=True,
                )
                return response["data"]["data"]
            except Exception as retry_exc:
                return self._handle_fetch_error(retry_exc, mount_point, path)

        except Exception as exc:
            return self._handle_fetch_error(exc, mount_point, path)

    def _handle_fetch_error(self, exc: Exception, mount_point: str, path: str) -> None:
        """Log the error and either raise or return None based on VAULT_REQUIRED."""
        msg = f"Failed to fetch Vault secret {mount_point}/{path}: {exc}"
        if self._vault_required:
            logger.error(msg)
            sys.stdout.flush()
            raise RuntimeError(msg) from exc
        logger.warning("%s — falling back to environment variables", msg)
        sys.stdout.flush()
        return None


def get_vault_client() -> VaultClient | None:
    """Factory that returns a configured VaultClient, or None if Vault is not configured.

    Returns None (without error) when VAULT_ROLE_ID or VAULT_SECRET_ID are
    absent so that callers can silently fall back to environment variables in
    local-dev environments where Vault is not available.
    """
    role_id = os.environ.get("VAULT_ROLE_ID", "")
    secret_id = os.environ.get("VAULT_SECRET_ID", "")
    if not role_id or not secret_id:
        logger.debug("VAULT_ROLE_ID / VAULT_SECRET_ID not set — Vault client not created")
        return None
    return VaultClient()

# Made with Bob
