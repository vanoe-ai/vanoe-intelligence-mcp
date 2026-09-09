"""client.get() tests — httpx is monkeypatched, no network touched."""
import httpx
import pytest

from mcp_server import client


@pytest.fixture(autouse=True)
def _api_key(monkeypatch):
    monkeypatch.setenv("VANOE_API_KEY", "sk_live_test")


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("VANOE_API_KEY", raising=False)
    monkeypatch.delenv("INTEL_API_KEY", raising=False)
    with pytest.raises(client.MissingApiKeyError):
        import asyncio
        asyncio.run(client.get("/v1/macro"))


def test_get_success_returns_json(monkeypatch):
    async def fake_get(self, url, params=None, headers=None):
        assert headers["Authorization"] == "Bearer sk_live_test"
        assert url == "https://api.vanoe.ai/v1/macro"
        return httpx.Response(200, json={"data": {"regime": "risk_on"}}, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    import asyncio
    result = asyncio.run(client.get("/v1/macro"))
    assert result == {"data": {"regime": "risk_on"}}


def test_get_uses_custom_base_url(monkeypatch):
    monkeypatch.setenv("VANOE_API_BASE_URL", "https://api.example.com/")

    async def fake_get(self, url, params=None, headers=None):
        assert url == "https://api.example.com/v1/usage"
        return httpx.Response(200, json={}, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    import asyncio
    asyncio.run(client.get("/v1/usage"))


def test_error_response_raises_intel_api_error_with_structured_body(monkeypatch):
    async def fake_get(self, url, params=None, headers=None):
        return httpx.Response(
            402,
            json={"error": {"code": "quota_exceeded", "message": "Monthly quota exceeded.", "request_id": "abc"}},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    import asyncio
    with pytest.raises(client.IntelAPIError) as exc_info:
        asyncio.run(client.get("/v1/macro"))
    assert exc_info.value.status_code == 402
    assert exc_info.value.code == "quota_exceeded"
    assert exc_info.value.message == "Monthly quota exceeded."


def test_error_response_with_unparseable_body_still_raises(monkeypatch):
    async def fake_get(self, url, params=None, headers=None):
        return httpx.Response(500, content=b"not json", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    import asyncio
    with pytest.raises(client.IntelAPIError) as exc_info:
        asyncio.run(client.get("/v1/macro"))
    assert exc_info.value.status_code == 500
    assert exc_info.value.code == "unknown_error"


def test_connection_error_raises_intel_api_error(monkeypatch):
    async def fake_get(self, url, params=None, headers=None):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    import asyncio
    with pytest.raises(client.IntelAPIError) as exc_info:
        asyncio.run(client.get("/v1/macro"))
    assert exc_info.value.code == "connection_error"


def test_legacy_env_names_still_work(monkeypatch):
    monkeypatch.delenv("VANOE_API_KEY", raising=False)
    monkeypatch.setenv("INTEL_API_KEY", "sk_live_legacy")
    monkeypatch.setenv("INTEL_API_BASE_URL", "http://localhost:8000")

    async def fake_get(self, url, params=None, headers=None):
        assert headers["Authorization"] == "Bearer sk_live_legacy"
        assert url == "http://localhost:8000/v1/usage"
        return httpx.Response(200, json={"ok": True}, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    import asyncio
    assert asyncio.run(client.get("/v1/usage")) == {"ok": True}
