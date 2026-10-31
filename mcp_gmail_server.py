#!/usr/bin/env python3
"""
MCP Server for Gmail Integration
Comprehensive Gmail functionality via MCP protocol
"""

import asyncio
import json
import sys
from typing import Any
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

app = Server("gmail-mcp-server")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    return [
        # Email Reading
        Tool(
            name="get_unread_emails",
            description="Get a list of unread emails from Gmail inbox.",
            inputSchema={
                "type": "object",
                "properties": {
                    "max_results": {"type": "integer", "description": "Maximum number of emails (default: 10)", "default": 10}
                }
            }
        ),
        Tool(
            name="get_email_details",
            description="Get full details of a specific email including subject, sender, body, and headers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_id": {"type": "string", "description": "The Gmail message ID"}
                },
                "required": ["message_id"]
            }
        ),
        Tool(
            name="list_emails",
            description="List emails with optional Gmail search query.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Gmail search query"},
                    "max_results": {"type": "integer", "description": "Maximum results (default: 10)", "default": 10}
                }
            }
        ),
        Tool(
            name="search_emails",
            description="Advanced email search with optional date range.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Gmail search query"},
                    "max_results": {"type": "integer", "default": 10},
                    "date_from": {"type": "string", "description": "Start date (YYYY/MM/DD)"},
                    "date_to": {"type": "string", "description": "End date (YYYY/MM/DD)"}
                },
                "required": ["query"]
            }
        ),
        # Email Status
        Tool(
            name="mark_as_read",
            description="Mark an email as read.",
            inputSchema={
                "type": "object",
                "properties": {"message_id": {"type": "string"}},
                "required": ["message_id"]
            }
        ),
        Tool(
            name="mark_as_unread",
            description="Mark an email as unread.",
            inputSchema={
                "type": "object",
                "properties": {"message_id": {"type": "string"}},
                "required": ["message_id"]
            }
        ),
        Tool(
            name="archive_email",
            description="Archive an email (remove from inbox).",
            inputSchema={
                "type": "object",
                "properties": {"message_id": {"type": "string"}},
                "required": ["message_id"]
            }
        ),
        Tool(
            name="star_email",
            description="Star an email.",
            inputSchema={
                "type": "object",
                "properties": {"message_id": {"type": "string"}},
                "required": ["message_id"]
            }
        ),
        Tool(
            name="unstar_email",
            description="Unstar an email.",
            inputSchema={
                "type": "object",
                "properties": {"message_id": {"type": "string"}},
                "required": ["message_id"]
            }
        ),
        # Email Sending
        Tool(
            name="send_reply",
            description="Send a reply to an email.",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_id": {"type": "string"},
                    "reply_text": {"type": "string"}
                },
                "required": ["message_id", "reply_text"]
            }
        ),
        Tool(
            name="send_email",
            description="Send a new email (not a reply).",
            inputSchema={
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email(s), comma-separated or list"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                    "cc": {"type": "string", "description": "CC email(s), optional"},
                    "bcc": {"type": "string", "description": "BCC email(s), optional"}
                },
                "required": ["to", "subject", "body"]
            }
        ),
        Tool(
            name="forward_email",
            description="Forward an email to another recipient.",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_id": {"type": "string"},
                    "to": {"type": "string"},
                    "forward_text": {"type": "string", "description": "Optional text to add"}
                },
                "required": ["message_id", "to"]
            }
        ),
        # Drafts
        Tool(
            name="create_draft",
            description="Create a draft email.",
            inputSchema={
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"}
                },
                "required": ["to", "subject", "body"]
            }
        ),
        Tool(
            name="get_drafts",
            description="Get list of draft emails.",
            inputSchema={
                "type": "object",
                "properties": {"max_results": {"type": "integer", "default": 10}}
            }
        ),
        Tool(
            name="send_draft",
            description="Send a draft email.",
            inputSchema={
                "type": "object",
                "properties": {"draft_id": {"type": "string"}},
                "required": ["draft_id"]
            }
        ),
        # Deletion
        Tool(
            name="delete_email",
            description="Move an email to Gmail Trash; it can be restored before Trash is emptied.",
            inputSchema={
                "type": "object",
                "properties": {"message_id": {"type": "string"}},
                "required": ["message_id"]
            }
        ),
        Tool(
            name="delete_emails_from_sender",
            description="Move matching emails from a sender to Gmail Trash; they can be restored before Trash is emptied.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sender_email": {"type": "string"},
                    "max_results": {"type": "integer", "default": 100}
                },
                "required": ["sender_email"]
            }
        ),
        # Labels
        Tool(
            name="list_labels",
            description="Get list of all Gmail labels.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="create_label",
            description="Create a new label.",
            inputSchema={
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"]
            }
        ),
        Tool(
            name="add_label_to_email",
            description="Add a label to an email.",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_id": {"type": "string"},
                    "label_id": {"type": "string"}
                },
                "required": ["message_id", "label_id"]
            }
        ),
        Tool(
            name="get_emails_by_label",
            description="Get emails with a specific label.",
            inputSchema={
                "type": "object",
                "properties": {
                    "label_id": {"type": "string"},
                    "max_results": {"type": "integer", "default": 10}
                },
                "required": ["label_id"]
            }
        ),
        # Threads
        Tool(
            name="get_thread",
            description="Get all messages in a thread.",
            inputSchema={
                "type": "object",
                "properties": {"thread_id": {"type": "string"}},
                "required": ["thread_id"]
            }
        ),
        # Statistics
        Tool(
            name="get_email_stats",
            description="Get email statistics (total, unread, inbox, starred counts).",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_attachments",
            description="Get list of attachments in an email.",
            inputSchema={
                "type": "object",
                "properties": {"message_id": {"type": "string"}},
                "required": ["message_id"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    if gmail_client is None and not initialize_gmail():
        return [TextContent(type="text", text=json.dumps({"error": "Gmail client initialization failed; check credentials and OAuth access."}))]
    
    try:
        # Email Reading
        if name == "get_unread_emails":
            max_results = arguments.get("max_results", 10)
            messages = gmail_client.get_unread_emails(max_results=max_results)
            return [TextContent(type="text", text=json.dumps({"count": len(messages), "messages": messages}, indent=2))]
        
        elif name == "get_email_details":
            message_id = arguments.get("message_id")
            if not message_id:
                return [TextContent(type="text", text=json.dumps({"error": "message_id is required"}))]
            email_details = gmail_client.get_email_details(message_id)
            return [TextContent(type="text", text=json.dumps(email_details, indent=2))]
        
        elif name == "list_emails":
            query = arguments.get("query", "")
            max_results = arguments.get("max_results", 10)
            messages = gmail_client.list_emails(query=query, max_results=max_results)
            return [TextContent(type="text", text=json.dumps({"count": len(messages), "query": query, "messages": messages}, indent=2))]
        
        elif name == "search_emails":
            query = arguments.get("query")
            max_results = arguments.get("max_results", 10)
            date_from = arguments.get("date_from")
            date_to = arguments.get("date_to")
            messages = gmail_client.search_emails(query, max_results, date_from, date_to)
            return [TextContent(type="text", text=json.dumps({"count": len(messages), "messages": messages}, indent=2))]
        
        # Email Status
        elif name == "mark_as_read":
            result = gmail_client.mark_as_read(arguments.get("message_id"))
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "mark_as_unread":
            result = gmail_client.mark_as_unread(arguments.get("message_id"))
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "archive_email":
            result = gmail_client.archive_email(arguments.get("message_id"))
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "star_email":
            result = gmail_client.star_email(arguments.get("message_id"))
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "unstar_email":
            result = gmail_client.unstar_email(arguments.get("message_id"))
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        # Email Sending
        elif name == "send_reply":
            message_id = arguments.get("message_id")
            reply_text = arguments.get("reply_text")
            if not message_id or not reply_text:
                return [TextContent(type="text", text=json.dumps({"error": "message_id and reply_text are required"}))]
            result = gmail_client.send_reply(message_id, reply_text)
            return [TextContent(type="text", text=json.dumps({"success": True, "reply_sent": result}, indent=2))]
        
        elif name == "send_email":
            to = arguments.get("to")
            subject = arguments.get("subject")
            body = arguments.get("body")
            cc = arguments.get("cc")
            bcc = arguments.get("bcc")
            if not to or not subject or not body:
                return [TextContent(type="text", text=json.dumps({"error": "to, subject, and body are required"}))]
            result = gmail_client.send_email(to, subject, body, cc, bcc)
            return [TextContent(type="text", text=json.dumps({"success": True, "email_sent": result}, indent=2))]
        
        elif name == "forward_email":
            message_id = arguments.get("message_id")
            to = arguments.get("to")
            forward_text = arguments.get("forward_text", "")
            if not message_id or not to:
                return [TextContent(type="text", text=json.dumps({"error": "message_id and to are required"}))]
            result = gmail_client.forward_email(message_id, to, forward_text)
            return [TextContent(type="text", text=json.dumps({"success": True, "email_forwarded": result}, indent=2))]
        
        # Drafts
        elif name == "create_draft":
            result = gmail_client.create_draft(
                arguments.get("to"),
                arguments.get("subject"),
                arguments.get("body")
            )
            return [TextContent(type="text", text=json.dumps({"success": True, "draft_created": result}, indent=2))]
        
        elif name == "get_drafts":
            max_results = arguments.get("max_results", 10)
            drafts = gmail_client.get_drafts(max_results=max_results)
            return [TextContent(type="text", text=json.dumps({"count": len(drafts), "drafts": drafts}, indent=2))]
        
        elif name == "send_draft":
            result = gmail_client.send_draft(arguments.get("draft_id"))
            return [TextContent(type="text", text=json.dumps({"success": True, "draft_sent": result}, indent=2))]
        
        # Deletion
        elif name == "delete_email":
            result = gmail_client.delete_email(arguments.get("message_id"))
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "delete_emails_from_sender":
            result = gmail_client.delete_emails_from_sender(
                arguments.get("sender_email"),
                arguments.get("max_results", 100)
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        # Labels
        elif name == "list_labels":
            labels = gmail_client.list_labels()
            return [TextContent(type="text", text=json.dumps({"count": len(labels), "labels": labels}, indent=2))]
        
        elif name == "create_label":
            result = gmail_client.create_label(arguments.get("name"))
            return [TextContent(type="text", text=json.dumps({"success": True, "label": result}, indent=2))]
        
        elif name == "add_label_to_email":
            result = gmail_client.add_label_to_email(
                arguments.get("message_id"),
                arguments.get("label_id")
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "get_emails_by_label":
            result = gmail_client.get_emails_by_label(
                arguments.get("label_id"),
                arguments.get("max_results", 10)
            )
            return [TextContent(type="text", text=json.dumps({"count": len(result), "messages": result}, indent=2))]
        
        # Threads
        elif name == "get_thread":
            result = gmail_client.get_thread(arguments.get("thread_id"))
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        # Statistics
        elif name == "get_email_stats":
            stats = gmail_client.get_stats()
            return [TextContent(type="text", text=json.dumps(stats, indent=2))]
        
        elif name == "get_attachments":
            result = gmail_client.get_attachments(arguments.get("message_id"))
            return [TextContent(type="text", text=json.dumps({"count": len(result), "attachments": result}, indent=2))]
        
        else:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]
    
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

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
