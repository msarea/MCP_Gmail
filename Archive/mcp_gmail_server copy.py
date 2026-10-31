#!/usr/bin/env python3
"""
MCP Server for Gmail Integration
Provides tools to read emails and send replies via Gmail API
"""

import asyncio
import json
import sys
from typing import Any, Optional
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from gmail_client import GmailClient

# Initialize Gmail client
gmail_client = None

def initialize_gmail():
    """Initialize Gmail client with authentication."""
    global gmail_client
    try:
        gmail_client = GmailClient()
        return True
    except Exception as e:
        print(f"Failed to initialize Gmail client: {e}", file=sys.stderr)
        return False

# Initialize on import
if not initialize_gmail():
    print("Warning: Gmail client initialization failed. Some tools may not work.", file=sys.stderr)

app = Server("gmail-mcp-server")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="get_unread_emails",
            description="Get a list of unread emails from Gmail inbox. Returns email IDs and basic info.",
            inputSchema={
                "type": "object",
                "properties": {
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of emails to return (default: 10)",
                        "default": 10
                    }
                }
            }
        ),
        Tool(
            name="get_email_details",
            description="Get full details of a specific email including subject, sender, body, and headers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "The Gmail message ID to retrieve"
                    }
                },
                "required": ["message_id"]
            }
        ),
        Tool(
            name="send_reply",
            description="Send a reply to an email. Automatically extracts recipient and subject from original message.",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "The Gmail message ID to reply to"
                    },
                    "reply_text": {
                        "type": "string",
                        "description": "The text content of the reply"
                    }
                },
                "required": ["message_id", "reply_text"]
            }
        ),
        Tool(
            name="list_emails",
            description="List emails with optional Gmail search query (e.g., 'from:example@gmail.com', 'subject:meeting').",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Gmail search query (optional)"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of emails to return (default: 10)",
                        "default": 10
                    }
                }
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    if gmail_client is None:
        return [TextContent(
            type="text",
            text=json.dumps({"error": "Gmail client not initialized. Please check credentials."})
        )]
    
    try:
        if name == "get_unread_emails":
            max_results = arguments.get("max_results", 10)
            messages = gmail_client.get_unread_emails(max_results=max_results)
            return [TextContent(
                type="text",
                text=json.dumps({
                    "count": len(messages),
                    "messages": messages
                }, indent=2)
            )]
        
        elif name == "get_email_details":
            message_id = arguments.get("message_id")
            if not message_id:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": "message_id is required"})
                )]
            
            email_details = gmail_client.get_email_details(message_id)
            return [TextContent(
                type="text",
                text=json.dumps(email_details, indent=2)
            )]
        
        elif name == "send_reply":
            message_id = arguments.get("message_id")
            reply_text = arguments.get("reply_text")
            
            if not message_id or not reply_text:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": "message_id and reply_text are required"})
                )]
            
            result = gmail_client.send_reply(message_id, reply_text)
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "reply_sent": result
                }, indent=2)
            )]
        
        elif name == "list_emails":
            query = arguments.get("query", "")
            max_results = arguments.get("max_results", 10)
            messages = gmail_client.list_emails(query=query, max_results=max_results)
            return [TextContent(
                type="text",
                text=json.dumps({
                    "count": len(messages),
                    "query": query,
                    "messages": messages
                }, indent=2)
            )]
        
        else:
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Unknown tool: {name}"})
            )]
    
    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps({"error": str(e)})
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
