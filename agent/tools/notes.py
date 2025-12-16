from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime
import json
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import TIMEZONE_OFFSET

# Cache for folder ID
_notes_folder_id = None

def _get_services():
    """Get authenticated Google services"""
    token_path = os.getenv('GOOGLE_TOKEN_PATH', os.path.join(os.path.dirname(__file__), '..', 'token.json'))
    creds = Credentials.from_authorized_user_file(token_path,
        scopes=['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive.file'])
    docs_service = build('docs', 'v1', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    return docs_service, drive_service

def _get_notes_folder_id(drive_service):
    """Find or create my_notes folder"""
    global _notes_folder_id
    
    if _notes_folder_id:
        return _notes_folder_id
    
    # Search for existing my_notes folder
    query = "name='my_notes' and mimeType='application/vnd.google-apps.folder'"
    results = drive_service.files().list(q=query, pageSize=1, fields="files(id)").execute()
    files = results.get('files', [])
    
    if files:
        _notes_folder_id = files[0]['id']
    else:
        # Create my_notes folder
        folder_metadata = {
            'name': 'my_notes',
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
        _notes_folder_id = folder['id']
    
    return _notes_folder_id

def _find_note_entry(drive_service, date_str):
    """Find note entry for a specific date"""
    folder_id = _get_notes_folder_id(drive_service)
    query = f"name='{date_str}' and mimeType='application/vnd.google-apps.document' and '{folder_id}' in parents"
    
    results = drive_service.files().list(q=query, pageSize=1, fields="files(id, name)").execute()
    files = results.get('files', [])
    return files[0]['id'] if files else None

def _create_note_entry(docs_service, drive_service, date_str):
    """Create a new note entry for a date"""
    folder_id = _get_notes_folder_id(drive_service)
    
    # Create document in my_notes folder
    doc = docs_service.documents().create(body={'title': date_str}).execute()
    doc_id = doc['documentId']
    
    # Move to notes folder
    drive_service.files().update(
        fileId=doc_id,
        addParents=folder_id,
        fields='id, parents'
    ).execute()
    
    return doc_id

async def read_notes(params):
    """Read notes entry for a specific date"""
    docs_service, drive_service = _get_services()
    
    # Default to today if no date provided
    date_str = params.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    # Find or create entry
    doc_id = _find_note_entry(drive_service, date_str)
    
    if not doc_id:
        return {'date': date_str, 'content': '', 'message': 'No notes found for this date'}
    
    # Read content
    doc = docs_service.documents().get(documentId=doc_id).execute()
    content = '\n'.join([elem.get('paragraph', {}).get('elements', [{}])[0].get('textRun', {}).get('content', '') 
                         for elem in doc.get('body', {}).get('content', [])])
    
    return {'date': date_str, 'content': content.strip()}

async def update_notes(params):
    """Update notes entry for a specific date"""
    docs_service, drive_service = _get_services()
    
    # Default to today if no date provided
    date_str = params.get('date', datetime.now().strftime('%Y-%m-%d'))
    content = params['content']
    current_time = datetime.now().strftime('%H:%M:%S')
    
    # Find or create entry
    doc_id = _find_note_entry(drive_service, date_str)
    
    if not doc_id:
        doc_id = _create_note_entry(docs_service, drive_service, date_str)
        # For new document, add content at the beginning
        formatted_content = f"{current_time}: {content}"
        insert_index = 1
    else:
        # For existing document, get the end index and append
        doc = docs_service.documents().get(documentId=doc_id).execute()
        end_index = doc.get('body', {}).get('content', [{}])[-1].get('endIndex', 1) - 1
        formatted_content = f"\n\n{current_time}: {content}"
        insert_index = end_index
    
    # Append content
    docs_service.documents().batchUpdate(
        documentId=doc_id,
        body={'requests': [{'insertText': {'location': {'index': insert_index}, 'text': formatted_content}}]}
    ).execute()
    
    return {'date': date_str, 'doc_id': doc_id, 'updated': True}

def get_tool_definitions():
    """Return tool definitions for Nova Sonic"""
    return [
        {
            "toolSpec": {
                "name": "read_notes",
                "description": "Read notes for a specific date. Defaults to today if no date provided.",
                "inputSchema": {
                    "json": json.dumps({
                        "type": "object",
                        "properties": {
                            "date": {"type": "string", "description": "Date in YYYY-MM-DD format (optional, defaults to today)"}
                        }
                    })
                }
            }
        },
        {
            "toolSpec": {
                "name": "update_notes",
                "description": "Add notes for a specific date. Creates entry if it doesn't exist. Defaults to today if no date provided.",
                "inputSchema": {
                    "json": json.dumps({
                        "type": "object",
                        "properties": {
                            "date": {"type": "string", "description": "Date in YYYY-MM-DD format (optional, defaults to today)"},
                            "content": {"type": "string", "description": "Content to add to the notes"}
                        },
                        "required": ["content"]
                    })
                }
            }
        }
    ]
