import pytest
from fastapi import HTTPException
from starlette.requests import Request

from api_key_auth import APIKeyAuth, APIKeyPrincipal, configure_api_key_auth, get_api_key_principal


class FakeApiKeyService:
    def __init__(self, record=None, error=None, touch_error=None):
        self.record = record
        self.error = error
        self.touched = None
        self.last_verified = None
        self.touch_error = touch_error

    async def verify_api_key(self, api_key: str):
        self.last_verified = api_key
        if self.error:
            raise self.error
        return self.record

    async def touch_last_used(self, key_id: str):
        if self.touch_error:
            raise self.touch_error
        self.touched = key_id


def build_request(headers: dict) -> Request:
    scope = {
        "type": "http",
        "headers": [(k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in headers.items()],
        "method": "GET",
        "path": "/",
        "query_string": b"",
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_get_api_key_principal_returns_none_when_not_configured():
    configure_api_key_auth(None)
    request = build_request({})
    result = await get_api_key_principal(request, required=False)
    assert result is None


@pytest.mark.asyncio
async def test_get_api_key_principal_success(monkeypatch):
    service = FakeApiKeyService(
        record={
            "id": "key-id",
            "user_id": "user-id",
            "workspace_id": "workspace-id",
            "scopes": ["read", "write"],
            "description": "CI token",
        }
    )
    configure_api_key_auth(service)
    request = build_request({"X-API-Key": "plaintext"})

    principal = await get_api_key_principal(request, scopes=("read",))

    assert isinstance(principal, APIKeyPrincipal)
    assert principal.key_id == "key-id"
    assert principal.user_id == "user-id"
    assert principal.workspace_id == "workspace-id"
    assert "read" in principal.scopes
    assert service.touched == "key-id"


@pytest.mark.asyncio
async def test_get_api_key_principal_authorization_header():
    service = FakeApiKeyService(
        record={
            "id": "key-2",
            "user_id": "user-2",
            "workspace_id": None,
            "scopes": ["admin"],
        }
    )
    configure_api_key_auth(service)
    request = build_request({"Authorization": "ApiKey plaintext"})

    principal = await get_api_key_principal(request, scopes=("admin",))
    assert principal.key_id == "key-2"


@pytest.mark.asyncio
async def test_get_api_key_principal_prefers_x_api_key_header():
    service = FakeApiKeyService(
        record={
            "id": "key-4",
            "user_id": "user-4",
            "workspace_id": None,
            "scopes": ["read"],
        }
    )
    configure_api_key_auth(service)
    request = build_request(
        {
            "X-API-Key": "from-x-header",
            "Authorization": "ApiKey from-authorization",
        }
    )

    principal = await get_api_key_principal(request, scopes=("read",))

    assert principal.key_id == "key-4"
    assert service.last_verified == "from-x-header"


@pytest.mark.asyncio
async def test_get_api_key_principal_missing_scope_raises():
    service = FakeApiKeyService(
        record={
            "id": "key-3",
            "user_id": "user-3",
            "workspace_id": None,
            "scopes": ["read"],
        }
    )
    configure_api_key_auth(service)
    request = build_request({"X-API-Key": "plaintext"})

    with pytest.raises(HTTPException) as exc:
        await get_api_key_principal(request, scopes=("write",))

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_get_api_key_principal_invalid_key_raises():
    service = FakeApiKeyService(record=None)
    configure_api_key_auth(service)
    request = build_request({"X-API-Key": "plaintext"})

    with pytest.raises(HTTPException) as exc:
        await get_api_key_principal(request, required=True)

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_api_key_principal_touch_last_used_failures_are_ignored():
    service = FakeApiKeyService(
        record={
            "id": "key-5",
            "user_id": "user-5",
            "workspace_id": None,
            "scopes": ["read"],
        },
        touch_error=RuntimeError("db unavailable"),
    )
    configure_api_key_auth(service)
    request = build_request({"X-API-Key": "plaintext"})

    principal = await get_api_key_principal(request, scopes=("read",))

    assert principal.key_id == "key-5"
    assert service.touched is None


@pytest.mark.asyncio
async def test_api_key_auth_dependency_required_scope():
    service = FakeApiKeyService(
        record={
            "id": "key-6",
            "user_id": "user-6",
            "workspace_id": "workspace-6",
            "scopes": ["write"],
        }
    )
    configure_api_key_auth(service)
    dependency = APIKeyAuth(scopes=("write",), required=True)
    request = build_request({"X-API-Key": "plaintext"})

    principal = await dependency(request)

    assert isinstance(principal, APIKeyPrincipal)
    assert principal.workspace_id == "workspace-6"


@pytest.mark.asyncio
async def test_api_key_auth_dependency_optional_allows_missing_key():
    service = FakeApiKeyService(
        record={
            "id": "key-7",
            "user_id": "user-7",
            "workspace_id": None,
            "scopes": ["read"],
        }
    )
    configure_api_key_auth(service)
    dependency = APIKeyAuth(scopes=("read",), required=False)
    request = build_request({})

    principal = await dependency(request)

    assert principal is None


@pytest.fixture(autouse=True)
def reset_service():
    # Ensure each test runs with clean configuration.
    configure_api_key_auth(None)
    yield
    configure_api_key_auth(None)

