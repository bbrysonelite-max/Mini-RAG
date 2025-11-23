from fastapi.testclient import TestClient

import server


def test_security_headers_present():
    with TestClient(server.app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        headers = resp.headers
        assert headers["strict-transport-security"].startswith("max-age=")
        assert headers["x-content-type-options"] == "nosniff"
        assert headers["x-frame-options"] == "DENY"
        assert headers["referrer-policy"] == "no-referrer"
        assert headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"
        assert headers["x-xss-protection"] == "1; mode=block"
        assert headers["cache-control"] == "no-store"
        assert headers["pragma"] == "no-cache"
        csp = headers["content-security-policy"]
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "object-src 'none'" in csp
