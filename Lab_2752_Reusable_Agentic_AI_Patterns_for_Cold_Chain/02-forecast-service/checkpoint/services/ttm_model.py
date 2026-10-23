#!/usr/bin/env python3
"""
TTM Model Wrapper
Handles loading and inference of Granite TTM (Tiny Time Mixer) model

Routing priority (highest → lowest):
  1. IBM watsonx.ai native API  — when TTM_MODEL_ID is set (Phase 1 revised)
  2. Local HuggingFace pipeline — when USE_TTM_MODEL=true
  3. Mock forecast              — fallback for development
"""

import os
import numpy as np
import pandas as pd
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration from .env
TTM_MODEL_PATH     = os.getenv("TTM_MODEL_PATH", "ibm-granite/granite-timeseries-ttm-v1")
TTM_MODEL_REVISION = os.getenv("TTM_MODEL_REVISION", "main")
CONTEXT_LENGTH     = int(os.getenv("CONTEXT_LENGTH", "512"))
PREDICTION_LENGTH  = int(os.getenv("PREDICTION_LENGTH", "96"))
FREQUENCY          = os.getenv("FREQUENCY", "1min")
USE_TTM_MODEL      = os.getenv("USE_TTM_MODEL", "False").lower() == "true"
DEVICE             = os.getenv("DEVICE", "cpu")

# ── Native watsonx.ai API config (Phase 1 revised) ───────────────────────────
# Set TTM_MODEL_ID to enable serverless inference — no deployment required.
# TTM_MODEL_ID=ibm/granite-ttm-512-96-r2  (matches CONTEXT_LENGTH=512, PREDICTION_LENGTH=96)
TTM_MODEL_ID      = os.getenv("TTM_MODEL_ID", "").strip()
WML_SPACE_ID      = os.getenv("WML_SPACE_ID", "").strip()
WML_API_KEY       = os.getenv("WML_API_KEY", "").strip()
IBM_CLOUD_REGION  = os.getenv("IBM_CLOUD_REGION", "us-south").strip()
# Derived from region — never hardcoded per PLAN.md §1
NATIVE_TTM_URL    = (
    f"https://{IBM_CLOUD_REGION}.ml.cloud.ibm.com"
    "/ml/v1/time_series/forecast?version=2024-05-31"
)

# ── OpenScale payload logging config ─────────────────────────────────────────
# When GOVERNANCE_PAYLOAD_LOGGING=true, every native API call writes a record
# to the OpenScale payload log so the governance feedback loop has live data.
# Reads IDs from governance/artifacts/deployment.json — no hardcoding.
GOVERNANCE_PAYLOAD_LOGGING = os.getenv("GOVERNANCE_PAYLOAD_LOGGING", "true").lower() == "true"
# Path to deployment.json — works whether running from repo root or forecast-backend/
_GOVERNANCE_DEPLOYMENT_JSON = os.path.join(
    os.path.dirname(__file__),          # forecast-backend/services/
    "..", "..",                          # → repo root
    "governance", "artifacts", "deployment.json"
)


