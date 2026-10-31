# MCP Gmail Server

An MCP (Model Context Protocol) server that provides Gmail integration for reading emails and sending replies.

## Setup

### 1. Install Dependencies

```bash
python3 -m pip install -r requirements.txt
```

### 2. Set Up Gmail API Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Gmail API:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Gmail API" and enable it
4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Desktop app" as the application type
   - Download the credentials file and save it as `credentials.json` in the project directory

### 3. First Run Authentication

When you first run the server, it will:
1. Open a browser window for Google OAuth authentication
2. Ask you to sign in and grant permissions
3. Save separate Gmail and Calendar tokens (`gmail_token.json` and `calendar_token.json`) for future use

The first authorization after this update asks for narrower permissions. Gmail uses `gmail.modify`; Calendar uses `calendar.readonly` and `calendar.events`. Existing `token.json` grants are not reused. If Google reports an old grant, revoke the previous app access in your Google Account and authorize again.

### 4. Run the MCP Server

```bash
python3 mcp_gmail_server.py
```

## Available Tools

### `get_unread_emails`
Get a list of unread emails from your inbox.

**Parameters:**
- `max_results` (optional): Maximum number of emails to return (default: 10)

### `get_email_details`
Get full details of a specific email including subject, sender, body, and headers.

**Parameters:**
- `message_id` (required): The Gmail message ID

### `send_reply`
Send a reply to an email. Automatically extracts recipient and subject from the original message.

**Parameters:**
- `message_id` (required): The Gmail message ID to reply to
- `reply_text` (required): The text content of the reply

### `list_emails`
List emails with optional Gmail search query.

**Parameters:**
- `query` (optional): Gmail search query (e.g., "from:example@gmail.com", "subject:meeting")
- `max_results` (optional): Maximum number of emails to return (default: 10)

## Usage Example

The MCP server can be used with any MCP-compatible client. Example tool calls:

```json
{
  "tool": "get_unread_emails",
  "arguments": {"max_results": 5}
}
```

```json
{
  "tool": "send_reply",
  "arguments": {
    "message_id": "1234567890",
    "reply_text": "Thank you for your email. I'll get back to you soon."
  }
}
```

## Security Notes

- Keep `credentials.json` and all OAuth token files secure and never commit them to version control
- `gmail_token.json` and `calendar_token.json` contain OAuth tokens and are ignored by Git
- Only grant necessary permissions when authenticating
- The Flask interface can read, send, and delete email. It binds to localhost with debug mode disabled. Do not expose it to a network without adding authentication and using an appropriate deployment server.

## Troubleshooting

- **"Credentials file not found"**: Make sure `credentials.json` is in the project directory
- **Authentication errors**: Delete the relevant token file (`gmail_token.json` or `calendar_token.json`) and re-authenticate
- **Permission errors**: Make sure you've granted the necessary Gmail permissions during OAuth

## Search and location tools

`get_weather` and `get_location_info` use Open-Meteo geocoding and forecast endpoints. `search_web` requires a `BRAVE_SEARCH_API_KEY`; `find_places` requires a Google Maps API key in `GOOGLE_MAPS_API_KEY`. These tools return a clear configuration error when a required key is missing instead of presenting placeholder results as real search results.
