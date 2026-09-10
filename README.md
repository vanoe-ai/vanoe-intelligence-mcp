# Vanoe Market Intelligence MCP server

<!-- mcp-name: io.github.vanoe-ai/vanoe-intelligence-mcp -->

Exposes the [Vanoe Market Intelligence API](https://api.vanoe.ai) as tools any
MCP-capable AI assistant (Claude Desktop, Claude Code, Cursor, etc.) can call
directly: a composite 0–100 verdict per ticker, trend-stage analysis (current
and a backtest-safe weekly history), Point & Figure signals, sector breadth,
the macro risk regime, SEC insider and 8-K filings, the macro calendar, and
your usage.

This is a thin authenticated client, not a free tier: every tool call is a
real, metered call against your plan using your own API key, exactly like
calling the REST API yourself. Get a free key (1,000 credits a month, no card)
at https://api.vanoe.ai/signup.

> Informational data only. Not financial advice. See https://api.vanoe.ai/terms.

## Hosted endpoint (no install)

The same tools are served over MCP's streamable HTTP transport by the API
itself, for clients that take a URL (Claude.ai custom connectors, ChatGPT,
hosted agent platforms):

- `https://api.vanoe.ai/mcp` with `Authorization: Bearer <your key>`, or
- `https://api.vanoe.ai/mcp/k/<your key>` for clients that cannot send headers
  (the key page after signup prints this URL; treat it like a password).

Stateless, JSON responses, metered exactly like the REST API. Use the package
below when you want the server to run on your own machine.

## Install

No install step is needed with [uv](https://docs.astral.sh/uv/) — `uvx` fetches
and runs the package on demand:

```
uvx vanoe-intelligence-mcp
```

Or install it permanently with `pipx install vanoe-intelligence-mcp` or
`pip install vanoe-intelligence-mcp`, which puts a `vanoe-intelligence-mcp`
command on your PATH.

## Configure your MCP client

Set one environment variable, `VANOE_API_KEY`. `VANOE_API_BASE_URL` is optional
and defaults to `https://api.vanoe.ai`.

**Claude Desktop** (`claude_desktop_config.json`) and most other clients:

```json
{
  "mcpServers": {
    "vanoe": {
      "command": "uvx",
      "args": ["vanoe-intelligence-mcp"],
      "env": { "VANOE_API_KEY": "sk_live_your_key_here" }
    }
  }
}
```

**Claude Code**:

```
claude mcp add vanoe -e VANOE_API_KEY=sk_live_your_key_here -- uvx vanoe-intelligence-mcp
```

Then ask your assistant things like *"What's the verdict on NVDA and why?"*,
*"Which stage are AAPL, MSFT and AMD in?"*, or *"Is the macro regime risk-on
right now?"* — it will call the tools below.

## Tools

| Tool | API call | Credits |
|---|---|---|
| `get_verdict(ticker)` | `GET /v1/verdict/{ticker}` | 5 |
| `get_stage(tickers)` | `GET /v1/signals/stage` | 1 per ticker |
| `get_stage_history(ticker, weeks)` | `GET /v1/signals/stage/history` | 5 |
| `get_pnf(tickers)` | `GET /v1/signals/pnf` | 1 per ticker |
| `get_sector_breadth()` | `GET /v1/sector-breadth` | 1 |
| `get_macro()` | `GET /v1/macro` | 1 |
| `get_filings(ticker)` | `GET /v1/filings/{ticker}` | 1 |
| `get_calendar()` | `GET /v1/calendar` | 1 |
| `get_usage()` | `GET /v1/usage` | 0 |

Tools never raise. Any failure — missing key, network error, quota exceeded,
an unknown ticker — comes back as `{"error": {"code", "message",
"http_status"}}` carrying the API's own message, so the assistant can explain
what happened instead of crashing the call.

Webhook management is deliberately not exposed: it is account administration,
not something to do mid-conversation. Use the REST API for that.

## Development

```
git clone https://github.com/vanoe-ai/vanoe-intelligence-mcp.git
cd vanoe-intelligence-mcp
python -m venv .venv && . .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e '.[test]'
pytest tests
VANOE_API_BASE_URL=http://localhost:8000 VANOE_API_KEY=sk_live_… vanoe-intelligence-mcp
```

Source lives at https://github.com/vanoe-ai/vanoe-intelligence-mcp; issues and
pull requests welcome. If you also run the API server locally, install this
in its own virtualenv, separate from the API server's own
`requirements.txt`: the `mcp` SDK pulls in a newer `starlette` than the API's
FastAPI pin tolerates, and sharing one environment breaks the API server with
`Router.__init__() got an unexpected keyword argument 'on_startup'`. End users
never hit this (the MCP server runs on their machine, next to their assistant).

`tests/manual_e2e_smoke.py` runs the real server as a subprocess over stdio
against a reachable API with a real key; it is not part of `pytest`.

The MCP Python SDK is on v2: the server class is
`mcp.server.mcpserver.MCPServer` (older tutorials show `FastMCP` at a
different import path).

## Releasing

```
python -m build
twine upload dist/*
```

Bump `version` in `pyproject.toml` first. The older `INTEL_API_KEY` /
`INTEL_API_BASE_URL` variable names are still accepted for compatibility.