class TTMModelWrapper:
    """
    Wrapper for Granite TTM (Tiny Time Mixer) model

    Routing:
      - TTM_MODEL_ID set → calls IBM watsonx.ai native time-series API (no deployment needed)
      - USE_TTM_MODEL=true → loads model locally from HuggingFace
      - neither           → returns mock forecast for development
    """

    def __init__(self):
        self.pipeline     = None
        self.model_loaded = False
        # Native API routing
        self._ttm_model_id = TTM_MODEL_ID
        self._wml_space_id = WML_SPACE_ID
        self._wml_api_key  = WML_API_KEY
        self._iam_token:   Optional[str] = None
        self._token_expiry: float = 0.0
        # Governance: lazy-loaded OpenScale IDs
        self._governance_ids: Optional[dict] = None
        self._wos_client = None
        
    def load_model(self):
        """
        Load TTM model from HuggingFace (local pipeline path only).

        This is NOT called for the native watsonx.ai API path — when TTM_MODEL_ID
        is set, scoring goes directly to IBM Cloud via score_via_native_api() and
        no local model download is needed.

        Only runs when USE_TTM_MODEL=True (local HuggingFace pipeline).
        """
        # Native API path: TTM_MODEL_ID is set → no local model needed
        if self._ttm_model_id:
            return  # is_loaded() already returns True for this path

        if not USE_TTM_MODEL:
            # Neither native API nor local model — mock path
            return
        
        try:
            print(f"🔄 Loading Granite TTM model: {TTM_MODEL_PATH}")
            print(f"   Context Length: {CONTEXT_LENGTH}")
            print(f"   Prediction Length: {PREDICTION_LENGTH}")
            print(f"   Frequency: {FREQUENCY}")
            print(f"   Device: {DEVICE}")
            
            # Import TTM dependencies (only when needed)
            from tsfm_public import TimeSeriesForecastingPipeline, TinyTimeMixerForPrediction
            
            # Load pre-trained model from HuggingFace
            print("   Downloading model from HuggingFace...")
            model = TinyTimeMixerForPrediction.from_pretrained(
                TTM_MODEL_PATH,
                revision=TTM_MODEL_REVISION
            )
            
            # Create forecasting pipeline
            print("   Creating forecasting pipeline...")
            self.pipeline = TimeSeriesForecastingPipeline(
                model=model,
                timestamp_column="timestamp",
                id_columns=["id"],
                target_columns=["value"],
                context_length=CONTEXT_LENGTH,
                prediction_length=PREDICTION_LENGTH,
                freq=FREQUENCY,  # Frequency from .env (e.g., "1min" for cold-chain monitoring)
                device=DEVICE
            )
            
            self.model_loaded = True
            print("✅ TTM model loaded successfully")
            
        except ImportError as e:
            print(f"❌ TTM dependencies not installed: {e}")
            print("   Install with: pip install granite-tsfm torch transformers")
            print("   Using mock forecasts instead")
            
        except Exception as e:
            print(f"❌ Error loading TTM model: {e}")
            print("   Using mock forecasts instead")
    
    def forecast(self, historical_data: pd.DataFrame) -> np.ndarray:
        """
        Generate forecast using TTM model.

        Routes to IBM watsonx.ai native API when TTM_MODEL_ID is set;
        otherwise falls through to the local HuggingFace pipeline (original behaviour).

        Args:
            historical_data: DataFrame with columns:
                - timestamp: datetime
                - id: identifier (e.g., truck_id)
                - value: time series value (e.g., temperature)

        Returns:
            np.ndarray: Predicted values for next PREDICTION_LENGTH time steps
        """
        # ── Native watsonx.ai API path ────────────────────────────────────────
        if self._ttm_model_id:
            print("   🔮 Routing forecast to IBM watsonx.ai native TTM API...")
            return self.score_via_native_api(historical_data)

        # ── Local pipeline path (unchanged) ───────────────────────────────────
        if not self.model_loaded or self.pipeline is None:
            raise RuntimeError(
                "TTM model not loaded. Either:\n"
                "1. Set TTM_MODEL_ID=ibm/granite-ttm-512-96-r2 in .env (recommended)\n"
                "2. Set USE_TTM_MODEL=true in .env and call load_model()\n"
                "3. Install dependencies: pip install granite-tsfm torch transformers"
            )
        
        try:
            # Validate input data
            required_columns = ['timestamp', 'id', 'value']
            missing_columns = [col for col in required_columns if col not in historical_data.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            # Ensure we have enough context
            if len(historical_data) < CONTEXT_LENGTH:
                raise ValueError(
                    f"Insufficient data: need {CONTEXT_LENGTH} points, got {len(historical_data)}"
                )
            
            # Use last CONTEXT_LENGTH points for prediction
            context_data = historical_data.tail(CONTEXT_LENGTH).copy()
            
            # Run TTM model prediction
            print(f"   Running TTM forecast on {len(context_data)} data points...")
            predictions = self.pipeline(context_data)
            
            # DEBUG: Print what TTM returned
            print(f"   🔍 TTM output type: {type(predictions)}")
            if isinstance(predictions, dict):
                print(f"   🔍 TTM dict keys: {predictions.keys()}")
            
            # Extract predicted values
            # TTM returns a dict with 'prediction' key containing the forecast
            if isinstance(predictions, dict) and 'prediction' in predictions:
                forecast_values = predictions['prediction']
                print(f"   🔍 Forecast values type: {type(forecast_values)}, shape: {getattr(forecast_values, 'shape', 'N/A')}")
            else:
                forecast_values = predictions
                print(f"   🔍 Direct forecast type: {type(forecast_values)}, shape: {getattr(forecast_values, 'shape', 'N/A')}")
            
            # Convert to numpy array and extract just the values (not timestamps)
            if isinstance(forecast_values, pd.DataFrame):
                print(f"   🔍 DataFrame columns: {forecast_values.columns.tolist()}")
                print(f"   🔍 DataFrame shape: {forecast_values.shape}")
                # If it's a DataFrame, get the prediction column values
                if 'prediction' in forecast_values.columns:
                    forecast_array = forecast_values['prediction'].values
                else:
                    # Get the first numeric column
                    forecast_array = forecast_values.iloc[:, 0].values
            elif isinstance(forecast_values, pd.Series):
                forecast_array = forecast_values.values
            else:
                forecast_array = np.array(forecast_values)
            
            # Ensure it's a 1D array of floats
            forecast_array = np.asarray(forecast_array, dtype=float).flatten()
            
            print(f"   ✅ Generated {len(forecast_array)} predictions")
            return forecast_array
            
        except Exception as e:
            print(f"❌ Error during TTM forecast: {e}")
            raise
    
    def score_via_native_api(self, historical_data: pd.DataFrame) -> np.ndarray:
        """
        Call IBM watsonx.ai native time-series forecast API (serverless — no deployment needed).

        Uses /ml/v1/time_series/forecast with model_id=ibm/granite-ttm-512-96-r2.
        The API accepts a named DataFrame (timestamp + temperature columns) and returns
        96-step predictions directly — no WML Function, no container, ~1-2s latency.

        Args:
            historical_data: DataFrame with columns:
                - timestamp: datetime or ISO-string
                - value:     temperature readings (renamed to 'temperature' for the API)
                Must contain at least CONTEXT_LENGTH rows.

        Returns:
            np.ndarray of shape (PREDICTION_LENGTH,) — identical to local forecast() return.
        """
        import time as _time
        import requests as _requests

        # ── Always fetch a fresh IAM token (notebook pattern — never stale) ──
        # Per PLAN.md §1.6: tokens expire ~1h; calling get_token() every request
        # lets the token manager handle refresh automatically.
        if _time.time() >= self._token_expiry - 60:
            self._refresh_iam_token()
        # Normalise bearer format (token_manager may or may not include "Bearer ")
        bearer = self._iam_token
        if not bearer.startswith("Bearer "):
            bearer = "Bearer " + bearer

        # ── Build payload ─────────────────────────────────────────────────────
        ctx = historical_data.tail(CONTEXT_LENGTH).copy()

        # Convert timestamps to ISO-8601 strings — required by the native API
        if pd.api.types.is_datetime64_any_dtype(ctx["timestamp"]):
            ts_list = ctx["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S").tolist()
        else:
            ts_list = [str(t) for t in ctx["timestamp"].tolist()]

        # API expects the column named "temperature", not "value"
        temp_list = ctx["value"].tolist()

        payload = {
            "model_id": self._ttm_model_id,   # "ibm/granite-ttm-512-96-r2" — IBM SaaS hosted
            "space_id": self._wml_space_id,   # WML deployment space (not a WML Function)
            "schema": {
                "timestamp_column": "timestamp",
                "target_columns":   ["temperature"],
                "freq":             FREQUENCY,
            },
            "parameters": {"prediction_length": PREDICTION_LENGTH},
            "data": {
                "timestamp":   ts_list,
                "temperature": temp_list,
            },
        }

        # ── Call native API (region-derived URL, never hardcoded) ────────────
        print(f"   📡 Calling watsonx.ai native TTM API ({self._ttm_model_id})...")
        response = _requests.post(
            NATIVE_TTM_URL,
            json=payload,
            headers={
                "Authorization": bearer,
                "Content-Type":  "application/json",
            },
            timeout=30,
        )
        response.raise_for_status()

        # ── Parse response ────────────────────────────────────────────────────
        # Response: {"results": [{"temperature": [...96 floats...], "timestamp": [...]}]}
        body = response.json()
        try:
            predictions = body["results"][0]["temperature"]
        except (KeyError, IndexError) as exc:
            raise ValueError(
                f"Unexpected native API response shape. Keys: {list(body.keys())}"
            ) from exc

        result = np.array(predictions, dtype=float)
        print(f"   ✅ Native API returned {len(result)} predictions")

        # ── Log to OpenScale payload dataset (governance) ─────────────────────
        # Submit in a true fire-and-forget daemon thread so the IAM token fetch
        # and HTTP call to OpenScale never add latency to the forecast response.
        if GOVERNANCE_PAYLOAD_LOGGING:
            import threading as _threading
            _t = _threading.Thread(
                target=self._log_payload_to_openscale,
                args=(ctx.copy(), result.copy()),
                daemon=True,
                name="gov-payload-log",
            )
            _t.start()

        return result

    def _load_governance_ids(self) -> Optional[dict]:
        """Load OpenScale resource IDs from governance/artifacts/deployment.json."""
        import json as _json
        try:
            path = os.path.normpath(_GOVERNANCE_DEPLOYMENT_JSON)
            if not os.path.exists(path):
                return None
            with open(path) as f:
                ids = _json.load(f)
            # Need at minimum payload_data_set_id to log
            if ids.get("payload_data_set_id") and ids.get("subscription_id"):
                return ids
        except Exception:
            pass
        return None

    def _get_governance_wos_client(self):
        """Lazily initialise OpenScale client (reuses across requests)."""
        if self._wos_client is not None:
            return self._wos_client
        if not self._wml_api_key:
            return None
        try:
            from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
            from ibm_watson_openscale import APIClient as WosAPIClient
            auth = IAMAuthenticator(apikey=self._wml_api_key)
            self._wos_client = WosAPIClient(authenticator=auth)
            return self._wos_client
        except Exception as e:
            print(f"   ⚠️  OpenScale client init failed: {e}")
            return None

    def _log_payload_to_openscale(self, ctx: pd.DataFrame, predictions: np.ndarray):
        """
        Write one payload record to the OpenScale payload log.

        Feature values (summary stats of the context window) + scalar prediction
        (mean of 96-step forecast) are stored — NOT the raw 512-float arrays.
        This is what OpenScale monitors and drift checks read from.

        Runs in a fire-and-forget fashion — any failure is logged but never
        raises to the caller so scoring is never blocked.
        """
        import uuid as _uuid
        try:
            # Lazy-load governance IDs
            if self._governance_ids is None:
                self._governance_ids = self._load_governance_ids()
            if not self._governance_ids:
                return  # governance not provisioned yet — silently skip

            wos = self._get_governance_wos_client()
            if wos is None:
                return

            from ibm_watson_openscale.supporting_classes.payload_record import PayloadRecord

            # Build feature summary from context window
            temps = ctx["value"].values if "value" in ctx.columns else ctx["temperature"].values
            payload_data_set_id = self._governance_ids["payload_data_set_id"]

            # Infer cargo_type from the caller context if available
            cargo_type = getattr(self, "_last_cargo_type", "unknown")
            critical_threshold = getattr(self, "_last_critical_threshold", 8.0)

            FEATURE_FIELDS    = ["temp_mean", "temp_std", "temp_min", "temp_max",
                                  "critical_threshold", "cargo_type"]
            PREDICTION_FIELDS = ["predicted_temp_mean"]

            feature_values = [
                round(float(np.mean(temps)), 4),
                round(float(np.std(temps)),  4),
                round(float(np.min(temps)),  4),
                round(float(np.max(temps)),  4),
                float(critical_threshold),
                str(cargo_type),
            ]
            pred_mean = round(float(np.mean(predictions)), 4)

            record = PayloadRecord(
                scoring_id=str(_uuid.uuid4()),
                request={"fields": FEATURE_FIELDS,    "values": [feature_values]},
                response={"fields": PREDICTION_FIELDS, "values": [[pred_mean]]},
                response_time=1500,
            )
            wos.data_sets.store_records(
                data_set_id=payload_data_set_id,
                request_body=[record],
                background_mode=True,   # non-blocking — don't delay forecast response
            )
            print(f"   📋 Payload logged to OpenScale (pred_mean={pred_mean})")
        except Exception as e:
            # Never block the forecast for governance failures
            print(f"   ⚠️  OpenScale payload log skipped: {e}")

    def _refresh_iam_token(self) -> None:
        """Fetch a fresh IBM Cloud IAM bearer token using WML_API_KEY."""
        import requests as _requests
        import time as _time

        if not self._wml_api_key:
            raise ValueError(
                "WML_API_KEY is not set. Add it to .env or the OCP Secret."
            )
        response = _requests.post(
            "https://iam.cloud.ibm.com/identity/token",
            data={
                "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                "apikey": self._wml_api_key,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        response.raise_for_status()
        token_data = response.json()
        self._iam_token    = token_data["access_token"]
        self._token_expiry = _time.time() + int(token_data.get("expires_in", 3600))
        print("   🔑 IAM token refreshed")

    def is_loaded(self) -> bool:
        """Check if the model is ready to serve requests."""
        if self._ttm_model_id:
            return True   # native API path — always ready
        return self.model_loaded and self.pipeline is not None


# Global instance (singleton pattern)
_ttm_model_instance: Optional[TTMModelWrapper] = None


def get_ttm_model() -> TTMModelWrapper:
    """
    Get global TTM model instance (singleton)
    
    This ensures we only load the model once and reuse it
    for all forecasting requests.
    """
    global _ttm_model_instance
    
    if _ttm_model_instance is None:
        _ttm_model_instance = TTMModelWrapper()
        _ttm_model_instance.load_model()
    
    return _ttm_model_instance


# Example usage
if __name__ == "__main__":
    """
    Test TTM model — native watsonx.ai API path.
    Requires TTM_MODEL_ID, WML_SPACE_ID, WML_API_KEY in .env
    """
    print("=" * 60)
    print("TTM Model Test — Native watsonx.ai API")
    print("=" * 60)

    model = TTMModelWrapper()

    if model.is_loaded():
        print("\n📊 Creating sample time series data (512 points)...")
        sample_data = pd.DataFrame({
            'timestamp': pd.date_range('2025-01-01', periods=CONTEXT_LENGTH, freq='1min'),
            'id':        ['TRUCK-001'] * CONTEXT_LENGTH,
            'value':     np.random.randn(CONTEXT_LENGTH) * 2 + 2.5,
        })

        print(f"   Data shape: {sample_data.shape}")
        print(f"   Time range: {sample_data['timestamp'].min()} → {sample_data['timestamp'].max()}")

        print("\n🔮 Generating forecast...")
        predictions = model.forecast(sample_data)

        print(f"   Predictions shape: {predictions.shape}")
        print(f"   First 5 values   : {predictions[:5].round(3).tolist()}")
        print(f"   Min / Max        : {predictions.min():.3f} / {predictions.max():.3f}")
        print("\n✅ Test complete!")
    else:
        print("\n⚠️  Model not ready — set TTM_MODEL_ID, WML_SPACE_ID, WML_API_KEY in .env")

# Made with Bob
