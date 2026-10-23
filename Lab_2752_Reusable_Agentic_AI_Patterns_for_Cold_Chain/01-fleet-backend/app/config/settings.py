"""Configuration settings loader."""
import os
import yaml
import re
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel
from ..utils.vault_client import VaultClient, get_vault_client


class PersistenceLevels(BaseModel):
    """Persistence level configuration."""
    initial_data: bool = True
    on_events: bool = True
    interval_seconds: int = 30


class JSONConfig(BaseModel):
    """JSON persistence configuration."""
    data_directory: str = "./data"


class AstraConfig(BaseModel):
    """Astra DB configuration."""
    enabled: bool = False
    secure_connect_bundle: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    keyspace: str = "fleetops"


class Db2Config(BaseModel):
    """IBM Db2 configuration."""
    enabled: bool = False
    host: str = "localhost"
    port: int = 50000
    database: str = "fleetops"
    username: Optional[str] = None
    password: Optional[str] = None
    db_schema: str = "fleetops"


class PersistenceConfig(BaseModel):
    """Persistence configuration."""
    enabled: bool = True
    type: str = "json"
    levels: PersistenceLevels = PersistenceLevels()
    json_config: JSONConfig = JSONConfig()
    astra: AstraConfig = AstraConfig()
    db2: Db2Config = Db2Config()


class SimulationConfig(BaseModel):
    """Simulation configuration."""
    speed_multiplier: int = 10
    update_interval: int = 5
    num_trucks: int = 10
    incident_trucks: int = 4
    station_spacing_km: int = 120


class WatsonxOrchestrateConfig(BaseModel):
    """watsonx Orchestrate configuration."""
    enabled: bool = False
    url: str = ""
    api_key: str = ""
    agent_weather: str = ""
    agent_station: str = ""
    agent_route: str = ""
    agent_decision: str = ""
    agent_notification: str = ""
    timeout: int = 60


class WebMethodsConfig(BaseModel):
    """webMethods Integration configuration."""
    enabled: bool = False
    url: str = ""
    api_key: str = ""
    timeout: int = 30


class VaultConfig(BaseModel):
    """IBM Vault (AppRole) configuration from config.yaml.

    Values here are used when the corresponding VAULT_* environment variables
    are NOT set (e.g. local dev without a .env file).  Env vars always win.
    """
    addr: str = ""
    role_id: str = ""
    secret_id: str = ""
    tls_verify: str = "true"   # "false" for self-signed certs
    mount: str = "logisticsv2"
    path: str = "webmethods"         # secret path for webMethods credentials
    path_watsonx: str = "watsonx"    # secret path for watsonx Orchestrate credentials


class Settings(BaseModel):
    """Application settings."""
    persistence: PersistenceConfig = PersistenceConfig()
    simulation: SimulationConfig = SimulationConfig()
    watsonx_orchestrate: WatsonxOrchestrateConfig = WatsonxOrchestrateConfig()
    webmethods: WebMethodsConfig = WebMethodsConfig()
    vault: VaultConfig = VaultConfig()


