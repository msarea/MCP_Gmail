import os
from datetime import datetime, timedelta, timezone
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events',
]


class CalendarClient:
    def __init__(self, credentials_path=None, token_path=None):
        self.credentials_path = credentials_path or os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
        self.token_path = token_path or os.getenv('CALENDAR_TOKEN_FILE', 'calendar_token.json')
        self.service = None
        self._authenticate()

    def _authenticate(self):
        """Authenticate and build Calendar service."""
        creds = None
        
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        
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
            
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('calendar', 'v3', credentials=creds)

    # ========== CALENDAR READING ==========
    
    def get_calendars(self):
        """Get list of all calendars."""
        try:
            calendars = self.service.calendarList().list().execute()
            return calendars.get('items', [])
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    def get_events(self, calendar_id='primary', time_min=None, time_max=None, max_results=100):
        """Get events from calendar."""
        try:
            if time_min is None:
                time_min = datetime.utcnow().isoformat() + 'Z'
            if time_max is None:
                time_max = (datetime.utcnow() + timedelta(days=30)).isoformat() + 'Z'
            
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            return events_result.get('items', [])
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    def get_busy_times(self, time_min, time_max, calendar_id='primary'):
        """Get busy time slots."""
        try:
            body = {
                "timeMin": time_min,
                "timeMax": time_max,
                "items": [{"id": calendar_id}]
            }
            
            freebusy = self.service.freebusy().query(body=body).execute()
            busy = freebusy['calendars'][calendar_id]['busy']
            return busy
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    # ========== FREE TIME DETECTION ==========
    
    def find_free_slots(self, duration_minutes=30, days_ahead=7, 
                       start_hour=9, end_hour=17, calendar_id='primary'):
        """Find available time slots for meetings."""
        try:
            from datetime import timezone
            
            # Use timezone-aware datetime
            now = datetime.now(timezone.utc)
            time_min = now.isoformat().replace('+00:00', 'Z')
            time_max = (now + timedelta(days=days_ahead)).isoformat().replace('+00:00', 'Z')
            
            # Get busy times
            busy_times = self.get_busy_times(time_min, time_max, calendar_id)
            
            # Generate potential slots
            free_slots = []
            current_date = now.replace(hour=start_hour, minute=0, second=0, microsecond=0)
            end_date = now + timedelta(days=days_ahead)
            
            while current_date < end_date:
                # Skip weekends (optional - remove if you want weekends)
                if current_date.weekday() < 5:  # Monday = 0, Friday = 4
                    slot_start = current_date
                    slot_end = slot_start + timedelta(minutes=duration_minutes)
                    
                    # Check if slot overlaps with busy times
                    is_free = True
                    for busy in busy_times:
                        # Parse busy times as timezone-aware
                        busy_start_str = busy['start'].replace('Z', '+00:00')
                        busy_end_str = busy['end'].replace('Z', '+00:00')
                        busy_start = datetime.fromisoformat(busy_start_str)
                        busy_end = datetime.fromisoformat(busy_end_str)
                        
                        # Make sure both are timezone-aware for comparison
                        if slot_start.tzinfo is None:
                            slot_start = slot_start.replace(tzinfo=timezone.utc)
                        if slot_end.tzinfo is None:
                            slot_end = slot_end.replace(tzinfo=timezone.utc)
                        
                        if (slot_start < busy_end and slot_end > busy_start):
                            is_free = False
                            break
                    
                    # Check if within working hours
                    if slot_start.hour >= start_hour and slot_end.hour <= end_hour:
                        if is_free:
                            free_slots.append({
                                'start': slot_start.isoformat(),
                                'end': slot_end.isoformat(),
                                'duration_minutes': duration_minutes
                            })
                
                # Move to next slot
                current_date += timedelta(minutes=30)
                
                # Reset to start of next day if past end hour
                if current_date.hour >= end_hour:
                    current_date = (current_date + timedelta(days=1)).replace(
                        hour=start_hour, minute=0, second=0, microsecond=0
                    )
            
            return free_slots[:10]  # Return top 10 slots
        except Exception as e:
            raise Exception(f"An error occurred: {e}")
            
    # ========== MEETING CREATION ==========
    
    def create_event(self, summary, start_time, end_time, attendees=None, 
                    description='', location='', calendar_id='primary'):
        """Create a calendar event."""
        try:
            event = {
                'summary': summary,
                'description': description,
                'location': location,
                'start': {
                    'dateTime': start_time,
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_time,
                    'timeZone': 'UTC',
                },
                'attendees': [{'email': email} for email in (attendees or [])],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                        {'method': 'popup', 'minutes': 15},  # 15 min before
                    ],
                },
            }
            
            event = self.service.events().insert(
                calendarId=calendar_id,
                body=event,
                sendUpdates='all'  # Send invites to attendees
            ).execute()
            
            return {
                'id': event['id'],
                'htmlLink': event.get('htmlLink'),
                'summary': event['summary'],
                'start': event['start']['dateTime'],
                'attendees': [a.get('email') for a in event.get('attendees', [])]
            }
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    def update_event(self, event_id, summary=None, start_time=None, end_time=None,
                    attendees=None, description=None, calendar_id='primary'):
        """Update an existing event."""
        try:
            event = self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            if summary:
                event['summary'] = summary
            if start_time:
                event['start']['dateTime'] = start_time
            if end_time:
                event['end']['dateTime'] = end_time
            if description:
                event['description'] = description
            if attendees:
                event['attendees'] = [{'email': email} for email in attendees]
            
            updated_event = self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event,
                sendUpdates='all'
            ).execute()
            
            return updated_event
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    def delete_event(self, event_id, calendar_id='primary'):
        """Delete a calendar event."""
        try:
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id,
                sendUpdates='all'
            ).execute()
            return {'success': True, 'event_id': event_id}
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    # ========== MEETING REQUESTS ==========
    
    def schedule_meeting_from_request(self, requester_email, subject, 
                                     preferred_times=None, duration_minutes=30):
        """Schedule a meeting based on a request."""
        try:
            # Find free slots
            free_slots = self.find_free_slots(duration_minutes=duration_minutes)
            
            if not free_slots:
                return {'error': 'No available time slots found'}
            
            # Use first available slot (or preferred time if available)
            selected_slot = free_slots[0]
            if preferred_times:
                # Try to match preferred time
                for slot in free_slots:
                    slot_time = datetime.fromisoformat(slot['start'])
                    for pref_time in preferred_times:
                        pref_datetime = datetime.fromisoformat(pref_time)
                        if abs((slot_time - pref_datetime).total_seconds()) < 3600:  # Within 1 hour
                            selected_slot = slot
                            break
            
            # Create event
            event = self.create_event(
                summary=subject,
                start_time=selected_slot['start'],
                end_time=selected_slot['end'],
                attendees=[requester_email],
                description=f'Meeting requested by {requester_email}'
            )
            
            return {
                'success': True,
                'event': event,
                'alternative_slots': free_slots[1:5]  # Show alternatives
            }
        except Exception as e:
            raise Exception(f"An error occurred: {e}")
