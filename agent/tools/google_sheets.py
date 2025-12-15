from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import os

def _get_sheets_service():
    """Get authenticated Google Sheets service"""
    token_path = os.path.join(os.path.dirname(__file__), '..', 'token.json')
    creds = Credentials.from_authorized_user_file(token_path,
        scopes=['https://www.googleapis.com/auth/spreadsheets'])
    return build('sheets', 'v4', credentials=creds)

async def create_google_sheet(params):
    """Create a new Google Sheet"""
    service = _get_sheets_service()
    spreadsheet = {'properties': {'title': params['title']}}
    result = service.spreadsheets().create(body=spreadsheet).execute()
    
    return {'sheet_id': result['spreadsheetId'], 'url': result['spreadsheetUrl']}

async def read_google_sheet(params):
    """Read data from a Google Sheet"""
    service = _get_sheets_service()
    range_name = params.get('range', 'Sheet1')
    
    result = service.spreadsheets().values().get(
        spreadsheetId=params['sheet_id'], range=range_name
    ).execute()
    
    return {'values': result.get('values', [])}

async def write_to_google_sheet(params):
    """Write data to a Google Sheet"""
    service = _get_sheets_service()
    range_name = params.get('range', 'Sheet1!A1')
    values = params['values']  # Should be list of lists: [["A1", "B1"], ["A2", "B2"]]
    
    body = {'values': values}
    result = service.spreadsheets().values().update(
        spreadsheetId=params['sheet_id'], range=range_name,
        valueInputOption='RAW', body=body
    ).execute()
    
    return {'updated_cells': result.get('updatedCells', 0)}

async def append_to_google_sheet(params):
    """Append rows to a Google Sheet"""
    service = _get_sheets_service()
    range_name = params.get('range', 'Sheet1')
    values = params['values']
    
    body = {'values': values}
    result = service.spreadsheets().values().append(
        spreadsheetId=params['sheet_id'], range=range_name,
        valueInputOption='RAW', body=body
    ).execute()
    
    return {'updated_cells': result.get('updates', {}).get('updatedCells', 0)}

def get_tool_definitions():
    """Return tool definitions for Nova Sonic"""
    return [
        {
            "toolSpec": {
                "name": "create_google_sheet",
                "description": "Create a new Google Sheet",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Sheet title"}
                        },
                        "required": ["title"]
                    }
                }
            }
        },
        {
            "toolSpec": {
                "name": "read_google_sheet",
                "description": "Read data from a Google Sheet",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "sheet_id": {"type": "string", "description": "Spreadsheet ID from URL"},
                            "range": {"type": "string", "description": "Range to read (e.g., 'Sheet1' or 'Sheet1!A1:B10')"}
                        },
                        "required": ["sheet_id"]
                    }
                }
            }
        },
        {
            "toolSpec": {
                "name": "write_to_google_sheet",
                "description": "Write data to a Google Sheet",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "sheet_id": {"type": "string", "description": "Spreadsheet ID"},
                            "values": {"type": "array", "description": "2D array of values [[row1], [row2]]"},
                            "range": {"type": "string", "description": "Starting cell (e.g., 'Sheet1!A1')"}
                        },
                        "required": ["sheet_id", "values"]
                    }
                }
            }
        },
        {
            "toolSpec": {
                "name": "append_to_google_sheet",
                "description": "Append rows to a Google Sheet",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "sheet_id": {"type": "string", "description": "Spreadsheet ID"},
                            "values": {"type": "array", "description": "2D array of rows to append"},
                            "range": {"type": "string", "description": "Sheet name (default: Sheet1)"}
                        },
                        "required": ["sheet_id", "values"]
                    }
                }
            }
        }
    ]
