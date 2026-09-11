"""Vanoe Market Intelligence MCP server — exposes the API's signals as MCP
tools so any MCP-capable AI assistant (Claude Desktop, Claude Code, etc.) can
call them directly.

This is a thin authenticated client, not a free bypass: every tool call
makes a real, metered call against your plan using your own VANOE_API_KEY,
exactly like calling the REST API yourself.

Setup:
  VANOE_API_KEY       your sk_live_... key (required) — free at https://api.vanoe.ai/signup
  VANOE_API_BASE_URL  defaults to https://api.vanoe.ai; point at a local
                      instance for development

Run: vanoe-intelligence-mcp   (or: python -m mcp_server) — stdio transport,
for Claude Desktop / Claude Code style MCP client configs.

Tools never raise — every failure (missing key, network error, an API
4xx/5xx) is caught and returned as a {"error": {...}} JSON payload in the
tool result, not an exception. This is deliberate: a raised exception from a
tool crashes with UnexpectedToolError rather than being cleanly surfaced to
the caller (confirmed against the installed SDK version), so tools return a
predictable JSON shape either way instead of depending on that behavior.
"""
from __future__ import annotations

import json

from mcp.server.mcpserver import MCPServer

from mcp_server import client

mcp = MCPServer(
    name="vanoe-market-intelligence",
    version="0.1.3",
    instructions=(
        "Vanoe Market Intelligence signals: four-stage trend analysis, Point & "
        "Figure patterns, sector breadth, a composite verdict score, macro "
        "regime, insider filings, and the economic calendar. All output is "
        "informational data only — not financial advice, and not a "
        "recommendation, solicitation, or offer to buy or sell any security."
    ),
)


async def _call(path: str, params: dict | None = None) -> str:
    """GET the API and return the JSON result as a string, or a
    {"error": {...}} JSON string on any failure — tools never raise."""
    try:
        data = await client.get(path, params)
        return json.dumps(data, indent=2)
    except client.MissingApiKeyError as e:
        return json.dumps({"error": {"code": "missing_api_key", "message": str(e)}}, indent=2)
    except client.IntelAPIError as e:
        return json.dumps(
            {"error": {"code": e.code, "message": e.message, "http_status": e.status_code}},
            indent=2,
        )
    except Exception as e:  # last-resort guard — tools must never raise
        return json.dumps({"error": {"code": "mcp_server_error", "message": str(e)}}, indent=2)


@mcp.tool(description="Macro regime (risk_on/neutral/risk_off), rates, inflation, yield curve, positioning.")
async def get_macro() -> str:
    return await _call("/v1/macro")


@mcp.tool(description=(
    "Stage analysis (1=Basing, 2=Advancing, 3=Topping, 4=Declining) "
    "for up to 50 tickers. Pass tickers as a comma-separated string, e.g. "
    "'AAPL,MSFT,NVDA'."
))
async def get_stage(tickers: str) -> str:
    return await _call("/v1/signals/stage", {"tickers": tickers})


@mcp.tool(description=(
    "Historical weekly trend-stage series for one ticker, walk-forward "
    "computed (no lookahead) — the only commercial source of trend "
    "stages as a backtest-safe data series. weeks defaults to 104, max 520."
))
async def get_stage_history(ticker: str, weeks: int = 104) -> str:
    return await _call("/v1/signals/stage/history", {"ticker": ticker, "weeks": weeks})


@mcp.tool(description=(
    "Point & Figure signal, breakout pattern, and relative strength vs SPY, "
    "for up to 50 tickers. Pass tickers as a comma-separated string."
))
async def get_pnf(tickers: str) -> str:
    return await _call("/v1/signals/pnf", {"tickers": tickers})


@mcp.tool(description="Bullish-percent breadth by sector — the % of names in each sector on a Point & Figure buy signal.")
async def get_sector_breadth() -> str:
    return await _call("/v1/sector-breadth")


@mcp.tool(description=(
    "Composite verdict for one ticker: fuses trend stage, Point & "
    "Figure, insider-transaction clusters, and macro regime into a 0-100 "
    "score, an accumulate/hold/distribute/avoid enum, and a plain-English "
    "rationale. One call replaces separately calling stage, pnf, filings, "
    "and macro."
))
async def get_verdict(ticker: str) -> str:
    return await _call(f"/v1/verdict/{ticker}")


@mcp.tool(description="Recent SEC insider transactions (Form 4) and 8-K filings for one ticker.")
async def get_filings(ticker: str) -> str:
    return await _call(f"/v1/filings/{ticker}")


@mcp.tool(description=(
    "FINRA daily short-sale volume for up to 50 tickers: share of volume sold short (latest, "
    "10-day average, trend). Short-sale volume, not short interest; market norm is roughly 40-55%. "
    "Pass tickers as a comma-separated string."
))
async def get_short_volume(tickers: str) -> str:
    return await _call("/v1/signals/short-volume", {"tickers": tickers})


@mcp.tool(description="Upcoming macro events (FOMC, CPI, payrolls) within a look-ahead window in days (default 10, max 60).")
async def get_calendar(within_days: int = 10) -> str:
    return await _call("/v1/calendar", {"within_days": within_days})


@mcp.tool(description="Your current billing-period usage and remaining credit quota on your plan. Free — never counts against quota.")
async def get_usage() -> str:
    return await _call("/v1/usage")


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
