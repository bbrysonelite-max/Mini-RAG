from fastapi.testclient import TestClient

import server


def test_ask_endpoint_requires_auth():
    with TestClient(server.app) as client:
        response = client.post("/api/v1/ask", data={"query": "hello", "k": 1})
        assert response.status_code == 401


def test_ingest_urls_requires_auth_and_forms():
    with TestClient(server.app) as client:
        response = client.post("/api/v1/ingest/urls", data={"urls": "https://example.com"})
        assert response.status_code in {401, 422}


def test_billing_webhook_without_configuration():
    original_service = server.BILLING_SERVICE
    original_key = server.STRIPE_API_KEY
    server.BILLING_SERVICE = None
    server.STRIPE_API_KEY = None
    try:
        with TestClient(server.app) as client:
            response = client.post("/api/billing/webhook", data=b"{}", headers={"Stripe-Signature": "test"})
            assert response.status_code == 503
    finally:
        server.BILLING_SERVICE = original_service
        server.STRIPE_API_KEY = original_key

