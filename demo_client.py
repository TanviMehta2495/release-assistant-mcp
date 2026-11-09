"""Connects to the server over stdio (like a real MCP client), lists its tools and calls them."""
import asyncio
import json
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters

SERVER = StdioServerParameters(command=sys.executable, args=[str(Path(__file__).parent / "server.py")])


def show(result):
    for block in result.content:
        if getattr(block, "text", None):
            try:
                print(json.dumps(json.loads(block.text), indent=2))
            except ValueError:
                print(block.text)


async def main():
    async with Client(SERVER) as client:
        tools = await client.list_tools()
        print("Tools exposed by the server:")
        for t in tools.tools:
            print(f"  - {t.name}: {t.description}")

        for service in ["checkout-api", "payments-service", "inventory-sync"]:
            print(f"\ncheck_release_readiness('{service}'):")
            show(await client.call_tool("check_release_readiness", {"service": service}))


if __name__ == "__main__":
    asyncio.run(main())
