#!/bin/bash
#
# Sync environment variables from a private .env.railway file into Railway.
# Usage:
#   1. cp PRODUCTION_ENV_TEMPLATE .env.railway
#   2. Fill in REAL secrets (SECRET_KEY, DATABASE_URL, OPENAI_API_KEY, etc.)
#   3. ./scripts/push_env_to_railway.sh [.env.railway]
#
# Requires: Railway CLI logged in (`railway login`)

set -euo pipefail

ENV_FILE="${1:-.env.railway}"

if [ ! -f "$ENV_FILE" ]; then
  echo "❌ Missing $ENV_FILE. Create it from PRODUCTION_ENV_TEMPLATE first."
  exit 1
fi

if ! command -v railway >/dev/null 2>&1; then
  echo "❌ railway CLI not found. Install from https://docs.railway.app/cli/install"
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

required_vars=(
  SECRET_KEY
  DATABASE_URL
  OPENAI_API_KEY
  ANTHROPIC_API_KEY
  GOOGLE_CLIENT_ID
  GOOGLE_CLIENT_SECRET
  STRIPE_API_KEY
  STRIPE_WEBHOOK_SECRET
)

optional_vars=(
  REDIS_URL
  MINI_RAG_API_KEY
  OTEL_ENABLED
)

echo "Validating required variables..."
for var in "${required_vars[@]}"; do
  if [ -z "${!var:-}" ]; then
    echo "❌ $var is not set in $ENV_FILE"
    exit 1
  fi
done

echo "Pushing required variables to Railway..."
for var in "${required_vars[@]}"; do
  railway variables --set "$var=${!var}"
done

echo "Pushing optional variables (if set)..."
for var in "${optional_vars[@]}"; do
  if [ -n "${!var:-}" ]; then
    railway variables --set "$var=${!var}"
  fi
done

echo "Setting deployment toggles..."
railway variables --set LOCAL_MODE=false
railway variables --set ALLOW_INSECURE_DEFAULTS=false

echo "✅ Railway env updated. Redeploy to apply changes."

