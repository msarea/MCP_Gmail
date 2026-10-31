#!/usr/bin/env python3
"""
MCP Search Server - Provides web search and location-based search tools
Uses location_helper for geocoding and can integrate with search APIs
"""

import sys
import os
import json
import asyncio
import urllib.parse
import urllib.request
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Initialize the server
app = Server("search-mcp-server")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available search tools."""
    return [
        Tool(
            name="search_web",
            description="Search the web using Brave Search. Requires BRAVE_SEARCH_API_KEY.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query (e.g., 'best restaurants in Los Angeles', 'weather in New York', 'latest news about AI')"
                    },
                    "location": {
                        "type": "string",
                        "description": "Optional location to make search location-relevant (e.g., 'Los Angeles', 'New York, NY')"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="find_places",
            description="Find places using Google Places. Requires GOOGLE_MAPS_API_KEY.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to search for (e.g., 'Italian restaurants', 'coffee shops', 'hotels', 'gas stations')"
                    },
                    "location": {
                        "type": "string",
                        "description": "Location to search near (e.g., 'Los Angeles', 'New York, NY', 'San Francisco'). Required for place searches."
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 10)",
                        "default": 10
                    }
                },
                "required": ["query", "location"]
            }
        ),
        Tool(
            name="get_weather",
            description="Get current weather for a location using Open-Meteo.",
            inputSchema={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "Location name (e.g., 'Los Angeles', 'New York, NY', 'London, UK')"
                    }
                },
                "required": ["location"]
            }
        ),
        Tool(
            name="get_location_info",
            description="Look up location coordinates and available metadata using Open-Meteo geocoding.",
            inputSchema={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "Location name (e.g., 'Los Angeles', 'New York, NY')"
                    }
                },
                "required": ["location"]
            }
        )
    ]

def _json_request(url, headers=None):
    request = urllib.request.Request(url, headers=headers or {"User-Agent": "MCP-Gmail/1.0"})
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def _geocode(location):
    url = "https://geocoding-api.open-meteo.com/v1/search?" + urllib.parse.urlencode({"name": location, "count": 1, "language": "en", "format": "json"})
    results = _json_request(url).get("results", [])
    return results[0] if results else None


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls using real providers and report missing configuration honestly."""
    try:
        if name == "search_web":
            query = (arguments.get("query") or "").strip()
            if not query:
                result = {"error": "query is required"}
            elif not os.getenv("BRAVE_SEARCH_API_KEY"):
                result = {"status": "not_configured", "error": "Set BRAVE_SEARCH_API_KEY to enable web search."}
            else:
                params = urllib.parse.urlencode({"q": query, "count": max(1, min(int(arguments.get("max_results", 5)), 20))})
                data = _json_request("https://api.search.brave.com/res/v1/web/search?" + params, {"Accept": "application/json", "X-Subscription-Token": os.environ["BRAVE_SEARCH_API_KEY"], "User-Agent": "MCP-Gmail/1.0"})
                result = {"query": query, "results": [{"title": item.get("title"), "url": item.get("url"), "description": item.get("description")} for item in data.get("web", {}).get("results", [])]}
        elif name == "find_places":
            query, location = (arguments.get("query") or "").strip(), (arguments.get("location") or "").strip()
            key = os.getenv("GOOGLE_MAPS_API_KEY")
            if not key:
                result = {"status": "not_configured", "error": "Set GOOGLE_MAPS_API_KEY to enable Google Places search."}
            else:
                import googlemaps
                client = googlemaps.Client(key=key)
                data = client.places(query=f"{query} in {location}", page_token=None)
                limit = max(1, min(int(arguments.get("max_results", 10)), 20))
                result = {"query": query, "location": location, "results": [{"name": item.get("name"), "address": item.get("formatted_address"), "rating": item.get("rating"), "place_id": item.get("place_id")} for item in data.get("results", [])[:limit]]}
        elif name in ("get_weather", "get_location_info"):
            location = (arguments.get("location") or "").strip()
            if not location:
                result = {"error": "location is required"}
            else:
                place = _geocode(location)
                if not place:
                    result = {"status": "not_found", "location": location}
                elif name == "get_location_info":
                    result = {"location": location, "name": place.get("name"), "country": place.get("country"), "admin1": place.get("admin1"), "latitude": place.get("latitude"), "longitude": place.get("longitude"), "timezone": place.get("timezone"), "population": place.get("population")}
                else:
                    params = urllib.parse.urlencode({"latitude": place["latitude"], "longitude": place["longitude"], "current": "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,wind_speed_10m", "timezone": "auto"})
                    forecast = _json_request("https://api.open-meteo.com/v1/forecast?" + params)
                    result = {"location": place.get("name"), "country": place.get("country"), "current": forecast.get("current"), "units": forecast.get("current_units")}
        else:
            result = {"error": f"Unknown tool: {name}"}
    except Exception as error:
        result = {"error": str(error)}
    return [TextContent(type="text", text=json.dumps(result, indent=2))]

async def main():
    """Main entry point for the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())

