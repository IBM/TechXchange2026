#!/bin/bash

# FleetOps Backend - Run Script

echo "==================================="
echo "FleetOps Simulation Backend"
echo "==================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment with Python 3.12..."
    python3.12 -m venv venv || python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "==================================="
echo "Starting FleetOps Backend Server"
echo "==================================="
echo ""
echo "API will be available at: http://localhost:8085"
echo "API Documentation: http://localhost:8085/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Load local environment variables if .env exists (never committed — see .gitignore)
#
# Credential priority (highest → lowest):
#   1. IBM Vault (AppRole)   — VAULT_ADDR + VAULT_ROLE_ID + VAULT_SECRET_ID in .env
#                              The app fetches WEBMETHODS_URL / WEBMETHODS_API_KEY
#                              from Vault at startup.  Set VAULT_REQUIRED=true to
#                              fail fast when Vault is unreachable (production).
#   2. Direct env vars        — WEBMETHODS_URL / WEBMETHODS_API_KEY in .env (fallback)
#   3. config.yaml placeholders — only used when neither Vault nor env vars provide values
#
# Example minimal .env for Vault-based credentials:
#   VAULT_ADDR=https://149.81.1.22:8200
#   VAULT_ROLE_ID=<role-id>
#   VAULT_SECRET_ID=<secret-id>
#   VAULT_REQUIRED=true
#   VAULT_TLS_VERIFY=false   # needed for self-signed certs
if [ -f ".env" ]; then
    echo "Loading environment from .env..."
    set -a && source .env && set +a
fi

# Run the server — stay in fleetops-backend/ so config.yaml is found at ./config.yaml
PYTHONPATH="$(pwd)/..:$(pwd)" uvicorn app.main:app --reload --host 0.0.0.0 --port 8085

# Made with Bob
