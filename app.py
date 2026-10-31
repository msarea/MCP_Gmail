#!/usr/bin/env python3
"""
Flask Web Application for Gmail MCP Server
Provides web interface for all Gmail and Calendar functionality
Includes AI Scheduling Agent interface
"""

from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from gmail_client import GmailClient
from calendar_client import CalendarClient
import os
import subprocess
import json

app = Flask(__name__)

# Initialize Gmail client
gmail_client = None

def get_gmail_client():
    """Get or initialize Gmail client."""
    global gmail_client
    if gmail_client is None:
        try:
            gmail_client = GmailClient()
        except Exception as e:
            return None
    return gmail_client

# Initialize calendar client
calendar_client = None

def get_calendar_client():
    """Get or initialize Calendar client."""
    global calendar_client
    if calendar_client is None:
        try:
            calendar_client = CalendarClient()
        except Exception as e:
            return None
    return calendar_client

# ========== MAIN ROUTES ==========

@app.route('/')
def index():
    """Serve the main Gmail web page."""
    return render_template('index.html')

@app.route('/agent')
def agent_interface():
    """Serve the AI Scheduling Agent interface."""
    return render_template('agent.html')

# ========== EMAIL READING ENDPOINTS ==========

@app.route('/api/emails/unread', methods=['GET'])
def get_unread_emails():
    """Get unread emails."""
    client = get_gmail_client()
    if not client:
        return jsonify({'error': 'Gmail client not initialized'}), 500
    
    try:
        max_results = int(request.args.get('max_results', 10))
        messages = client.get_unread_emails(max_results=max_results)
        return jsonify({'success': True, 'count': len(messages), 'messages': messages})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/emails/<message_id>', methods=['GET'])
def get_email_details(message_id):
    """Get email details."""
    client = get_gmail_client()
    if not client:
        return jsonify({'error': 'Gmail client not initialized'}), 500
    
    try:
        details = client.get_email_details(message_id)
        return jsonify({'success': True, 'email': details})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/emails', methods=['GET'])
def list_emails():
    """List emails with query."""
    client = get_gmail_client()
    if not client:
        return jsonify({'error': 'Gmail client not initialized'}), 500
    
    try:
        query = request.args.get('query', '')
        max_results = int(request.args.get('max_results', 10))
        messages = client.list_emails(query=query, max_results=max_results)
        return jsonify({'success': True, 'count': len(messages), 'messages': messages})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/emails/search', methods=['POST'])
def search_emails():
    """Advanced email search."""
    client = get_gmail_client()
    if not client:
        return jsonify({'error': 'Gmail client not initialized'}), 500
    
    try:
        data = request.json
        query = data.get('query', '')
        max_results = int(data.get('max_results', 10))
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        messages = client.search_emails(query, max_results, date_from, date_to)
        return jsonify({'success': True, 'count': len(messages), 'messages': messages})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== EMAIL STATUS ENDPOINTS ==========

@app.route('/api/emails/<message_id>/read', methods=['POST'])
def mark_as_read(message_id):
    """Mark email as read."""
    client = get_gmail_client()
    if not client:
        return jsonify({'error': 'Gmail client not initialized'}), 500
    
    try:
        result = client.mark_as_read(message_id)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/emails/<message_id>/unread', methods=['POST'])
def mark_as_unread(message_id):
    """Mark email as unread."""
    client = get_gmail_client()
    if not client:
        return jsonify({'error': 'Gmail client not initialized'}), 500
    
    try:
        result = client.mark_as_unread(message_id)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/emails/<message_id>/archive', methods=['POST'])
def archive_email(message_id):
    """Archive email."""
    client = get_gmail_client()
    if not client:
        return jsonify({'error': 'Gmail client not initialized'}), 500
    
    try:
        result = client.archive_email(message_id)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/emails/<message_id>/star', methods=['POST'])
def star_email(message_id):
    """Star email."""
    client = get_gmail_client()
    if not client:
        return jsonify({'error': 'Gmail client not initialized'}), 500
    
    try:
        result = client.star_email(message_id)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/emails/<message_id>/unstar', methods=['POST'])
def unstar_email(message_id):
    """Unstar email."""
    client = get_gmail_client()
    if not client:
        return jsonify({'error': 'Gmail client not initialized'}), 500
    
    try:
        result = client.unstar_email(message_id)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== EMAIL SENDING ENDPOINTS ==========

