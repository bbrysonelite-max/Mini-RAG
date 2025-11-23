# CI/CD Setup Guide

This document summarizes how the GitHub Actions pipeline is structured and what secrets are required.

## Workflow Overview (`.github/workflows/ci.yml`)

Jobs:
1. **backend**
   - Installs Python 3.9, pip dependencies from `requirements.txt`.
   - Runs a targeted pytest suite (`test_quota_service.py`, `test_api_key_auth.py`, `test_billing_guard.py`, `tests/test_api_contract.py`).
   - Uses placeholder env vars for `DATABASE_URL`, `STRIPE_API_KEY`, `STRIPE_WEBHOOK_SECRET`. For full integration you can add a Postgres service or point to a managed instance.

2. **frontend**
   - Installs Node 20, runs `npm ci` and `npm run build` inside `frontend-react/`.
   - Replace the directory if the React app lands elsewhere.

## Required Secrets (future)

| Secret | Purpose |
|--------|---------|
| `DATABASE_URL` (optional) | Real database for integration tests when needed. |
| `STRIPE_API_KEY` | Required if end-to-end billing tests are added. |
| `STRIPE_WEBHOOK_SECRET` | Validates Stripe webhook signatures in CI. |
| `REGISTRY_TOKEN` (optional) | Needed once container publishing is added. |

For now the workflow uses placeholder values so it can run without additional configuration. Update the env section or use GitHub secrets once we connect to real services.

## Next Steps
- Add Docker build & push stage (leverage `Dockerfile` / `docker-compose.yml`).
- Introduce Postgres service container for full integration tests.
- Publish React build artifacts (e.g., to S3) after successful builds.

