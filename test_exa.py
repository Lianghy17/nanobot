#!/usr/bin/env python3
"""Test Exa API."""

import asyncio
import json

# Load config
with open("config.json") as f:
    config = json.load(f)

api_key = config.get("tools", {}).get("web", {}).get("search", {}).get("apiKey", "")
print(f"API Key: {api_key[:10]}...")

from exa_py import Exa

exa = Exa(api_key=api_key)

# Test sync search
print("\nTesting sync search...")
try:
    result = exa.search(
        query="A股上周行情",
        type="auto",
        num_results=3,
        contents={
            "highlights": {
                "max_characters": 4000
            }
        }
    )
    print(f"Result type: {type(result)}")
    print(f"Number of results: {len(result.results)}")
    for i, item in enumerate(result.results[:3], 1):
        print(f"\n{i}. {item.title}")
        print(f"   {item.url}")
        if hasattr(item, 'highlights') and item.highlights:
            print(f"   Highlights: {item.highlights[:100]}...")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
