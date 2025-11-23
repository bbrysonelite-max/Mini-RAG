"""
Integration tests for Stripe billing webhook processing.
Tests the full lifecycle of subscription events.
"""

import pytest
import json
import hmac
import hashlib
import time
from fastapi.testclient import TestClient


def generate_stripe_signature(payload: str, secret: str) -> str:
    """Generate a valid Stripe webhook signature."""
    timestamp = str(int(time.time()))
    signed_payload = f"{timestamp}.{payload}"
    signature = hmac.new(
        secret.encode(),
        signed_payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"t={timestamp},v1={signature}"


@pytest.fixture
def webhook_secret():
    """Test webhook secret."""
    return "whsec_test_secret_12345"


@pytest.fixture
def client(webhook_secret, monkeypatch):
    """Create test client with webhook secret configured."""
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", webhook_secret)
    monkeypatch.setenv("STRIPE_API_KEY", "sk_test_fake")
    monkeypatch.setenv("ALLOW_INSECURE_DEFAULTS", "true")
    
    from server import app
    return TestClient(app)


def test_checkout_completed_webhook(client, webhook_secret):
    """Test checkout.session.completed event processing."""
    event_data = {
        "id": "evt_test_123",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_123",
                "customer": "cus_test_123",
                "subscription": "sub_test_123",
                "metadata": {
                    "organization_id": "org-test-uuid"
                }
            }
        }
    }
    
    payload = json.dumps(event_data)
    signature = generate_stripe_signature(payload, webhook_secret)
    
    response = client.post(
        "/api/v1/billing/webhook",
        data=payload,
        headers={
            "Stripe-Signature": signature,
            "Content-Type": "application/json"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["received"] == True


def test_subscription_updated_webhook(client, webhook_secret):
    """Test customer.subscription.updated event."""
    event_data = {
        "id": "evt_test_456",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_test_123",
                "customer": "cus_test_123",
                "status": "active",
                "current_period_end": 1735689600  # Future timestamp
            }
        }
    }
    
    payload = json.dumps(event_data)
    signature = generate_stripe_signature(payload, webhook_secret)
    
    response = client.post(
        "/api/v1/billing/webhook",
        data=payload,
        headers={
            "Stripe-Signature": signature,
            "Content-Type": "application/json"
        }
    )
    
    assert response.status_code == 200


def test_subscription_deleted_webhook(client, webhook_secret):
    """Test customer.subscription.deleted event (cancellation)."""
    event_data = {
        "id": "evt_test_789",
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_test_123",
                "customer": "cus_test_123",
                "status": "canceled"
            }
        }
    }
    
    payload = json.dumps(event_data)
    signature = generate_stripe_signature(payload, webhook_secret)
    
    response = client.post(
        "/api/v1/billing/webhook",
        data=payload,
        headers={
            "Stripe-Signature": signature,
            "Content-Type": "application/json"
        }
    )
    
    assert response.status_code == 200


def test_invoice_payment_failed_webhook(client, webhook_secret):
    """Test invoice.payment_failed event."""
    event_data = {
        "id": "evt_test_999",
        "type": "invoice.payment_failed",
        "data": {
            "object": {
                "id": "in_test_123",
                "customer": "cus_test_123",
                "subscription": "sub_test_123",
                "status": "open",
                "amount_due": 2999
            }
        }
    }
    
    payload = json.dumps(event_data)
    signature = generate_stripe_signature(payload, webhook_secret)
    
    response = client.post(
        "/api/v1/billing/webhook",
        data=payload,
        headers={
            "Stripe-Signature": signature,
            "Content-Type": "application/json"
        }
    )
    
    assert response.status_code == 200


def test_webhook_invalid_signature(client, webhook_secret):
    """Test webhook with invalid signature is rejected."""
    event_data = {"id": "evt_test", "type": "test"}
    payload = json.dumps(event_data)
    
    # Invalid signature
    invalid_signature = "t=123,v1=invalid"
    
    response = client.post(
        "/api/v1/billing/webhook",
        data=payload,
        headers={
            "Stripe-Signature": invalid_signature,
            "Content-Type": "application/json"
        }
    )
    
    # Should reject
    assert response.status_code in [400, 401, 403]


def test_webhook_missing_signature(client):
    """Test webhook without signature is rejected."""
    event_data = {"id": "evt_test", "type": "test"}
    payload = json.dumps(event_data)
    
    response = client.post(
        "/api/v1/billing/webhook",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    
    assert response.status_code in [400, 401, 403]


def test_webhook_duplicate_event_idempotency(client, webhook_secret):
    """Test that duplicate events are handled idempotently."""
    event_data = {
        "id": "evt_idempotent_123",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_idem",
                "customer": "cus_test_idem",
                "metadata": {"organization_id": "org-idem"}
            }
        }
    }
    
    payload = json.dumps(event_data)
    signature = generate_stripe_signature(payload, webhook_secret)
    
    # Send same event twice
    response1 = client.post(
        "/api/v1/billing/webhook",
        data=payload,
        headers={
            "Stripe-Signature": signature,
            "Content-Type": "application/json"
        }
    )
    
    # Wait a moment
    time.sleep(0.1)
    
    # Regenerate signature (Stripe would send new timestamp)
    signature2 = generate_stripe_signature(payload, webhook_secret)
    
    response2 = client.post(
        "/api/v1/billing/webhook",
        data=payload,
        headers={
            "Stripe-Signature": signature2,
            "Content-Type": "application/json"
        }
    )
    
    # Both should succeed (idempotent)
    assert response1.status_code == 200
    assert response2.status_code == 200


def test_webhook_legacy_endpoint_alias(client, webhook_secret):
    """Test that legacy /api/billing/webhook still works."""
    event_data = {
        "id": "evt_legacy_123",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_legacy",
                "customer": "cus_legacy",
                "metadata": {"organization_id": "org-legacy"}
            }
        }
    }
    
    payload = json.dumps(event_data)
    signature = generate_stripe_signature(payload, webhook_secret)
    
    # Test legacy endpoint
    response = client.post(
        "/api/billing/webhook",
        data=payload,
        headers={
            "Stripe-Signature": signature,
            "Content-Type": "application/json"
        }
    )
    
    assert response.status_code == 200


@pytest.mark.skipif(
    not pytest.config.getoption("--integration", default=False),
    reason="Requires --integration flag for real Stripe test mode"
)
def test_real_stripe_webhook(client):
    """
    Test against real Stripe test mode.
    Run with: pytest test_billing_webhooks.py --integration
    
    Prerequisites:
    - STRIPE_API_KEY set to real sk_test_* key
    - Stripe CLI running: stripe listen --forward-to localhost:8000/api/v1/billing/webhook
    """
    # This is a placeholder for manual testing
    # In practice, you'd trigger a real event via Stripe CLI:
    # stripe trigger checkout.session.completed
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

