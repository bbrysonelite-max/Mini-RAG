# Mini-RAG Billing & API Onboarding

This guide explains how to configure Stripe, understand the new billing endpoints, and exercise the multi-tenant API safely in lower environments.

---

## 1. Stripe Configuration Checklist

1. **Create a Stripe account** (test mode is fine for local/dev).
2. **Products & Prices**
   - Create at least one recurring product (e.g., “Mini-RAG Pro”).
   - Under the product, create a price (monthly) and note its `price_xxx` identifier.
3. **API Keys & Webhooks**
   - Generate a restricted **secret key** for server-side calls (Test mode: `sk_test_*`).
   - In the Stripe dashboard, create a webhook endpoint pointing to your public tunnel (e.g., `https://your-ngrok-host/api/v1/billing/webhook`; the legacy `/api/billing/webhook` alias still works).
   - Subscribe to these events:
     - `checkout.session.completed`
     - `customer.subscription.created`
     - `customer.subscription.updated`
     - `customer.subscription.deleted`
     - `invoice.payment_failed`
   - Capture the **webhook signing secret** (`whsec_*`).
4. **Environment Variables**

| Variable | Purpose |
|----------|---------|
| `STRIPE_API_KEY` | Secret API key used by the server. |
| `STRIPE_PRICE_ID` | Default price for checkout sessions. |
| `STRIPE_WEBHOOK_SECRET` | Verifies incoming webhook signatures. |
| `STRIPE_SUCCESS_URL` | Redirect after successful checkout. |
| `STRIPE_CANCEL_URL` | Redirect when the user cancels checkout. |
| `STRIPE_PORTAL_RETURN_URL` | Destination after managing billing in the portal. |

> Tip: add these to `.env.local` (ignored by git) and restart the server.

---

## 2. Billing Workflow Overview

1. **Admin requests checkout**
   - Endpoint: `POST /api/v1/billing/checkout` (legacy alias: `/api/billing/checkout`)
   - Requires JWT/API key with admin scope.
   - Returns a Stripe Checkout URL; redirect the browser to complete payment.
2. **Stripe webhook fires**
   - `/api/v1/billing/webhook` validates the signature and stores the raw payload in `organization_billing_events`. The server also exposes `/api/billing/webhook` for backward compatibility.
   - `organizations.billing_status`, `stripe_customer_id`, `stripe_subscription_id`, `trial_ends_at`, and `subscription_expires_at` are updated automatically.
3. **Ingestion gating**
   - `/api/ingest_urls` and `/api/ingest_files` call `_require_billing_active`.
   - Allowed states:
     - `trialing` (before `trial_ends_at`)
     - `active` (before `subscription_expires_at`)
   - Disallowed states return HTTP 402 with a descriptive message and structured `billing.blocked` log events.
4. **Billing portal**
   - Endpoint: `POST /api/v1/billing/portal` (legacy alias: `/api/billing/portal`)
   - Returns a portal URL where admins can update payment methods or cancel.

---

## 3. API Endpoint Reference

| Endpoint | Method | Description | Auth Scope |
|----------|--------|-------------|------------|
| `/api/v1/billing/checkout` | POST | Create a Stripe Checkout session. | Admin |
| `/api/v1/billing/portal` | POST | Create a Billing Portal session. | Admin |
| `/api/v1/billing/webhook` | POST | Stripe webhook receiver (no auth, signature verified). | — |
| `/api/v1/admin/workspaces` | GET | List workspaces + org billing status. | Admin |
| `/api/v1/admin/billing` | GET | List organization billing snapshots. | Admin |
| `/api/v1/admin/billing/{org_id}` | PATCH | Override plan/billing status, trial, or expiry dates. | Admin |
| `/api/v1/ask` | POST | Multi-tenant QA endpoint (respects workspace id). | Read |
| `/api/v1/ingest/urls` | POST | Ingest YouTube/transcript URLs (billing + quota enforced). | Write |
| `/api/v1/ingest/files` | POST | Upload and ingest documents (billing + quota enforced). | Write |
| `/api/v1/sources` | GET/POST | Manage indexed sources (write requires billing). | Read/Write |

> Legacy `/api/*` routes remain for backward compatibility but `/api/v1/*` is the forward-compatible surface.

---

## 4. Sample Requests

### 4.1 Create Checkout Session

```bash
curl -X POST https://localhost:8000/api/v1/billing/checkout \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"price_id":"price_123","success_url":"https://app/success","cancel_url":"https://app/cancel"}'
```

Response:

```json
{
  "id": "cs_test_a1b2c3",
  "url": "https://checkout.stripe.com/c/pay/cs_test_a1b2c3"
}
```

### 4.2 Webhook Verification (Local)

Use the Stripe CLI:

```bash
stripe login
stripe listen --forward-to localhost:8000/api/v1/billing/webhook
```

This automatically sets `STRIPE_WEBHOOK_SECRET` in the CLI output.

### 4.3 Ingestion Block Example

When a workspace is `past_due`, ingest endpoints return:

```json
{
  "detail": "Workspace billing status 'past_due' does not permit ingestion."
}
```

The server simultaneously logs `billing.blocked` with `workspace_id`, `reason`, and user context for alerting.

---

## 5. Postman & SDK Notes

- **Postman**: Import `docs/postman/mini-rag.postman_collection.json` (generated via `npm i -g postman-collection-transformer && ./scripts/export_postman.sh` once the script lands).
- **Python SDK**: The `clients/sdk.py` module wraps `/ask`, ingest, and billing flows with automatic API key injection and retries – see the README section bundled with the SDK.

---

## 6. Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `HTTP 503` on billing endpoints | `STRIPE_API_KEY` not set or invalid | Double-check `.env.local` and restart. |
| `HTTP 400 invalid signature` on webhook | Mismatched `STRIPE_WEBHOOK_SECRET` | Update env var to match Stripe CLI/dashboard. |
| Ingestion blocked despite active subscription | Clock skew or missing webhook events | Re-send the latest subscription event from Stripe dashboard and verify timestamps. |
| Duplicate events in DB | Stripe retries are normal; `organization_billing_events` enforces uniqueness on `event_id`. |

---

With billing, quotas, and authenticated APIs combined, Mini-RAG is ready for enterprise pilots. Share this doc with customer success / ops teams so they can spin up tenants confidently.**

