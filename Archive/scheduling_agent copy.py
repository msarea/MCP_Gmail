#!/usr/bin/env python3
"""
Scheduling Agent - Connects Gmail and Calendar MCP servers with Gemini AI
Uses agent_core.py for meeting extraction and reply generation
"""

import os
import asyncio
import json
import sys
from pathlib import Path
from google import genai
from google.genai import types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Import agent_core functions
from agent_core import extract_meeting_details, generate_reply_text

# --- 1. Configuration and Initialization ---

# Check for the Gemini API Key
if not os.getenv("GEMINI_API_KEY"):
    print("Error: The GEMINI_API_KEY environment variable is not set.")
    print("Please set it permanently in your ~/.zshrc file.")
    sys.exit(1)

# Initialize the Gemini Client
try:
    GEMINI_CLIENT = genai.Client()
    print("✓ Gemini client initialized")
except Exception as e:
    print(f"Error initializing Gemini client: {e}")
    sys.exit(1)

# Get the script directory for absolute paths
SCRIPT_DIR = Path(__file__).parent.absolute()

async def get_all_tools(gmail_session, calendar_session):
    """Get tools from all MCP servers."""
    all_tools = []
    
    if gmail_session:
        try:
            print("  → Getting Gmail tools...")
            gmail_tools_result = await gmail_session.list_tools()
            all_tools.extend(gmail_tools_result.tools)
            print(f"  ✓ Found {len(gmail_tools_result.tools)} Gmail tools")
        except Exception as e:
            print(f"  ✗ Error getting Gmail tools: {e}")
            import traceback
            traceback.print_exc()
    
    if calendar_session:
        try:
            print("  → Getting Calendar tools...")
            calendar_tools_result = await calendar_session.list_tools()
            all_tools.extend(calendar_tools_result.tools)
            print(f"  ✓ Found {len(calendar_tools_result.tools)} Calendar tools")
        except Exception as e:
            print(f"  ✗ Error getting Calendar tools: {e}")
            import traceback
            traceback.print_exc()
    
    return all_tools

async def call_mcp_tool(gmail_session, calendar_session, tool_name: str, arguments: dict):
    """Call a tool on the appropriate MCP server."""
    # Try Gmail server first
    if gmail_session:
        try:
            result = await gmail_session.call_tool(tool_name, arguments)
            return result
        except Exception as e:
            # Tool not found in Gmail, try Calendar
            pass
    
    # Try Calendar server
    if calendar_session:
        try:
            result = await calendar_session.call_tool(tool_name, arguments)
            return result
        except Exception as e:
            raise Exception(f"Tool '{tool_name}' not found in any server: {e}")
    
    raise Exception("No MCP servers available")

# --- 2. Main Agent Logic ---

