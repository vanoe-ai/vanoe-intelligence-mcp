"""MCP tool tests — call tools in-process via mcp.call_tool(), with
mcp_server.client.get monkeypatched (no network, no real MCP transport).
Tools must never raise (see server.py's docstring) — every failure path
asserts a clean {"error": {...}} JSON text result instead of an exception.
"""
import asyncio
import json

import pytest

from mcp_server import client, server


def _call(name: str, args: dict) -> dict:
    result = asyncio.run(server.mcp.call_tool(name, args))
    assert result.is_error is False  # tools never raise -> is_error is always False
    return json.loads(result.content[0].text)


def test_get_macro_passes_through_path(monkeypatch):
    async def fake_get(path, params=None):
        assert path == "/v1/macro"
        assert params is None
        return {"data": {"regime": "risk_on"}}

    monkeypatch.setattr(client, "get", fake_get)
    assert _call("get_macro", {}) == {"data": {"regime": "risk_on"}}


def test_get_stage_passes_tickers_param(monkeypatch):
    async def fake_get(path, params=None):
        assert path == "/v1/signals/stage"
        assert params == {"tickers": "AAPL,MSFT"}
        return {"data": {"AAPL": {"stage": 2}}}

    monkeypatch.setattr(client, "get", fake_get)
    result = _call("get_stage", {"tickers": "AAPL,MSFT"})
    assert result["data"]["AAPL"]["stage"] == 2


def test_get_stage_history_default_weeks(monkeypatch):
    async def fake_get(path, params=None):
        assert path == "/v1/signals/stage/history"
        assert params == {"ticker": "AAPL", "weeks": 104}
        return {"data": {}}

    monkeypatch.setattr(client, "get", fake_get)
    _call("get_stage_history", {"ticker": "AAPL"})


def test_get_verdict_builds_path_with_ticker(monkeypatch):
    async def fake_get(path, params=None):
        assert path == "/v1/verdict/AAPL"
        return {"data": {"verdict": "accumulate"}}

    monkeypatch.setattr(client, "get", fake_get)
    assert _call("get_verdict", {"ticker": "AAPL"})["data"]["verdict"] == "accumulate"


def test_get_calendar_default_within_days(monkeypatch):
    async def fake_get(path, params=None):
        assert params == {"within_days": 10}
        return {"data": []}

    monkeypatch.setattr(client, "get", fake_get)
    _call("get_calendar", {})


def test_missing_api_key_returns_error_json_not_exception(monkeypatch):
    async def fake_get(path, params=None):
        raise client.MissingApiKeyError()

    monkeypatch.setattr(client, "get", fake_get)
    result = _call("get_usage", {})
    assert result["error"]["code"] == "missing_api_key"


def test_intel_api_error_returns_structured_error_json(monkeypatch):
    async def fake_get(path, params=None):
        raise client.IntelAPIError(402, "quota_exceeded", "Monthly quota exceeded.")

    monkeypatch.setattr(client, "get", fake_get)
    result = _call("get_macro", {})
    assert result["error"] == {
        "code": "quota_exceeded",
        "message": "Monthly quota exceeded.",
        "http_status": 402,
    }


def test_unexpected_exception_still_returns_error_json_not_raise(monkeypatch):
    async def fake_get(path, params=None):
        raise ValueError("something unrelated broke")

    monkeypatch.setattr(client, "get", fake_get)
    result = _call("get_macro", {})
    assert result["error"]["code"] == "mcp_server_error"


def test_all_ten_tools_are_registered():
    expected = {
        "get_macro", "get_stage", "get_stage_history", "get_pnf",
        "get_sector_breadth", "get_verdict", "get_filings", "get_calendar",
        "get_usage", "get_short_volume",
    }
    tools = asyncio.run(server.mcp.list_tools())
    names = {t.name for t in tools}
    assert expected <= names
