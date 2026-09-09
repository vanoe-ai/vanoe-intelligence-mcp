"""Thin HTTP client for the Vanoe Market Intelligence API — one function per
/v1 GET endpoint.

Auth: Authorization: Bearer <VANOE_API_KEY>. Base URL: VANOE_API_BASE_URL
(defaults to https://api.vanoe.ai; point it at a local instance for dev).
The older INTEL_API_KEY / INTEL_API_BASE_URL names are still honoured.

On any non-2xx response, raises IntelAPIError carrying the API's own
structured {"error": {code, message, request_id}} body when present, so a
tool caller sees the SAME message a developer would get calling the API
directly (e.g. "Monthly quota exceeded..."), not a raw HTTP status.
"""
from __future__ import annotations

import os

import httpx

DEFAULT_BASE_URL = "https://api.vanoe.ai"
SIGNUP_URL = "https://api.vanoe.ai/signup"
_TIMEOUT_SECONDS = 20


class IntelAPIError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(f"{message} (code={code}, http_status={status_code})")


class MissingApiKeyError(Exception):
    def __init__(self):
        super().__init__(
            f"VANOE_API_KEY is not set. Get a free key at {SIGNUP_URL} and set the "
            "VANOE_API_KEY environment variable before starting this MCP server."
        )


def _env(new: str, old: str) -> str | None:
    return os.environ.get(new) or os.environ.get(old)


def _base_url() -> str:
    return (_env("VANOE_API_BASE_URL", "INTEL_API_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")


def _headers() -> dict:
    key = _env("VANOE_API_KEY", "INTEL_API_KEY")
    if not key:
        raise MissingApiKeyError()
    return {"Authorization": f"Bearer {key}"}


async def get(path: str, params: dict | None = None) -> dict:
    url = f"{_base_url()}{path}"
    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as http:
        try:
            r = await http.get(url, params=params, headers=_headers())
        except httpx.RequestError as e:
            raise IntelAPIError(0, "connection_error",
                                f"Could not reach the API at {_base_url()}: {e}") from e

    if r.status_code >= 400:
        try:
            body = r.json()
            err = body.get("error", {})
            raise IntelAPIError(r.status_code, err.get("code", "unknown_error"),
                                err.get("message", r.text))
        except ValueError:
            raise IntelAPIError(r.status_code, "unknown_error", r.text)
    return r.json()
