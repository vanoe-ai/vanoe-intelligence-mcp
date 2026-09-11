"""Entry point for the Claude Desktop bundle: runs the published package's
stdio server. The API key arrives as VANOE_API_KEY from the bundle's user
settings (manifest.json -> user_config.api_key)."""
from mcp_server.server import main

if __name__ == "__main__":
    main()
