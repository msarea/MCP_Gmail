import os
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']


class GmailClient:
    def __init__(self, credentials_path='credentials.json', token_path='token.json'):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self._authenticate()

    def _authenticate(self):
        """Authenticate and build Gmail service."""
        creds = None
        
        # Load existing token if available
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Credentials file not found: {self.credentials_path}\n"
                        "Please download credentials.json from Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('gmail', 'v1', credentials=creds)

    def get_unread_emails(self, max_results=10):
        """Get list of unread emails."""
        try:
            results = self.service.users().messages().list(
                userId='me',
                labelIds=['INBOX'],
                q='is:unread',
                maxResults=max_results
            ).execute()
            messages = results.get('messages', [])
            return messages
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    def get_email_details(self, message_id):
        """Get full details of an email message."""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            payload = message['payload']
            headers = payload.get('headers', [])
            
            # Extract headers
            email_data = {
                'id': message_id,
                'threadId': message.get('threadId'),
                'snippet': message.get('snippet', ''),
                'headers': {}
            }
            
            for header in headers:
                name = header['name'].lower()
                email_data['headers'][name] = header['value']
            
            # Extract body
            body = ''
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body']['data']
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
                        break
                    elif part['mimeType'] == 'text/html' and not body:
                        data = part['body']['data']
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
            else:
                if payload['mimeType'] == 'text/plain':
                    data = payload['body']['data']
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
            
            email_data['body'] = body
            return email_data
            
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    def send_reply(self, message_id, reply_text):
        """Send a reply to an email."""
        try:
            # Get original message
            original_message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            headers = original_message['payload']['headers']
            
            # Extract necessary headers
            subject = None
            sender = None
            message_id_header = None
            
            for header in headers:
                name = header['name'].lower()
                if name == 'subject':
                    subject = header['value']
                elif name == 'from':
                    sender = header['value']
                elif name == 'message-id':
                    message_id_header = header['value']
            
            if not subject or not sender:
                raise ValueError("Could not extract subject or sender from original message")
            
            # Create reply message
            reply_subject = f"Re: {subject}"
            
            message = MIMEText(reply_text)
            message['to'] = sender
            message['subject'] = reply_subject
            
            if message_id_header:
                message['In-Reply-To'] = message_id_header
                message['References'] = message_id_header
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Send message
            send_message = {'raw': raw_message}
            sent_message = self.service.users().messages().send(
                userId='me',
                body=send_message
            ).execute()
            
            # Mark original as read
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            
            return {
                'id': sent_message['id'],
                'threadId': sent_message.get('threadId'),
                'subject': reply_subject,
                'to': sender
            }
            
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    def list_emails(self, query='', max_results=10):
        """List emails with optional query filter."""
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            messages = results.get('messages', [])
            return messages
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")
