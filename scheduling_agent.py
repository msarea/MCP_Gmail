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
from location_helper import get_location_coordinates

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

# Use gemini-1.5-flash-latest (free tier, fast)
GEMINI_MODEL = 'gemini-2.5-flash-lite'

# Get the script directory for absolute paths
SCRIPT_DIR = Path(__file__).parent.absolute()

async def get_all_tools(gmail_session, calendar_session, search_session=None):
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
    
    if search_session:
        try:
            print("  → Getting Search tools...")
            search_tools_result = await search_session.list_tools()
            all_tools.extend(search_tools_result.tools)
            print(f"  ✓ Found {len(search_tools_result.tools)} Search tools")
        except Exception as e:
            print(f"  ✗ Error getting Search tools: {e}")
            import traceback
            traceback.print_exc()
    
    return all_tools

async def call_mcp_tool(gmail_session, calendar_session, search_session, tool_name: str, arguments: dict):
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
            # Tool not found in Calendar, try Search
            pass
    
    # Try Search server
    if search_session:
        try:
            result = await search_session.call_tool(tool_name, arguments)
            return result
        except Exception as e:
            pass
    
    raise Exception(f"Tool '{tool_name}' not found in any server")

# --- 2. Main Agent Logic ---

async def run_agent(gmail_session, calendar_session, search_session, user_prompt: str):
    """Main agent loop that processes user requests using Gemini and MCP tools."""
    print(f"\n{'='*60}")
    print(f"User Request: {user_prompt}")
    print(f"{'='*60}\n")

    # 2a. Get available tools from all connected MCP servers
    print("Step 1: Connecting to MCP servers and collecting tools...")
    tools = await get_all_tools(gmail_session, calendar_session, search_session)
    
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

    # 2b. Extract location from prompt for location-based search
    # Optionally use Google Geocoding API for accurate results
    # Set GOOGLE_MAPS_API_KEY environment variable and use_google_api=True to enable
    google_maps_key = os.getenv('GOOGLE_MAPS_API_KEY')
    use_google_geocoding = google_maps_key is not None
    
    location_coords = get_location_coordinates(
        user_prompt,
        use_google_api=use_google_geocoding,
        api_key=google_maps_key
    )
    if location_coords:
        print(f"  → Detected location: {location_coords}")
    elif use_google_geocoding:
        print("  → Location extraction attempted (Google Geocoding API enabled)")
    
    # 2c. Initialize conversation with the user prompt
    # Add a system instruction for natural, conversational tone
    system_instruction = """You're a helpful assistant that can help with MANY things:
- Emails and calendar scheduling (you have tools for these)
- General questions and information
- Location-based searches (restaurants, businesses, places, weather, local info, etc.)
- Web searches and current information
- ANY question the user asks

IMPORTANT: You are NOT limited to just emails and calendar. You can help with ANYTHING the user asks about. If they ask about restaurants, weather, places, or general information, provide helpful answers using your knowledge and any location context provided.

CRITICAL: Write like a REAL HUMAN, not a robot or AI assistant.

MANDATORY RULES:
1. ALWAYS use contractions: I'm, you're, we'll, that's, don't, can't, won't, I've, you've, we've, they're
2. Write casually - like texting a friend or colleague
3. Mix sentence lengths - some short punchy ones, some longer
4. Use everyday words, never corporate jargon
5. Be direct and friendly, not formal
6. Vary your phrasing - never repeat the same sentence patterns

NEVER USE THESE ROBOTIC PHRASES:
❌ "I have successfully..." → ✅ "Done!" or "Got it!"
❌ "I would be happy to assist" → ✅ "Happy to help!" or "Sure thing!"
❌ "Please be advised that" → ✅ "Just so you know" or "FYI"
❌ "I have reviewed your request" → ✅ "I checked that" or "Looked into it"
❌ "The system has processed" → ✅ "I've got that" or "All set"
❌ "I would like to inform you" → ✅ "Just wanted to let you know"
❌ "In accordance with" → ✅ "Based on" or just skip it

EXAMPLES:

BAD (robotic): "I have successfully retrieved your emails. I would be happy to assist you further with any additional requests you may have."
GOOD (natural): "Got your emails! What do you need help with?"

BAD (robotic): "I have reviewed your calendar and found that you are available on Tuesday at 2:00 PM."
GOOD (natural): "Checked your calendar - you're free Tuesday at 2pm if that works."

BAD (robotic): "The meeting has been scheduled successfully. Please find the details below."
GOOD (natural): "All set! I've got you booked. Here are the details:"

BAD (robotic): "I have completed the task as requested."
GOOD (natural): "Done! That's all taken care of."

Remember: You're a person helping another person. Write like you're actually talking, not like you're generating corporate emails or customer service responses.

CRITICAL RULES FOR LOCATION-BASED QUERIES:
- When users ask about restaurants, businesses, places, weather, or local information, ALWAYS help them
- Use the location context provided in the prompt if available
- Provide helpful, natural responses based on your knowledge
- If you have location coordinates, use them to give location-relevant information
- You can help with ANY question - you are NOT restricted to emails and calendar only
- Be helpful and informative - don't refuse to help with general questions
- If asked about a location, use your knowledge to provide useful information about that area\n\n"""
    
    # 2d. Add location context to prompt if location was detected
    # Note: Google Search/Maps tools cannot be mixed with function calling tools
    # Instead, we pass location in the prompt so Gemini can use it for context
    location_context = ""
    if location_coords:
        location_context = f"\n\n[Location Context: The user's location is approximately {location_coords['latitude']}, {location_coords['longitude']}. When searching for information, prioritize results relevant to this location. If the user asks about places, businesses, or local information, use this location for context.]"
        print(f"  ✓ Location context added to prompt: {location_coords['latitude']}, {location_coords['longitude']}")
    
    # 2e. Prepend system instruction and append location context to user prompt
    enhanced_prompt = system_instruction + user_prompt + location_context
    
    messages = [
        types.Content(
            role="user", 
            parts=[types.Part(text=enhanced_prompt)]
        )
    ]
    
    # 2f. Prepare tools - Note: Google Search/Maps cannot be mixed with function calling
    # We'll use function declarations (MCP tools) only
    all_tools_list = [types.Tool(function_declarations=tool_declarations)]
    
    # 2g. Main interaction loop
    iteration = 0
    max_iterations = 10  # Prevent infinite loops
    
    while iteration < max_iterations:
        iteration += 1
        print(f"\n--- Iteration {iteration} ---")
        print(f"Step 2: Calling Gemini model ({GEMINI_MODEL}) to decide next action...")
        
        try:
            # Build config with tools (function calling only - Google Search/Maps not compatible)
            response = GEMINI_CLIENT.models.generate_content(
                model=GEMINI_MODEL,
                contents=messages,
                config=types.GenerateContentConfig(
                    tools=all_tools_list
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
                mcp_result = await call_mcp_tool(gmail_session, calendar_session, search_session, call.name, dict(call.args))
                
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

                # Create function response - pass dict directly, not FunctionResponse object
                tool_responses.append(
                    types.Content(
                        role="function",
                        parts=[
                            types.Part.from_function_response(
                                name=call.name,
                                response={"result": result_text}
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
                
                # Create error response - pass dict directly
                tool_responses.append(
                    types.Content(
                        role="function",
                        parts=[
                            types.Part.from_function_response(
                                name=call.name,
                                response={"error": error_msg}
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
    search_server_path = str(SCRIPT_DIR / "mcp_search_server.py")
    
    # Verify files exist
    if not os.path.exists(gmail_server_path):
        print(f"✗ Gmail server file not found: {gmail_server_path}")
        return
    if not os.path.exists(calendar_server_path):
        print(f"✗ Calendar server file not found: {calendar_server_path}")
        return
    if not os.path.exists(search_server_path):
        print(f"⚠ Search server file not found: {search_server_path}")
        print("  → Search functionality will be limited")
        search_server_path = None
    
    print(f"\n→ Gmail server: {gmail_server_path}")
    print(f"→ Calendar server: {calendar_server_path}")
    if search_server_path:
        print(f"→ Search server: {search_server_path}")
    print()
    
    # Use async with to properly manage context managers
    try:
        # Start Gmail and Calendar servers
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
            
            # Start Search server if available
            if search_server_path:
                async with stdio_client(
                    StdioServerParameters(
                        command="python3",
                        args=[search_server_path]
                    )
                ) as (search_read, search_write):
                    print("✓ All servers started")
                    print("→ Creating ClientSession objects...")
                    
                    # Create ClientSession objects from the streams
                    async with ClientSession(gmail_read, gmail_write) as gmail_session, \
                              ClientSession(calendar_read, calendar_write) as calendar_session, \
                              ClientSession(search_read, search_write) as search_session:
                        
                        print("✓ ClientSession objects created")
                        print("→ Initializing sessions...")
                        
                        # Initialize all sessions
                        await gmail_session.initialize()
                        await calendar_session.initialize()
                        await search_session.initialize()
                        
                        print("✓ All sessions initialized\n")
                        
                        # Example scheduling prompt - you can modify this
                        prompt = """I just got an email from 'Alice' with the subject 'Meeting Request'. 
Find the details of that email, check if I'm free on Tuesday next week at 11:00 AM for 60 minutes, 
and if I am, tell me what the email says and propose booking the meeting. 
Only search for a single, most recent email from Alice with that subject."""
                        
                        # You can also accept prompts from command line
                        if len(sys.argv) > 1:
                            prompt = " ".join(sys.argv[1:])
                        
                        await run_agent(gmail_session, calendar_session, search_session, prompt)
            else:
                # Fallback: Run without search server
                print("✓ Gmail and Calendar servers started")
                print("→ Creating ClientSession objects...")
                
                async with ClientSession(gmail_read, gmail_write) as gmail_session, \
                          ClientSession(calendar_read, calendar_write) as calendar_session:
                    
                    print("✓ ClientSession objects created")
                    print("→ Initializing sessions...")
                    
                    await gmail_session.initialize()
                    await calendar_session.initialize()
                    
                    print("✓ Sessions initialized (Search server not available)\n")
                    
                    # Example scheduling prompt
                    prompt = """I just got an email from 'Alice' with the subject 'Meeting Request'. 
Find the details of that email, check if I'm free on Tuesday next week at 11:00 AM for 60 minutes, 
and if I am, tell me what the email says and propose booking the meeting. 
Only search for a single, most recent email from Alice with that subject."""
                    
                    if len(sys.argv) > 1:
                        prompt = " ".join(sys.argv[1:])
                    
                    await run_agent(gmail_session, calendar_session, None, prompt)
                
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        print("\nTroubleshooting:")
        print("1. Make sure mcp_gmail_server.py and mcp_calendar_server.py exist")
        print("2. Check credentials.json and the Gmail/Calendar token files are available")
        print("3. Verify Python can execute the server scripts")
        print("4. Try running the servers manually to check for errors:")
        print("   python3 mcp_gmail_server.py")
        print("   python3 mcp_calendar_server.py")

if __name__ == "__main__":
    asyncio.run(main())
