import os
import requests
import json

async def internet_search(query):
    """Search the internet using Perplexity API"""
    api_key = os.getenv("PERPLEXITY_API_KEY", "")
    url = "https://api.perplexity.ai/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "sonar",
        "messages": [
            {"role": "system", "content": "Be precise and concise."},
            {"role": "user", "content": query['query']}
        ],
        "max_tokens": 500,
        "temperature": 0.7
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.json() if response.status_code == 200 else {"error": response.text}

def get_tool_definition():
    """Return the tool definition for Nova Sonic"""
    return {
        "toolSpec": {
            "name": "internet_search",
            "description": "Internet search with perplexity",
            "inputSchema": {
                "json": json.dumps({
                    "type": "object",
                    "properties": {"query": {"type": "string", "description": "query to search"}},
                    "required": ["query"]
                })
            }
        }
    }
