"""Real end-to-end smoke test: spawns mcp_server as an actual subprocess over
real stdio (not the in-process call_tool() shortcut the pytest suite uses),
against a real running intel-api instance. Not part of the pytest suite —
run manually, needs a reachable intel-api (INTEL_API_BASE_URL) and a real key
(INTEL_API_KEY) already set in the environment.

    python mcp_server/tests/manual_e2e_smoke.py
"""
import asyncio
import os
import sys

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def main() -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_server"],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/..",
        env=dict(os.environ),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = sorted(t.name for t in tools.tools)
            print("Registered tools:", names)
            assert "get_macro" in names and "get_stage" in names

            macro = await session.call_tool("get_macro", {})
            print("\nget_macro ->", macro.content[0].text[:300])
            assert not macro.is_error

            stage = await session.call_tool("get_stage", {"tickers": "AAPL,MSFT"})
            print("\nget_stage ->", stage.content[0].text[:300])
            assert not stage.is_error

            usage = await session.call_tool("get_usage", {})
            print("\nget_usage ->", usage.content[0].text[:300])
            assert not usage.is_error

            print("\nAll real subprocess/stdio round-trips succeeded.")


if __name__ == "__main__":
    asyncio.run(main())