@app.route('/api/emails/<message_id>/reply', methods=['POST'])
def send_reply(message_id):
    """Send reply to email."""
    client = get_gmail_client()
    if not client:
        return jsonify({'error': 'Gmail client not initialized'}), 500
    
    try:
        data = request.json
        reply_text = data.get('reply_text', '')
        if not reply_text:
            return jsonify({'error': 'reply_text is required'}), 400
        
        result = client.send_reply(message_id, reply_text)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/emails/send', methods=['POST'])
def send_email():
    """Send new email."""
    client = get_gmail_client()
    if not client:
        return jsonify({'error': 'Gmail client not initialized'}), 500
    
    try:
        data = request.json
        to = data.get('to')
        subject = data.get('subject')
        body = data.get('body')
        cc = data.get('cc')
        bcc = data.get('bcc')
        
        if not to or not subject or not body:
            return jsonify({'error': 'to, subject, and body are required'}), 400
        
        result = client.send_email(to, subject, body, cc, bcc)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/emails/<message_id>/forward', methods=['POST'])
def forward_email(message_id):
    """Forward email."""
    client = get_gmail_client()
    if not client:
        return jsonify({'error': 'Gmail client not initialized'}), 500
    
    try:
        data = request.json
        to = data.get('to')
        forward_text = data.get('forward_text', '')
        
        if not to:
            return jsonify({'error': 'to is required'}), 400
        
        result = client.forward_email(message_id, to, forward_text)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== DRAFTS ENDPOINTS ==========

@app.route('/api/drafts', methods=['GET'])
def get_drafts():
    """Get drafts."""
    client = get_gmail_client()
    if not client:
        return jsonify({'error': 'Gmail client not initialized'}), 500
    
    try:
        max_results = int(request.args.get('max_results', 10))
        drafts = client.get_drafts(max_results=max_results)
        return jsonify({'success': True, 'count': len(drafts), 'drafts': drafts})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/drafts', methods=['POST'])
def create_draft():
    """Create draft."""
    client = get_gmail_client()
    if not client:
        return jsonify({'error': 'Gmail client not initialized'}), 500
    
    try:
        data = request.json
        to = data.get('to')
        subject = data.get('subject')
        body = data.get('body')
        
        if not to or not subject or not body:
            return jsonify({'error': 'to, subject, and body are required'}), 400
        
        result = client.create_draft(to, subject, body)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/drafts/<draft_id>/send', methods=['POST'])
def send_draft(draft_id):
    """Send draft."""
    client = get_gmail_client()
    if not client:
        return jsonify({'error': 'Gmail client not initialized'}), 500
    
    try:
        result = client.send_draft(draft_id)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== DELETION ENDPOINTS ==========

@app.route('/api/emails/<message_id>', methods=['DELETE'])
def delete_email(message_id):
    """Delete email."""
    client = get_gmail_client()
    if not client:
        return jsonify({'error': 'Gmail client not initialized'}), 500
    
    try:
        result = client.delete_email(message_id)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/emails/delete-from-sender', methods=['POST'])
def delete_emails_from_sender():
    """Delete emails from sender."""
    client = get_gmail_client()
    if not client:
        return jsonify({'error': 'Gmail client not initialized'}), 500
    
    try:
        data = request.json
        sender_email = data.get('sender_email')
        max_results = int(data.get('max_results', 100))
        
        if not sender_email:
            return jsonify({'error': 'sender_email is required'}), 400
        
        result = client.delete_emails_from_sender(sender_email, max_results)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== LABELS ENDPOINTS ==========

@app.route('/api/labels', methods=['GET'])
def list_labels():
    """List labels."""
    client = get_gmail_client()
    if not client:
        return jsonify({'error': 'Gmail client not initialized'}), 500
    
    try:
        labels = client.list_labels()
        return jsonify({'success': True, 'count': len(labels), 'labels': labels})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/labels', methods=['POST'])
def create_label():
    """Create label."""
    client = get_gmail_client()
    if not client:
        return jsonify({'error': 'Gmail client not initialized'}), 500
    
    try:
        data = request.json
        name = data.get('name')
        if not name:
            return jsonify({'error': 'name is required'}), 400
        
        result = client.create_label(name)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/emails/<message_id>/labels/<label_id>', methods=['POST'])
