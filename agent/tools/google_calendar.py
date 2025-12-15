from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime
import json
import os

def _get_calendar_service():
    """Get authenticated Google Calendar service"""
    token_path = os.path.join(os.path.dirname(__file__), '..', 'token.json')
    creds = Credentials.from_authorized_user_file(token_path, 
        scopes=['https://www.googleapis.com/auth/calendar'])
    return build('calendar', 'v3', credentials=creds)

async def create_calendar_event(params):
    """Create a new calendar event"""
    service = _get_calendar_service()
    event = {
        'summary': params['title'],
        'start': {'dateTime': params['start_time'], 'timeZone': params.get('timezone', 'UTC')},
        'end': {'dateTime': params['end_time'], 'timeZone': params.get('timezone', 'UTC')},
        'description': params.get('description', '')
    }
    result = service.events().insert(calendarId='primary', body=event).execute()
    return {'event_id': result['id'], 'link': result['htmlLink']}

async def list_calendar_events(params):
    """List upcoming calendar events"""
    service = _get_calendar_service()
    time_min = params.get('start_date', datetime.utcnow().isoformat() + 'Z')
    max_results = params.get('max_results', 10)
    
    events_result = service.events().list(
        calendarId='primary', timeMin=time_min, maxResults=max_results,
        singleEvents=True, orderBy='startTime'
    ).execute()
    
    events = events_result.get('items', [])
    return {'events': [{'title': e['summary'], 'start': e['start'].get('dateTime', e['start'].get('date')), 
                        'end': e['end'].get('dateTime', e['end'].get('date'))} for e in events]}

def get_tool_definitions():
    """Return tool definitions for Nova Sonic"""
    return [
        {
            "toolSpec": {
                "name": "create_calendar_event",
                "description": "Create a new Google Calendar event",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Event title"},
                            "start_time": {"type": "string", "description": "Start time in ISO format (YYYY-MM-DDTHH:MM:SS)"},
                            "end_time": {"type": "string", "description": "End time in ISO format"},
                            "description": {"type": "string", "description": "Event description"},
                            "timezone": {"type": "string", "description": "Timezone (default: UTC)"}
                        },
                        "required": ["title", "start_time", "end_time"]
                    }
                }
            }
        },
        {
            "toolSpec": {
                "name": "list_calendar_events",
                "description": "List upcoming calendar events",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "start_date": {"type": "string", "description": "Start date in ISO format (default: now)"},
                            "max_results": {"type": "integer", "description": "Max number of events (default: 10)"}
                        }
                    }
                }
            }
        }
    ]
