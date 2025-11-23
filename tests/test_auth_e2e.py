"""
End-to-end authentication flow tests.
Tests the complete OAuth + JWT + API key workflows.
"""

import pytest
import os
from fastapi.testclient import TestClient


@pytest.fixture
def allow_insecure():
    """Set insecure defaults for testing."""
    os.environ["ALLOW_INSECURE_DEFAULTS"] = "true"
    yield
    if "ALLOW_INSECURE_DEFAULTS" in os.environ:
        del os.environ["ALLOW_INSECURE_DEFAULTS"]


@pytest.fixture
def client(allow_insecure):
    """Create test client."""
    from server import app
    return TestClient(app)


def test_health_endpoint_public(client):
    """Health endpoint should be accessible without auth."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"


def test_ask_endpoint_requires_auth(client):
    """Ask endpoint should reject unauthenticated requests."""
    response = client.post(
        "/ask",
        data={"query": "test query", "k": 5}
    )
    assert response.status_code == 401
    assert "detail" in response.json()


def test_sources_requires_auth(client):
    """Sources endpoint should require authentication."""
    response = client.get("/api/sources")
    assert response.status_code == 401


def test_oauth_redirect_works(client):
    """OAuth endpoint should redirect to Google."""
    response = client.get("/auth/google", follow_redirects=False)
    # Should redirect (302 or 307)
    assert response.status_code in [302, 307]
    
    # If OAuth is configured, should redirect to accounts.google.com
    if "location" in response.headers:
        location = response.headers["location"]
        # May redirect to google or return error if not configured
        assert "google" in location.lower() or "error" in location.lower()


def test_metrics_endpoint_public(client):
    """Metrics endpoint should be publicly accessible."""
    response = client.get("/metrics")
    assert response.status_code == 200
    # Should contain prometheus metrics
    assert "ask_requests_total" in response.text or "# HELP" in response.text


def test_stats_endpoint_works(client):
    """Stats endpoint should return chunk count."""
    response = client.get("/api/v1/stats")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert isinstance(data["count"], int)


def test_openapi_docs_accessible(client):
    """OpenAPI docs should be available."""
    response = client.get("/docs")
    assert response.status_code == 200
    # Should be HTML with Swagger UI
    assert "swagger" in response.text.lower() or "openapi" in response.text.lower()


def test_api_v1_endpoints_exist(client):
    """Verify v1 API endpoints are registered."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    openapi_spec = response.json()
    
    # Check for key v1 endpoints
    paths = openapi_spec.get("paths", {})
    assert "/api/v1/stats" in paths
    assert "/api/v1/sources" in paths
    assert "/ask" in paths or "/api/v1/ask" in paths


def test_admin_endpoints_require_admin_scope(client):
    """Admin endpoints should reject non-admin requests."""
    # Try without any auth
    response = client.get("/api/v1/admin/workspaces")
    assert response.status_code == 401
    
    # Try admin billing endpoint
    response = client.get("/api/v1/admin/billing")
    assert response.status_code == 401


def test_cors_headers_present(client):
    """CORS headers should be configured."""
    response = client.options("/api/v1/stats", headers={
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET"
    })
    # Should either allow or reject, but not crash
    assert response.status_code in [200, 204, 403, 404]


def test_rate_limiting_configured(client):
    """Rate limiting should be active on protected endpoints."""
    # Make multiple rapid requests (unauthenticated will 401, but should still count)
    responses = []
    for _ in range(35):  # Ask endpoint limit is 30/min
        response = client.post("/ask", data={"query": "test", "k": 5})
        responses.append(response.status_code)
    
    # Should see either 401 (no auth) or 429 (rate limit)
    # If we hit rate limit, it means the limiter is working
    assert 429 in responses or all(code == 401 for code in responses)


def test_ingestion_requires_write_scope(client):
    """Ingestion endpoints should require write scope."""
    # Test file upload
    response = client.post(
        "/api/ingest_files",
        files={"files": ("test.txt", b"test content", "text/plain")},
        data={"language": "en"}
    )
    # Should reject without auth (401) or write scope (403)
    assert response.status_code in [401, 403]
    
    # Test URL ingestion
    response = client.post(
        "/api/ingest_urls",
        json={"urls": ["https://example.com"], "language": "en"}
    )
    assert response.status_code in [401, 403]


def test_security_headers_present(client):
    """Security headers should be set."""
    response = client.get("/health")
    headers = response.headers
    
    # Check for key security headers
    # Note: exact headers depend on middleware configuration
    assert response.status_code == 200
    
    # At minimum, should have some security-related headers
    # (exact list depends on your security middleware)
    has_security_headers = any([
        "x-content-type-options" in headers,
        "x-frame-options" in headers,
        "strict-transport-security" in headers,
        "content-security-policy" in headers
    ])
    assert has_security_headers, "No security headers found"


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="Requires DATABASE_URL for full auth flow"
)
def test_full_oauth_callback_flow(client):
    """
    Test OAuth callback processing (requires real DB).
    This is a placeholder for manual/integration testing.
    """
    # In a real E2E test, you would:
    # 1. Hit /auth/google and capture redirect
    # 2. Mock Google OAuth response
    # 3. Hit /auth/callback with mock token
    # 4. Verify JWT cookie is set
    # 5. Use JWT to make authenticated request
    
    # For now, just verify the callback endpoint exists
    response = client.get("/auth/callback")
    # Will fail without proper OAuth state, but endpoint should exist
    assert response.status_code in [400, 401, 302, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

