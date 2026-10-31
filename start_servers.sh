#!/bin/bash

echo "Starting Gmail MCP Server..."
python3 mcp_gmail_server.py &

echo "Starting Calendar MCP Server..."
python3 mcp_calendar_server.py &

echo "Starting Search MCP Server..."
python3 mcp_search_server.py &

echo "All three servers are running in the background."
echo "Use 'jobs' to see them and 'kill' to stop them."
