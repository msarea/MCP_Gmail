#!/usr/bin/env python3
"""
MCP Search Server - Provides web search and location-based search tools
Uses location_helper for geocoding and can integrate with search APIs
"""

import sys
import os
import json
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from location_helper import get_location_coordinates, geocode_location

# Initialize the server
app = Server("search-mcp-server")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available search tools."""
    return [
        Tool(
            name="search_web",
            description="Search the web for information. Use this for general queries, news, facts, or any information that might be on the internet.",
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
            description="Find places, businesses, restaurants, or points of interest near a location. Use this for location-based searches like 'coffee shops', 'hotels', 'restaurants', etc.",
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
            description="Get current weather information for a location.",
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
            description="Get general information about a location (coordinates, timezone, population, etc.).",
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

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    
    if name == "search_web":
        query = arguments.get("query", "")
        location = arguments.get("location")
        max_results = arguments.get("max_results", 5)
        
        # Get location coordinates if location provided
        location_info = ""
        if location:
            coords = get_location_coordinates(f"location: {location}")
            if coords:
                location_info = f" (near {location} at {coords['latitude']}, {coords['longitude']})"
        
        # For now, return a structured response that Gemini can use
        # In production, you would call an actual search API here
        result = {
            "query": query,
            "location": location,
            "location_coords": get_location_coordinates(f"location: {location}") if location else None,
            "message": f"I searched for '{query}'{location_info if location_info else ''}. "
                      f"Here's what I found based on general knowledge and the location context provided. "
                      f"For real-time web search results, you would need to integrate with a search API like Google Custom Search, Bing Search, or DuckDuckGo.",
            "suggestion": "To get actual web search results, integrate with Google Custom Search API, Bing Search API, or use a service like SerpAPI."
        }
        
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]
    
    elif name == "find_places":
        query = arguments.get("query", "")
        location = arguments.get("location", "")
        max_results = arguments.get("max_results", 10)
        
        if not location:
            return [TextContent(
                type="text",
                text=json.dumps({"error": "Location is required for finding places"}, indent=2)
            )]
        
        # Get location coordinates
        coords = get_location_coordinates(f"location: {location}")
        
        if not coords:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": f"Could not find coordinates for location: {location}",
                    "suggestion": "Try a more specific location name or enable Google Geocoding API"
                }, indent=2)
            )]
        
        # For now, return structured response
        # In production, you would call Google Places API, Yelp API, or similar
        result = {
            "query": query,
            "location": location,
            "coordinates": coords,
            "message": f"I found information about '{query}' near {location} (coordinates: {coords['latitude']}, {coords['longitude']}). "
                      f"For actual place listings with ratings, hours, and reviews, integrate with Google Places API or Yelp API.",
            "suggestion": "To get real place data, integrate with Google Places API (requires Google Maps API key) or Yelp Fusion API."
        }
        
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]
    
    elif name == "get_weather":
        location = arguments.get("location", "")
        
        if not location:
            return [TextContent(
                type="text",
                text=json.dumps({"error": "Location is required"}, indent=2)
            )]
        
        coords = get_location_coordinates(f"location: {location}")
        
        result = {
            "location": location,
            "coordinates": coords,
            "message": f"To get current weather for {location}, integrate with a weather API like OpenWeatherMap, WeatherAPI, or AccuWeather. "
                      f"Location coordinates: {coords if coords else 'not found'}",
            "suggestion": "Integrate with OpenWeatherMap API (free tier available) or WeatherAPI for real-time weather data."
        }
        
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]
    
    elif name == "get_location_info":
        location = arguments.get("location", "")
        
        if not location:
            return [TextContent(
                type="text",
                text=json.dumps({"error": "Location is required"}, indent=2)
            )]
        
        coords = get_location_coordinates(f"location: {location}")
        
        result = {
            "location": location,
            "coordinates": coords,
            "message": f"Location: {location}. Coordinates: {coords if coords else 'not found'}. "
                      f"For detailed location information (population, timezone, etc.), use Google Geocoding API or GeoNames API.",
            "suggestion": "Use Google Geocoding API (reverse geocoding) or GeoNames API for detailed location information."
        }
        
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]
    
    else:
        return [TextContent(
            type="text",
            text=json.dumps({"error": f"Unknown tool: {name}"}, indent=2)
        )]

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

