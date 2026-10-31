import os
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']


class GmailClient:
    def __init__(self, credentials_path=None, token_path=None):
        self.credentials_path = credentials_path or os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
        self.token_path = token_path or os.getenv('GMAIL_TOKEN_FILE', 'gmail_token.json')
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

    # ========== EMAIL READING ==========
    
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

    def search_emails(self, query, max_results=10, date_from=None, date_to=None):
        """Advanced email search with date range."""
        try:
            full_query = query
            if date_from:
                full_query += f" after:{date_from}"
            if date_to:
                full_query += f" before:{date_to}"
            
            results = self.service.users().messages().list(
                userId='me',
                q=full_query,
                maxResults=max_results
            ).execute()
            messages = results.get('messages', [])
            return messages
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    # ========== EMAIL STATUS MANAGEMENT ==========
    
    def mark_as_read(self, message_id):
        """Mark an email as read."""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            return {'success': True, 'message_id': message_id, 'status': 'read'}
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    def mark_as_unread(self, message_id):
        """Mark an email as unread."""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': ['UNREAD']}
            ).execute()
            return {'success': True, 'message_id': message_id, 'status': 'unread'}
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    def archive_email(self, message_id):
        """Archive an email (remove from inbox)."""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['INBOX']}
            ).execute()
            return {'success': True, 'message_id': message_id, 'action': 'archived'}
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    def unarchive_email(self, message_id):
        """Unarchive an email (add back to inbox)."""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': ['INBOX']}
            ).execute()
            return {'success': True, 'message_id': message_id, 'action': 'unarchived'}
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    def star_email(self, message_id):
        """Star an email."""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': ['STARRED']}
            ).execute()
            return {'success': True, 'message_id': message_id, 'action': 'starred'}
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    def unstar_email(self, message_id):
        """Unstar an email."""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['STARRED']}
            ).execute()
            return {'success': True, 'message_id': message_id, 'action': 'unstarred'}
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    def mark_as_spam(self, message_id):
        """Mark an email as spam."""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': ['SPAM']}
            ).execute()
            return {'success': True, 'message_id': message_id, 'action': 'marked_as_spam'}
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    def mark_as_not_spam(self, message_id):
        """Mark an email as not spam."""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['SPAM']}
            ).execute()
            return {'success': True, 'message_id': message_id, 'action': 'marked_as_not_spam'}
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    # ========== EMAIL SENDING ==========
    
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

    def send_email(self, to, subject, body, cc=None, bcc=None, attachments=None):
        """Send a new email (not a reply)."""
        try:
            message = MIMEMultipart()
            message['to'] = ', '.join(to) if isinstance(to, list) else to
            message['subject'] = subject
            
            if cc:
                message['cc'] = ', '.join(cc) if isinstance(cc, list) else cc
            if bcc:
                message['bcc'] = ', '.join(bcc) if isinstance(bcc, list) else bcc
            
            message.attach(MIMEText(body, 'plain'))
            
            # Handle attachments
            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        with open(file_path, 'rb') as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename= {os.path.basename(file_path)}'
                            )
                            message.attach(part)
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            send_message = {'raw': raw_message}
            
            sent_message = self.service.users().messages().send(
                userId='me',
                body=send_message
            ).execute()
            
            return {
                'id': sent_message['id'],
                'threadId': sent_message.get('threadId'),
                'subject': subject,
                'to': to
            }
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    def forward_email(self, message_id, to, forward_text=""):
        """Forward an email to another recipient."""
        try:
            # Get original message
            original_message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            headers = original_message['payload']['headers']
            original_subject = None
            original_from = None
            
            for header in headers:
                name = header['name'].lower()
                if name == 'subject':
                    original_subject = header['value']
                elif name == 'from':
                    original_from = header['value']
            
            # Get email body
            email_details = self.get_email_details(message_id)
            original_body = email_details.get('body', '')
            
            # Create forward message
            forward_subject = f"Fwd: {original_subject}"
            body = f"{forward_text}\n\n---------- Forwarded message ----------\nFrom: {original_from}\nSubject: {original_subject}\n\n{original_body}"
            
            message = MIMEText(body)
            message['to'] = ', '.join(to) if isinstance(to, list) else to
            message['subject'] = forward_subject
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            send_message = {'raw': raw_message}
            
            sent_message = self.service.users().messages().send(
                userId='me',
                body=send_message
            ).execute()
            
            return {
                'id': sent_message['id'],
                'threadId': sent_message.get('threadId'),
                'subject': forward_subject,
                'to': to
            }
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    # ========== DRAFTS ==========
    
    def create_draft(self, to, subject, body):
        """Create a draft email."""
        try:
            message = MIMEText(body)
            message['to'] = ', '.join(to) if isinstance(to, list) else to
            message['subject'] = subject
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            draft_message = {'message': {'raw': raw_message}}
            
            draft = self.service.users().drafts().create(
                userId='me',
                body=draft_message
            ).execute()
            
            return {
                'id': draft['id'],
                'message_id': draft['message']['id'],
                'subject': subject
            }
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    def get_drafts(self, max_results=10):
        """Get list of draft emails."""
        try:
            results = self.service.users().drafts().list(
                userId='me',
                maxResults=max_results
            ).execute()
            drafts = results.get('drafts', [])
            return drafts
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    def send_draft(self, draft_id):
        """Send a draft email."""
        try:
            draft = self.service.users().drafts().send(
                userId='me',
                body={'id': draft_id}
            ).execute()
            
            return {
                'id': draft['message']['id'],
                'threadId': draft['message'].get('threadId')
            }
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    # ========== DELETION ==========
    
    def delete_email(self, message_id):
        """Move a single email to Trash by message ID."""
        try:
            self.service.users().messages().trash(
                userId='me',
                id=message_id
            ).execute()
            return {'success': True, 'message_id': message_id, 'action': 'trashed'}
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    def delete_emails_from_sender(self, sender_email, max_results=100):
        """Move emails from a specific sender to Trash."""
        try:
            query = f'from:{sender_email}'
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            trashed_count = 0
            failed_ids = []
            
            for message in messages:
                try:
                    self.service.users().messages().trash(
                        userId='me',
                        id=message['id']
                    ).execute()
                    trashed_count += 1
                except Exception as e:
                    print(f"Failed to trash {message['id']}: {e}")

                    failed_ids.append(message['id'])
            
            return {
                'success': True,
                'trashed_count': trashed_count,
                'total_found': len(messages),
                'failed_ids': failed_ids
            }
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    def delete_emails_batch(self, message_ids):
        """Move multiple emails to Trash by their IDs."""
        trashed_count = 0
        failed_ids = []
        
        for message_id in message_ids:
            try:
                self.service.users().messages().trash(
                    userId='me',
                    id=message_id
                ).execute()
                trashed_count += 1
            except Exception as e:
                failed_ids.append(message_id)
        
        return {
            'success': True,
            'trashed_count': trashed_count,
            'total_requested': len(message_ids),
            'failed_ids': failed_ids
        }

    # ========== LABELS ==========
    
    def list_labels(self):
        """Get list of all labels."""
        try:
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            return labels
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    def create_label(self, name):
        """Create a new label."""
        try:
            label = self.service.users().labels().create(
                userId='me',
                body={'name': name}
            ).execute()
            return label
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    def add_label_to_email(self, message_id, label_id):
        """Add a label to an email."""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': [label_id]}
            ).execute()
            return {'success': True, 'message_id': message_id, 'label_id': label_id}
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    def remove_label_from_email(self, message_id, label_id):
        """Remove a label from an email."""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': [label_id]}
            ).execute()
            return {'success': True, 'message_id': message_id, 'label_id': label_id}
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    def get_emails_by_label(self, label_id, max_results=10):
        """Get emails with a specific label."""
        try:
            results = self.service.users().messages().list(
                userId='me',
                labelIds=[label_id],
                maxResults=max_results
            ).execute()
            messages = results.get('messages', [])
            return messages
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    # ========== THREADS ==========
    
    def get_thread(self, thread_id):
        """Get all messages in a thread."""
        try:
            thread = self.service.users().threads().get(
                userId='me',
                id=thread_id,
                format='full'
            ).execute()
            return thread
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    def delete_thread(self, thread_id):
        """Move an entire thread to Trash."""
        try:
            self.service.users().threads().trash(
                userId='me',
                id=thread_id
            ).execute()
            return {'success': True, 'thread_id': thread_id, 'action': 'trashed'}
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    def archive_thread(self, thread_id):
        """Archive an entire thread."""
        try:
            self.service.users().threads().modify(
                userId='me',
                id=thread_id,
                body={'removeLabelIds': ['INBOX']}
            ).execute()
            return {'success': True, 'thread_id': thread_id, 'action': 'archived'}
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    # ========== ATTACHMENTS ==========
    
    def get_attachments(self, message_id):
        """Get list of attachments in an email."""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            attachments = []
            payload = message['payload']
            
            def extract_attachments(parts):
                for part in parts:
                    if part.get('filename'):
                        attachments.append({
                            'filename': part['filename'],
                            'mimeType': part['mimeType'],
                            'size': part['body'].get('size', 0),
                            'attachmentId': part['body'].get('attachmentId')
                        })
                    if 'parts' in part:
                        extract_attachments(part['parts'])
            
            if 'parts' in payload:
                extract_attachments(payload['parts'])
            
            return attachments
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    def download_attachment(self, message_id, attachment_id, filename):
        """Download an attachment from an email."""
        try:
            attachment = self.service.users().messages().attachments().get(
                userId='me',
                messageId=message_id,
                id=attachment_id
            ).execute()
            
            file_data = base64.urlsafe_b64decode(attachment['data'])
            
            with open(filename, 'wb') as f:
                f.write(file_data)
            
            return {'success': True, 'filename': filename, 'size': len(file_data)}
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    # ========== STATISTICS ==========
    
    def get_email_count(self, query=''):
        """Get count of emails matching a query."""
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=1
            ).execute()
            return results.get('resultSizeEstimate', 0)
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    def get_unread_count(self):
        """Get count of unread emails."""
        return self.get_email_count('is:unread')

    def get_stats(self):
        """Get email statistics."""
        try:
            return {
                'total_emails': self.get_email_count(),
                'unread_emails': self.get_unread_count(),
                'inbox_emails': self.get_email_count('in:inbox'),
                'starred_emails': self.get_email_count('is:starred')
            }
        except Exception as e:
            raise Exception(f"An error occurred: {e}")
