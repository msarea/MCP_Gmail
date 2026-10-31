#!/usr/bin/env python3
"""
MCP Server for Calendar Integration
Comprehensive Google Calendar functionality via MCP protocol
"""

import asyncio
import json
import sys
from typing import Any
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from calendar_client import CalendarClient # Assuming your client is named this

# Initialize Calendar client
calendar_client = None

def initialize_calendar():
    """Initialize Calendar client with authentication."""
    global calendar_client
    try:
        # Note: This relies on the 'credentials.json' and 'token.json' setup
        calendar_client = CalendarClient()
        return True
    except Exception as e:
        print(f"Failed to initialize Calendar client: {e}", file=sys.stderr)
        return False

# Initialize on import
if not initialize_calendar():
    print("Warning: Calendar client initialization failed. Some tools may not work.", file=sys.stderr)

app = Server("calendar-mcp-server")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    return [
        # Calendar Reading/Querying
        Tool(
            name="get_calendars",
            description="Get a list of all user calendars and their IDs.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_events",
            description="Get a list of future events from a specified calendar.",
            inputSchema={
                "type": "object",
                "properties": {
                    "calendar_id": {"type": "string", "description": "The calendar ID (default: 'primary')", "default": "primary"},
                    "time_min": {"type": "string", "description": "Start datetime (ISO 8601, e.g., '2025-12-01T00:00:00Z')"},
                    "time_max": {"type": "string", "description": "End datetime (ISO 8601)"},
                    "max_results": {"type": "integer", "description": "Maximum number of events (default: 100)", "default": 100}
                }
            }
        ),
        Tool(
            name="get_busy_times",
            description="Get busy time slots for a calendar within a time range.",
            inputSchema={
                "type": "object",
                "properties": {
                    "time_min": {"type": "string", "description": "Start datetime (ISO 8601, required)"},
                    "time_max": {"type": "string", "description": "End datetime (ISO 8601, required)"},
                    "calendar_id": {"type": "string", "description": "The calendar ID (default: 'primary')", "default": "primary"}
                },
                "required": ["time_min", "time_max"]
            }
        ),
        Tool(
            name="find_free_slots",
            description="Find available time slots for a meeting.",
            inputSchema={
                "type": "object",
                "properties": {
                    "duration_minutes": {"type": "integer", "description": "Required duration in minutes (e.g., 30 or 60)", "default": 30},
                    "days_ahead": {"type": "integer", "description": "Number of days to search ahead from now", "default": 7},
                    "start_hour": {"type": "integer", "description": "Daily start hour (24h format, UTC)", "default": 9},
                    "end_hour": {"type": "integer", "description": "Daily end hour (24h format, UTC)", "default": 17},
                    "calendar_id": {"type": "string", "description": "The calendar ID (default: 'primary')", "default": "primary"}
                }
            }
        ),
        # Event Management
        Tool(
            name="create_event",
            description="Create a new calendar event.",
            inputSchema={
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "start_time": {"type": "string", "description": "Start datetime (ISO 8601, required)"},
                    "end_time": {"type": "string", "description": "End datetime (ISO 8601, required)"},
                    "attendees": {"type": "array", "items": {"type": "string"}, "description": "List of attendee emails"},
                    "description": {"type": "string"},
                    "location": {"type": "string"},
                    "calendar_id": {"type": "string", "default": "primary"}
                },
                "required": ["summary", "start_time", "end_time"]
            }
        ),
        Tool(
            name="update_event",
            description="Update an existing calendar event.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "string"},
                    "summary": {"type": "string"},
                    "start_time": {"type": "string", "description": "Start datetime (ISO 8601)"},
                    "end_time": {"type": "string", "description": "End datetime (ISO 8601)"},
                    "attendees": {"type": "array", "items": {"type": "string"}, "description": "Full list of attendees to replace current ones"},
                    "description": {"type": "string"},
                    "calendar_id": {"type": "string", "default": "primary"}
                },
                "required": ["event_id"]
            }
        ),
        Tool(
            name="delete_event",
            description="Delete a calendar event.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "string"},
                    "calendar_id": {"type": "string", "default": "primary"}
                },
                "required": ["event_id"]
            }
        ),
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    if calendar_client is None:
        return [TextContent(
            type="text",
            text=json.dumps({"error": "Calendar client not initialized. Please check credentials."}, indent=2)
        )]
    
    try:
        # Event Management
        if name == "create_event":
            result = calendar_client.create_event(
                summary=arguments["summary"],
                start_time=arguments["start_time"],
                end_time=arguments["end_time"],
                attendees=arguments.get("attendees"),
                description=arguments.get("description", ""),
                location=arguments.get("location", ""),
                calendar_id=arguments.get("calendar_id", "primary")
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "update_event":
            result = calendar_client.update_event(
                event_id=arguments["event_id"],
                summary=arguments.get("summary"),
                start_time=arguments.get("start_time"),
                end_time=arguments.get("end_time"),
                attendees=arguments.get("attendees"),
                description=arguments.get("description"),
                calendar_id=arguments.get("calendar_id", "primary")
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "delete_event":
            result = calendar_client.delete_event(
                event_id=arguments["event_id"],
                calendar_id=arguments.get("calendar_id", "primary")
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        # Calendar Reading/Querying
        elif name == "get_calendars":
            calendars = calendar_client.get_calendars()
            return [TextContent(type="text", text=json.dumps({"count": len(calendars), "calendars": calendars}, indent=2))]
            
        elif name == "get_events":
            events = calendar_client.get_events(
                calendar_id=arguments.get("calendar_id", "primary"),
                time_min=arguments.get("time_min"),
                time_max=arguments.get("time_max"),
                max_results=arguments.get("max_results", 100)
            )
            return [TextContent(type="text", text=json.dumps({"count": len(events), "events": events}, indent=2))]
            
        elif name == "get_busy_times":
            busy = calendar_client.get_busy_times(
                time_min=arguments["time_min"],
                time_max=arguments["time_max"],
                calendar_id=arguments.get("calendar_id", "primary")
            )
            return [TextContent(type="text", text=json.dumps({"count": len(busy), "busy_slots": busy}, indent=2))]
            
        elif name == "find_free_slots":
            slots = calendar_client.find_free_slots(
                duration_minutes=arguments.get("duration_minutes", 30),
                days_ahead=arguments.get("days_ahead", 7),
                start_hour=arguments.get("start_hour", 9),
                end_hour=arguments.get("end_hour", 17),
                calendar_id=arguments.get("calendar_id", "primary")
            )
            return [TextContent(type="text", text=json.dumps({"count": len(slots), "free_slots": slots}, indent=2))]
            
        else:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]
    
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}, indent=2))]

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