class ConfigLoader:
    """Configuration loader singleton."""
    
    _instance: Optional['ConfigLoader'] = None
    _settings: Optional[Settings] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def _interpolate_env_vars(self, data: Any) -> Any:
        """Recursively interpolate environment variables in config data.
        
        Supports ${VAR_NAME} and ${VAR_NAME:default_value} syntax.
        
        Args:
            data: Configuration data (dict, list, str, or other)
            
        Returns:
            Data with environment variables interpolated
        """
        if isinstance(data, dict):
            return {key: self._interpolate_env_vars(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._interpolate_env_vars(item) for item in data]
        elif isinstance(data, str):
            # Pattern matches ${VAR_NAME} or ${VAR_NAME:default}
            pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
            
            def replace_env_var(match):
                var_name = match.group(1)
                default_value = match.group(2) if match.group(2) is not None else ""
                return os.environ.get(var_name, default_value)
            
            return re.sub(pattern, replace_env_var, data)
        else:
            return data
    
    def _apply_vault_secrets(self, secrets: dict, path: str) -> None:
        """Inject credentials fetched from a Vault path into Settings.

        Args:
            secrets: Dict returned by VaultClient.fetch_secret().
            path:    The Vault path the secrets came from — used to route keys
                     to the correct Settings section.
        """
        wm = self._settings.webmethods
        wo = self._settings.watsonx_orchestrate

        applied_wm = False
        applied_wo = False

        if "WEBMETHODS_URL" in secrets:
            wm.url = secrets["WEBMETHODS_URL"]
            applied_wm = True
        if "WEBMETHODS_API_KEY" in secrets:
            wm.api_key = secrets["WEBMETHODS_API_KEY"]
            applied_wm = True

        if "WATSONX_ORCHESTRATE_URL" in secrets:
            wo.url = secrets["WATSONX_ORCHESTRATE_URL"]
            applied_wo = True
        if "WATSONX_ORCHESTRATE_API_KEY" in secrets:
            wo.api_key = secrets["WATSONX_ORCHESTRATE_API_KEY"]
            applied_wo = True
        if "WATSONX_ORCHESTRATE_AGENT_WEATHER" in secrets:
            wo.agent_weather = secrets["WATSONX_ORCHESTRATE_AGENT_WEATHER"]
            applied_wo = True
        if "WATSONX_ORCHESTRATE_AGENT_STATION" in secrets:
            wo.agent_station = secrets["WATSONX_ORCHESTRATE_AGENT_STATION"]
            applied_wo = True
        if "WATSONX_ORCHESTRATE_AGENT_ROUTE" in secrets:
            wo.agent_route = secrets["WATSONX_ORCHESTRATE_AGENT_ROUTE"]
            applied_wo = True
        if "WATSONX_ORCHESTRATE_AGENT_DECISION" in secrets:
            wo.agent_decision = secrets["WATSONX_ORCHESTRATE_AGENT_DECISION"]
            applied_wo = True
        if "WATSONX_ORCHESTRATE_AGENT_NOTIFICATION" in secrets:
            wo.agent_notification = secrets["WATSONX_ORCHESTRATE_AGENT_NOTIFICATION"]
            applied_wo = True

        if applied_wm:
            print(f"✓ webMethods credentials loaded from Vault ({path})")
        if applied_wo:
            print(f"✓ watsonx Orchestrate credentials loaded from Vault ({path})")

    def _fetch_vault_secrets(self) -> None:
        """Attempt to load ALL credentials from Vault (watsonx + webMethods).

        Fetches two separate KV v2 paths within the same authenticated session:
          - vault.path_watsonx  (default: logisticsv2/watsonx)
          - vault.path          (default: logisticsv2/webmethods)

        Credential resolution order for the VaultClient:
          1. VAULT_ROLE_ID / VAULT_SECRET_ID environment variables (highest priority)
          2. vault.role_id / vault.secret_id from config.yaml
          3. Neither present → skip Vault, fall back to direct env vars

        Raises RuntimeError on failure when VAULT_REQUIRED=true.
        """
        vc = self._settings.vault
        role_id = os.environ.get("VAULT_ROLE_ID", "") or vc.role_id
        secret_id = os.environ.get("VAULT_SECRET_ID", "") or vc.secret_id
        addr = os.environ.get("VAULT_ADDR", "") or vc.addr
        tls_verify = os.environ.get("VAULT_TLS_VERIFY", "") or vc.tls_verify

        if not role_id or not secret_id:
            vault = get_vault_client()  # may still work if env vars were set after parsing
        else:
            vault = VaultClient(addr=addr, role_id=role_id, secret_id=secret_id, tls_verify=tls_verify)

        if vault is None:
            print("⚠ Vault not configured — falling back to environment variables")
            return

        mount_point = vc.mount or "logisticsv2"
        vault_required = os.environ.get("VAULT_REQUIRED", "").lower() == "true"

        # Fetch watsonx Orchestrate credentials
        path_watsonx = vc.path_watsonx or "watsonx"
        secrets_watsonx = vault.fetch_secret(mount_point, path_watsonx)
        if secrets_watsonx:
            self._apply_vault_secrets(secrets_watsonx, path_watsonx)
        elif vault_required:
            raise RuntimeError(
                f"VAULT_REQUIRED=true but Vault secret fetch for {mount_point}/{path_watsonx} returned None"
            )
        else:
            print(f"⚠ Vault fetch returned no data for {mount_point}/{path_watsonx} — falling back to environment variables")

        # Fetch webMethods credentials (re-uses the same authenticated vault client)
        path_wm = vc.path or "webmethods"
        secrets_wm = vault.fetch_secret(mount_point, path_wm)
        if secrets_wm:
            self._apply_vault_secrets(secrets_wm, path_wm)
        elif vault_required:
            raise RuntimeError(
                f"VAULT_REQUIRED=true but Vault secret fetch for {mount_point}/{path_wm} returned None"
            )
        else:
            print(f"⚠ Vault fetch returned no data for {mount_point}/{path_wm} — falling back to environment variables")

    def load_config(self, config_path: str = "config.yaml") -> Settings:
        """Load configuration from YAML file with environment variable interpolation.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Settings object
        """
        if self._settings is not None:
            return self._settings
        
        config_file = Path(config_path)
        
        if not config_file.exists():
            print(f"Config file {config_path} not found, using defaults")
            self._settings = Settings()
            self._fetch_vault_secrets()
            self._apply_env_overrides()
            return self._settings
        
        try:
            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Interpolate environment variables
            config_data = self._interpolate_env_vars(config_data)
            
            self._settings = Settings(**config_data)
            print(f"✓ Configuration loaded from {config_path}")

            # Priority: Vault > env vars > config.yaml placeholders
            # Vault is applied first; env-var overrides run after and win if set.
            self._fetch_vault_secrets()

            # Always apply env overrides so that .env values win over
            # config.yaml placeholders that resolved to empty strings
            self._apply_env_overrides()
            
            # Validate WatsonX configuration if enabled
            if self._settings.watsonx_orchestrate.enabled:
                self._validate_watsonx_config()

            return self._settings
        except Exception as e:
            print(f"Error loading config: {e}, using defaults")
            self._settings = Settings()
            self._fetch_vault_secrets()
            self._apply_env_overrides()
            return self._settings
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides to settings after defaults are loaded.

        Reads well-known env vars and patches the already-constructed Settings
        object in-place so callers get live env values even when no config.yaml
        is present.
        """
        if self._settings is None:
            return

        # ── Persistence ───────────────────────────────────────────────────────
        if os.environ.get("PERSISTENCE_ENABLED", "").lower() in ("false", "0"):
            self._settings.persistence.enabled = False

        # ── Simulation ────────────────────────────────────────────────────────
        if val := os.environ.get("SIMULATION_SPEED_MULTIPLIER"):
            try:
                self._settings.simulation.speed_multiplier = int(val)
            except ValueError:
                pass
        if val := os.environ.get("SIMULATION_NUM_TRUCKS"):
            try:
                self._settings.simulation.num_trucks = int(val)
            except ValueError:
                pass

        # ── watsonx Orchestrate ───────────────────────────────────────────────
        if val := os.environ.get("WATSONX_ORCHESTRATE_URL"):
            self._settings.watsonx_orchestrate.url = val
            self._settings.watsonx_orchestrate.enabled = True
        if val := os.environ.get("WATSONX_ORCHESTRATE_API_KEY"):
            self._settings.watsonx_orchestrate.api_key = val
        if val := os.environ.get("WATSONX_ORCHESTRATE_AGENT_WEATHER"):
            self._settings.watsonx_orchestrate.agent_weather = val
        if val := os.environ.get("WATSONX_ORCHESTRATE_AGENT_STATION"):
            self._settings.watsonx_orchestrate.agent_station = val
        if val := os.environ.get("WATSONX_ORCHESTRATE_AGENT_ROUTE"):
            self._settings.watsonx_orchestrate.agent_route = val
        if val := os.environ.get("WATSONX_ORCHESTRATE_AGENT_DECISION"):
            self._settings.watsonx_orchestrate.agent_decision = val
        if val := os.environ.get("WATSONX_ORCHESTRATE_AGENT_NOTIFICATION"):
            self._settings.watsonx_orchestrate.agent_notification = val

    def _validate_watsonx_config(self):
        """Validate WatsonX Orchestrate configuration.
        
        Raises:
            ValueError: If required configuration is missing
        """
        config = self._settings.watsonx_orchestrate
        missing_vars = []
        
        if not config.url or config.url == "":
            missing_vars.append("WATSONX_ORCHESTRATE_URL")
        if not config.api_key or config.api_key == "":
            missing_vars.append("WATSONX_ORCHESTRATE_API_KEY")
        if not config.agent_weather or config.agent_weather == "":
            missing_vars.append("WATSONX_ORCHESTRATE_AGENT_WEATHER")
        if not config.agent_station or config.agent_station == "":
            missing_vars.append("WATSONX_ORCHESTRATE_AGENT_STATION")
        if not config.agent_route or config.agent_route == "":
            missing_vars.append("WATSONX_ORCHESTRATE_AGENT_ROUTE")
        if not config.agent_decision or config.agent_decision == "":
            missing_vars.append("WATSONX_ORCHESTRATE_AGENT_DECISION")
        if not config.agent_notification or config.agent_notification == "":
            missing_vars.append("WATSONX_ORCHESTRATE_AGENT_NOTIFICATION")
        
        if missing_vars:
            error_msg = (
                f"WatsonX Orchestrate is enabled but required environment variables are missing:\n"
                f"  {', '.join(missing_vars)}\n"
                f"Please ensure these environment variables are set via Kubernetes secrets."
            )
            print(f"❌ {error_msg}")
            raise ValueError(error_msg)
        
        print(f"✓ WatsonX Orchestrate configuration validated")
        print(f"  - URL: {config.url[:50]}...")
        print(f"  - API Key: {'*' * 20}")
        print(f"  - Weather Agent: {config.agent_weather}")
        print(f"  - Station Agent: {config.agent_station}")
        print(f"  - Route Agent: {config.agent_route}")
        print(f"  - Decision Agent: {config.agent_decision}")
        print(f"  - Notification Agent: {config.agent_notification}")
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides to settings.

        Called both when config.yaml is absent AND after it is loaded, so that
        a sourced .env file always wins over config.yaml placeholder values
        that resolved to empty strings (e.g. ${WEBMETHODS_URL} with no env var set).
        """
        wo = self._settings.watsonx_orchestrate
        wo.enabled = os.environ.get("WATSONX_ORCHESTRATE_URL", "") != ""
        wo.url = os.environ.get("WATSONX_ORCHESTRATE_URL", wo.url)
        wo.api_key = os.environ.get("WATSONX_ORCHESTRATE_API_KEY", wo.api_key)
        wo.agent_weather = os.environ.get("WATSONX_ORCHESTRATE_AGENT_WEATHER", wo.agent_weather)
        wo.agent_station = os.environ.get("WATSONX_ORCHESTRATE_AGENT_STATION", wo.agent_station)
        wo.agent_route = os.environ.get("WATSONX_ORCHESTRATE_AGENT_ROUTE", wo.agent_route)
        wo.agent_decision = os.environ.get("WATSONX_ORCHESTRATE_AGENT_DECISION", wo.agent_decision)
        wo.agent_notification = os.environ.get("WATSONX_ORCHESTRATE_AGENT_NOTIFICATION", wo.agent_notification)

        wm = self._settings.webmethods
        wm.url = os.environ.get("WEBMETHODS_URL", wm.url)
        wm.api_key = os.environ.get("WEBMETHODS_API_KEY", wm.api_key)
        # Respect config.yaml's enabled flag — only auto-enable when credentials are
        # present; never enable if config.yaml explicitly set enabled: false.
        if wm.url and wm.api_key:
            # Credentials are present: honour the yaml flag (default True)
            pass  # wm.enabled already carries the config.yaml value
        else:
            # Missing credentials: disable regardless of yaml flag
            wm.enabled = False

        if wm.enabled:
            print(f"✓ webMethods integration configured")
            print(f"  - URL: {wm.url[:60]}...")
            print(f"  - API Key: {'*' * 20}")
        else:
            print("⚠ webMethods integration disabled (WEBMETHODS_URL / WEBMETHODS_API_KEY not set or enabled: false)")

    def reload_config(self, config_path: str = "config.yaml") -> Settings:
        """Reload configuration from file, re-reading env vars.

        Clears the cached settings so the next call to load_config() picks up
        any changes to environment variables (e.g. after a Secret rotation)
        without requiring a process restart.

        Returns:
            Fresh Settings object
        """
        self._settings = None
        return self.load_config(config_path)

    def get_settings(self) -> Settings:
        """Get current settings.
        
        Returns:
            Settings object
        """
        if self._settings is None:
            return self.load_config()
        return self._settings


# Global config loader instance
_config_loader = ConfigLoader()


def get_settings() -> Settings:
    """Get application settings.
    
    Returns:
        Settings object
    """
    return _config_loader.get_settings()


def load_config(config_path: str = "config.yaml") -> Settings:
    """Load configuration from file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Settings object
    """
    return _config_loader.load_config(config_path)

# Made with Bob
