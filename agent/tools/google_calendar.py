from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime
import json
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import TIMEZONE_OFFSET

def _ensure_timezone(datetime_str):
    """Add current timezone if not present in datetime string"""
    if not datetime_str:
        return datetime_str
    
    # If it's just a date (YYYY-MM-DD), add time
    if len(datetime_str) == 10 and datetime_str.count('-') == 2:
        datetime_str += 'T00:00:00'
    
    # If already has timezone info, return as is
    if datetime_str.endswith('Z') or '+' in datetime_str[-6:] or '-' in datetime_str[-6:]:
        return datetime_str
    
    # Add global timezone offset
    return datetime_str + TIMEZONE_OFFSET

def _get_calendar_service():
    """Get authenticated Google Calendar service"""
    token_path = os.getenv('GOOGLE_TOKEN_PATH', os.path.join(os.path.dirname(__file__), '..', 'token.json'))
    creds = Credentials.from_authorized_user_file(token_path, 
        scopes=['https://www.googleapis.com/auth/calendar'])
    return build('calendar', 'v3', credentials=creds)

async def create_calendar_event(params):
    """Create a new calendar event"""
    service = _get_calendar_service()
    event = {
        'summary': params['title'],
        'start': {'dateTime': _ensure_timezone(params['start_time']), 'timeZone': params.get('timezone', 'Australia/Melbourne')},
        'end': {'dateTime': _ensure_timezone(params['end_time']), 'timeZone': params.get('timezone', 'Australia/Melbourne')},
        'description': params.get('description', '')
    }
    result = service.events().insert(calendarId='primary', body=event).execute()
    return {'event_id': result['id'], 'link': result['htmlLink']}

async def list_calendar_events(params):
    """List upcoming calendar events"""
    print(params)
    service = _get_calendar_service()
    time_min = params.get('start_date', datetime.now().isoformat())
    time_min = _ensure_timezone(time_min)
    max_results = params.get('max_results', 10)
    
    events_result = service.events().list(
        calendarId='primary', timeMin=time_min, maxResults=max_results,
        singleEvents=True, orderBy='startTime'
    ).execute()

    events = events_result.get('items', [])
    return {'events': [{'title': e['summary'], 'start': e['start'].get('dateTime', e['start'].get('date')), 
                        'end': e['end'].get('dateTime', e['end'].get('date')), 'event_id': e['id']} for e in events]}

async def update_calendar_event(params):
    """Update an existing calendar event"""
    service = _get_calendar_service()
    event_id = params['event_id']
    
    # Get existing event
    event = service.events().get(calendarId='primary', eventId=event_id).execute()
    
    # Update fields if provided
    if 'title' in params:
        event['summary'] = params['title']
    if 'start_time' in params:
        event['start'] = {'dateTime': _ensure_timezone(params['start_time']), 'timeZone': params.get('timezone', 'Australia/Melbourne')}
    if 'end_time' in params:
        event['end'] = {'dateTime': _ensure_timezone(params['end_time']), 'timeZone': params.get('timezone', 'Australia/Melbourne')}
    if 'description' in params:
        event['description'] = params['description']
    
    result = service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
    return {'event_id': result['id'], 'link': result['htmlLink'], 'updated': True}

async def delete_calendar_event(params):
    """Delete a calendar event"""
    service = _get_calendar_service()
    event_id = params['event_id']
    
    service.events().delete(calendarId='primary', eventId=event_id).execute()
    return {'event_id': event_id, 'deleted': True}

def get_tool_definitions():
    """Return tool definitions for Nova Sonic"""
    return [
        {
            "toolSpec": {
                "name": "create_calendar_event",
                "description": "Create a new Google Calendar event",
                "inputSchema": {
                    "json": json.dumps({
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Event title"},
                            "start_time": {"type": "string", "description": "Start time in ISO format (YYYY-MM-DDTHH:MM:SS)"},
                            "end_time": {"type": "string", "description": "End time in ISO format"},
                            "description": {"type": "string", "description": "Event description"},
                            "timezone": {"type": "string", "description": "Timezone (default: UTC)"}
                        },
                        "required": ["title", "start_time", "end_time"]
                    })
                }
            }
        },
        {
            "toolSpec": {
                "name": "list_calendar_events",
                "description": "List upcoming calendar events",
                "inputSchema": {
                    "json": json.dumps({
                        "type": "object",
                        "properties": {
                            "start_date": {"type": "string", "description": "Start date in ISO format (default: now)"},
                            "max_results": {"type": "integer", "description": "Max number of events (default: 10)"}
                        }
                    })
                }
            }
        },
        {
            "toolSpec": {
                "name": "update_calendar_event",
                "description": "Update an existing calendar event",
                "inputSchema": {
                    "json": json.dumps({
                        "type": "object",
                        "properties": {
                            "event_id": {"type": "string", "description": "Event ID to update"},
                            "title": {"type": "string", "description": "New event title (optional)"},
                            "start_time": {"type": "string", "description": "New start time in ISO format (optional)"},
                            "end_time": {"type": "string", "description": "New end time in ISO format (optional)"},
                            "description": {"type": "string", "description": "New event description (optional)"}
                        },
                        "required": ["event_id"]
                    })
                }
            }
        },
        {
            "toolSpec": {
                "name": "delete_calendar_event",
                "description": "Delete a calendar event",
                "inputSchema": {
                    "json": json.dumps({
                        "type": "object",
                        "properties": {
                            "event_id": {"type": "string", "description": "Event ID to delete"}
                        },
                        "required": ["event_id"]
                    })
                }
            }
        }
    ]