async def run_agent(gmail_session, calendar_session, user_prompt: str):
    """Main agent loop that processes user requests using Gemini and MCP tools."""
    print(f"\n{'='*60}")
    print(f"User Request: {user_prompt}")
    print(f"{'='*60}\n")

    # 2a. Get available tools from all connected MCP servers
    print("Step 1: Connecting to MCP servers and collecting tools...")
    tools = await get_all_tools(gmail_session, calendar_session)
    
    if not tools:
        print("✗ No tools available from MCP servers!")
        return
    
    # Map MCP Tools to Gemini FunctionDeclarations
    tool_declarations = [
        types.FunctionDeclaration(
            name=tool.name,
            description=tool.description,
            parameters=tool.inputSchema
        ) for tool in tools
    ]
    print(f"✓ Found {len(tool_declarations)} total tools for Gemini\n")

    # 2b. Initialize conversation with the user prompt
    messages = [
        types.Content(
            role="user", 
            parts=[types.Part.from_text(user_prompt)]
        )
    ]
    
    # 2c. Main interaction loop
    iteration = 0
    max_iterations = 10  # Prevent infinite loops
    
    while iteration < max_iterations:
        iteration += 1
        print(f"\n--- Iteration {iteration} ---")
        print("Step 2: Calling Gemini model to decide next action...")
        
        try:
            response = GEMINI_CLIENT.models.generate_content(
                model='gemini-2.5-pro',
                contents=messages,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(function_declarations=tool_declarations)]
                ),
            )
        except Exception as e:
            print(f"✗ Error calling Gemini: {e}")
            import traceback
            traceback.print_exc()
            break

        # Check for model response
        if not hasattr(response, 'function_calls') or not response.function_calls:
            # Model replied with a final text answer
            print("\n" + "="*60)
            print("FINAL RESPONSE:")
            print("="*60)
            print(response.text)
            print("="*60 + "\n")
            break
        
        # 3. Model requests tool calls
        print(f"Step 3: Gemini requested {len(response.function_calls)} tool call(s).")
        
        tool_responses = []
        for call in response.function_calls:
            print(f"\n  → Executing: {call.name}")
            print(f"    Arguments: {json.dumps(dict(call.args), indent=4)}")
            
            try:
                # 4. Execute the tool call via the MCP client
                mcp_result = await call_mcp_tool(gmail_session, calendar_session, call.name, dict(call.args))
                
                # Extract text from MCP TextContent response
                result_text = ""
                if hasattr(mcp_result, 'content'):
                    for content_item in mcp_result.content:
                        if hasattr(content_item, 'text'):
                            result_text = content_item.text
                            break
                elif isinstance(mcp_result, str):
                    result_text = mcp_result
                
                # Parse JSON if it's a JSON string
                try:
                    result_json = json.loads(result_text)
                    result_text = json.dumps(result_json, indent=2)
                except:
                    pass

                tool_responses.append(
                    types.Content(
                        role="function",
                        parts=[
                            types.Part.from_function_response(
                                name=call.name,
                                response=types.FunctionResponse(
                                    name=call.name,
                                    response={"result": result_text}
                                )
                            )
                        ]
                    )
                )
                print(f"  ✓ Tool Success: {call.name}")

            except Exception as e:
                # Handle error from the MCP server
                error_msg = str(e)
                print(f"  ✗ Tool Error: {call.name} - {error_msg}")
                import traceback
                traceback.print_exc()
                
                tool_responses.append(
                    types.Content(
                        role="function",
                        parts=[
                            types.Part.from_function_response(
                                name=call.name,
                                response=types.FunctionResponse(
                                    name=call.name,
                                    response={"error": error_msg}
                                )
                            )
                        ]
                    )
                )

        # 5. Append the model's request and the tool's result to the message history
        if hasattr(response, 'candidates') and response.candidates:
            messages.append(response.candidates[0].content)
        messages.extend(tool_responses)
    
    if iteration >= max_iterations:
        print(f"\n⚠ Maximum iterations ({max_iterations}) reached. Stopping.")

async def main():
    """Main entry point."""
    print("\n" + "="*60)
    print("SCHEDULING AGENT - Starting Up")
    print("="*60)
    
    # Use absolute paths to the server scripts
    gmail_server_path = str(SCRIPT_DIR / "mcp_gmail_server.py")
    calendar_server_path = str(SCRIPT_DIR / "mcp_calendar_server.py")
    
    # Verify files exist
    if not os.path.exists(gmail_server_path):
        print(f"✗ Gmail server file not found: {gmail_server_path}")
        return
    if not os.path.exists(calendar_server_path):
        print(f"✗ Calendar server file not found: {calendar_server_path}")
        return
    
    print(f"\n→ Gmail server: {gmail_server_path}")
    print(f"→ Calendar server: {calendar_server_path}\n")
    
    # Use async with to properly manage context managers
    try:
        async with stdio_client(
            StdioServerParameters(
                command="python3",
                args=[gmail_server_path]
            )
        ) as (gmail_read, gmail_write), \
        stdio_client(
            StdioServerParameters(
                command="python3",
                args=[calendar_server_path]
            )
        ) as (calendar_read, calendar_write):
            
            print("✓ Both servers started")
            print("→ Creating ClientSession objects...")
            
            # Create ClientSession objects from the streams
            async with ClientSession(gmail_read, gmail_write) as gmail_session, \
                      ClientSession(calendar_read, calendar_write) as calendar_session:
                
                print("✓ ClientSession objects created")
                print("→ Initializing sessions...")
                
                # Initialize both sessions
                await gmail_session.initialize()
                await calendar_session.initialize()
                
                print("✓ Both sessions initialized\n")
                
                # Example scheduling prompt - you can modify this
                prompt = """I just got an email from 'Alice' with the subject 'Meeting Request'. 
Find the details of that email, check if I'm free on Tuesday next week at 11:00 AM for 60 minutes, 
and if I am, tell me what the email says and propose booking the meeting. 
Only search for a single, most recent email from Alice with that subject."""
                
                # You can also accept prompts from command line
                if len(sys.argv) > 1:
                    prompt = " ".join(sys.argv[1:])
                
                await run_agent(gmail_session, calendar_session, prompt)
                
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        print("\nTroubleshooting:")
        print("1. Make sure mcp_gmail_server.py and mcp_calendar_server.py exist")
        print("2. Check that credentials.json and token.json are in the directory")
        print("3. Verify Python can execute the server scripts")
        print("4. Try running the servers manually to check for errors:")
        print("   python3 mcp_gmail_server.py")
        print("   python3 mcp_calendar_server.py")

if __name__ == "__main__":
    asyncio.run(main())
