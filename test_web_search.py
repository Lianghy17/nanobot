#!/usr/bin/env python3
"""Test web_search tool."""

import asyncio
import json

# Load config
with open("config.json") as f:
    config = json.load(f)

api_key = config.get("tools", {}).get("web", {}).get("search", {}).get("apiKey", "")
print(f"API Key: {api_key[:10]}...")

# Import the tool
from nanobot.agent.tools.web import WebSearchTool

tool = WebSearchTool(api_key=api_key, max_results=5)

async def test():
    print("\nTesting web_search tool...")
    try:
        result = await tool.execute(
            query="A股上周行情",
            count=3,
            search_type="auto"
        )
        print(f"\nResult:\n{result}")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test())
