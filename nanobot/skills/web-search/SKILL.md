---
name: web-search
description: Search the web using Exa AI - a neural search engine. Find company info, news, tweets, people profiles, and general web content.
homepage: https://exa.ai/docs
metadata: {"nanobot":{"emoji":"🔍","requires":{"env":["EXA_API_KEY"]}}}
---

# Web Search (Exa AI)

Exa AI is a neural search engine that understands meaning, not just keywords.

## Tool: `web_search`

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | string | Search query (required) |
| `count` | int | Number of results (1-20, default: 5) |
| `search_type` | string | "auto" (default), "keyword", "neural" |
| `category` | string | "company", "news", "tweet", "people", or omit |

## Categories (Important!)

Choose the right category for targeted results:

| Category | Use Case | Returns |
|----------|----------|---------|
| `company` | Find companies, startups | Homepages, metadata (funding, headcount) |
| `news` | Recent coverage, announcements | News articles, press |
| `tweet` | Social sentiment, public opinion | X/Twitter posts |
| `people` | Find professionals | LinkedIn profiles (public data) |
| *(omit)* | General research | Web pages, deep content |

## Search Types

- **auto** → Exa chooses the best type (default)
- **neural** → Semantic search, best for concepts and natural language
- **keyword** → Traditional keyword matching

## Examples

### General search
```
web_search(query="AI infrastructure startups San Francisco", count=10)
```

### Company discovery
```
web_search(query="AI infrastructure startups", category="company", count=20)
```

### News coverage
```
web_search(query="OpenAI GPT-5 announcement", category="news", count=10)
```

### Twitter/X posts
```
web_search(query="AI startup funding trends", category="tweet", count=15)
```

### LinkedIn profiles
```
web_search(query="VP Engineering AI infrastructure", category="people", count=10)
```

### Neural search (conceptual)
```
web_search(query="how to scale machine learning systems", search_type="neural", count=10)
```

## Tips

1. **Use categories** for targeted searches - dramatically improves relevance
2. **Neural search** works best for conceptual/natural language queries
3. **Combine with web_fetch** to get full content from search results
4. **Increase count** for comprehensive research (up to 20 results)

## Configuration

In `config.json`:
```json
{
  "tools": {
    "web": {
      "search": {
        "apiKey": "your-exa-api-key",
        "maxResults": 5
      }
    }
  }
}
```

Or set environment variable:
```bash
export EXA_API_KEY="your-api-key"
```

Get your API key: https://exa.ai