def add_label_to_email(message_id, label_id):
    """Add label to email."""
    client = get_gmail_client()
    if not client:
        return jsonify({'error': 'Gmail client not initialized'}), 500
    
    try:
        result = client.add_label_to_email(message_id, label_id)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== STATISTICS ENDPOINTS ==========

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get email statistics."""
    client = get_gmail_client()
    if not client:
        return jsonify({'error': 'Gmail client not initialized'}), 500
    
    try:
        stats = client.get_stats()
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/emails/<message_id>/attachments', methods=['GET'])
def get_attachments(message_id):
    """Get attachments."""
    client = get_gmail_client()
    if not client:
        return jsonify({'error': 'Gmail client not initialized'}), 500
    
    try:
        attachments = client.get_attachments(message_id)
        return jsonify({'success': True, 'count': len(attachments), 'attachments': attachments})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== CALENDAR ENDPOINTS ==========

@app.route('/api/calendar/events', methods=['GET'])
def get_events():
    """Get calendar events."""
    client = get_calendar_client()
    if not client:
        return jsonify({'error': 'Calendar client not initialized'}), 500
    
    try:
        time_min = request.args.get('time_min')
        time_max = request.args.get('time_max')
        events = client.get_events(time_min=time_min, time_max=time_max)
        return jsonify({'success': True, 'count': len(events), 'events': events})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/calendar/free-slots', methods=['GET'])
def get_free_slots():
    """Get free time slots."""
    client = get_calendar_client()
    if not client:
        return jsonify({'error': 'Calendar client not initialized'}), 500
    
    try:
        duration = int(request.args.get('duration', 30))
        days = int(request.args.get('days', 7))
        slots = client.find_free_slots(duration_minutes=duration, days_ahead=days)
        return jsonify({'success': True, 'count': len(slots), 'slots': slots})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/calendar/events', methods=['POST'])
def create_event():
    """Create calendar event."""
    client = get_calendar_client()
    if not client:
        return jsonify({'error': 'Calendar client not initialized'}), 500
    
    try:
        data = request.json
        result = client.create_event(
            summary=data.get('summary'),
            start_time=data.get('start_time'),
            end_time=data.get('end_time'),
            attendees=data.get('attendees', []),
            description=data.get('description', ''),
            location=data.get('location', '')
        )
        return jsonify({'success': True, 'event': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/calendar/schedule-meeting', methods=['POST'])
def schedule_meeting():
    """Schedule meeting from request."""
    client = get_calendar_client()
    gmail = get_gmail_client()
    
    if not client or not gmail:
        return jsonify({'error': 'Clients not initialized'}), 500
    
    try:
        data = request.json
        requester_email = data.get('requester_email')
        subject = data.get('subject', 'Meeting Request')
        duration = int(data.get('duration', 30))
        preferred_times = data.get('preferred_times', [])
        
        # Schedule meeting
        result = client.schedule_meeting_from_request(
            requester_email, subject, preferred_times, duration
        )
        
        if result.get('error'):
            return jsonify(result), 400
        
        # Send confirmation email
        event = result['event']
        email_body = f"""Hey! I've got your meeting scheduled.

Subject: {event['summary']}
Time: {event['start']}
Calendar Link: {event['htmlLink']}

If that time doesn't work for you, just shoot me a message and I'll find another slot that works better.
"""
        
        gmail.send_email(
            to=requester_email,
            subject=f"Meeting Scheduled: {event['summary']}",
            body=email_body
        )
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== AI AGENT ENDPOINTS ==========

@app.route('/api/agent/run', methods=['POST'])
def run_agent():
    """Run the scheduling agent with a user prompt."""
    try:
        data = request.json
        prompt = data.get('prompt', '')
        
        if not prompt:
            return jsonify({'error': 'Prompt is required'}), 400
        
        # Run the agent in a subprocess
        result = subprocess.run(
            ['python3', 'scheduling_agent.py', prompt],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        return jsonify({
            'success': True,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        })
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Request timed out'}), 408
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/agent/stream')
def stream_agent():
    """Stream agent responses in real-time using Server-Sent Events."""
    prompt = request.args.get('prompt', '')
    
    if not prompt:
        return jsonify({'error': 'Prompt is required'}), 400
    
    def generate():
        """Generator function for streaming responses."""
        try:
            # Run agent and yield output line by line
            process = subprocess.Popen(
                ['python3', 'scheduling_agent.py', prompt],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            for line in iter(process.stdout.readline, ''):
                if line:
                    yield f"data: {json.dumps({'message': line.strip()})}\n\n"
            
            process.wait()
            yield f"data: {json.dumps({'done': True, 'returncode': process.returncode})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    # This API can read, send, and delete mail. Keep the dev server local
    # and disable the interactive debugger by default.
    app.run(debug=False, host='127.0.0.1', port=5001)
