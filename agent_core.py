# --- agent_core.py ---

import json
import re
from datetime import datetime, timedelta
from google import genai
from google.genai import types

# Initialize Gemini Client (reads GEMINI_API_KEY from environment)
try:
    GEMINI_CLIENT = genai.Client()
except Exception as e:
    print(f"Warning: Gemini Client failed to initialize. Set GEMINI_API_KEY. Error: {e}")
    GEMINI_CLIENT = None

def extract_meeting_details(email_body: str, email_subject: str) -> dict:
    """
    Uses Gemini's structured output capability to reliably extract
    meeting intent and details from the email text.
    """
    if not GEMINI_CLIENT:
        print("Gemini client not available. Skipping AI extraction.")
        return {"intent": "OTHER"}

    # Define the precise JSON output format (Schema)
    meeting_schema = types.Schema(
        type=types.Type.OBJECT,
        properties={
            "intent": types.Schema(
                type=types.Type.STRING,
                description="The purpose. Must be one of: 'SCHEDULE_MEETING', 'CONFIRM_TIME', 'REQUEST_INFO', or 'OTHER'."
            ),
            "title": types.Schema(
                type=types.Type.STRING,
                description="The suggested title for the calendar event (e.g., 'Q3 Review Call'). Default to subject if none found."
            ),
            "duration_minutes": types.Schema(
                type=types.Type.INTEGER,
                description="The required or proposed duration in minutes (e.g., 30, 60, 90). Default to 30 if uncertain."
            ),
            "proposed_times": types.Schema(
                type=types.Type.ARRAY,
                items=types.Schema(type=types.Type.STRING),
                description="A list of specific dates/times mentioned by the sender for the meeting, formatted in ISO 8601 UTC (e.g., '2025-12-10T14:30:00Z'). If a specific time is not given, use a general phrase like 'next week Monday morning'."
            ),
        },
        required=["intent", "title", "duration_minutes", "proposed_times"]
    )

    # Craft the Prompt - Natural, conversational tone
    prompt = f"""
    Analyze the following email subject and body to understand what the sender wants.
    If they're trying to schedule something, pull out the meeting details.
    If there's no specific time mentioned, make a reasonable guess (like 'next week').
    
    SUBJECT: {email_subject}
    BODY:
    ---
    {email_body}
    ---
    
    Return the result as a JSON object matching the provided schema.
    """

    # Call Gemini API
    try:
        response = GEMINI_CLIENT.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=meeting_schema,
            ),
        )
        # Parse the AI's structured response
        return json.loads(response.text)
    
    except Exception as e:
        print(f"Error during Gemini extraction: {e}")
        return {"intent": "OTHER"}


def generate_reply_text(meeting_details: dict, action_result: dict) -> str:
    """Uses Gemini to generate a human-like reply based on the action taken."""
    if not GEMINI_CLIENT:
        return "Hey, thanks for reaching out! I'm having some technical hiccups right now, but I'll get back to you as soon as I can sort this out."
        
    action_type = action_result.get('action')
    
    # Natural, conversational prompt - avoid robotic language
    prompt = f"""
    Write a short email (2-3 sentences) about the meeting. Write like a real person, not an AI assistant.

    CRITICAL RULES - Sound human:
    1. ALWAYS use contractions: I'm, you're, we'll, that's, don't, can't, won't, I've, you've
    2. Write like you're texting - casual and direct
    3. NEVER use these robotic phrases:
       ❌ "I have successfully completed"
       ❌ "I would be happy to assist"
       ❌ "Please be advised"
       ❌ "I have reviewed your request"
       ❌ "The system has processed"
       ✅ Instead say: "Done!", "Got it!", "I checked that", "Here's what I found"
    
    4. Vary your sentences - mix short and long
    5. Use everyday words, not corporate jargon
    6. Sound like a busy but friendly colleague, not a perfect robot
    
    Meeting: {meeting_details.get('title', 'A discussion')}
    Duration: {meeting_details.get('duration_minutes', 30)} minutes
    Action: {action_type}
    
    If BOOKED:
        Time: {action_result.get('start_time', 'N/A')}
        Write like: "Hey! Got you booked for [time]. See you then!"
        
    If PROPOSED_ALTERNATIVES:
        Slots: {action_result.get('alternative_slots', 'N/A')}
        Write like: "That time doesn't work for me, but I'm free [alternatives]. Any of those work?"

    Remember: You're a person, not a bot. Write like you're actually talking.
    """
    
    try:
        response = GEMINI_CLIENT.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f"Error generating reply: {e}")
        return "Got it! I'm checking on this now and will get back to you with the details soon."
