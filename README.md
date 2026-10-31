# MCP Gmail Server

An MCP (Model Context Protocol) server that provides Gmail integration for reading emails and sending replies.

## Setup

### 1. Install Dependencies

pip install -r requirements.txt### 2. Set Up Gmail API Credentials

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
3. Save the token to `token.json` for future use

### 4. Run the MCP Server
ash
python mcp_gmail_server.py## Available Tools

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

{
  "tool": "get_unread_emails",
  "arguments": {"max_results": 5}
}
{
  "tool": "send_reply",
  "arguments": {
    "message_id": "1234567890",
    "reply_text": "Thank you for your email. I'll get back to you soon."
  }
}## Security Notes

- Keep `credentials.json` and `token.json` secure and never commit them to version control
- The `token.json` file contains your OAuth tokens and should be kept private
- Only grant necessary permissions when authenticating

## Troubleshooting

- **"Credentials file not found"**: Make sure `credentials.json` is in the project directory
- **Authentication errors**: Delete `token.json` and re-authenticate
- **Permission errors**: Make sure you've granted the necessary Gmail permissions during OAuth
