from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import os

def _get_docs_service():
    """Get authenticated Google Docs service"""
    token_path = os.path.join(os.path.dirname(__file__), '..', 'token.json')
    creds = Credentials.from_authorized_user_file(token_path,
        scopes=['https://www.googleapis.com/auth/documents'])
    return build('docs', 'v1', credentials=creds)

async def create_google_doc(params):
    """Create a new Google Doc"""
    service = _get_docs_service()
    doc = service.documents().create(body={'title': params['title']}).execute()
    
    if params.get('content'):
        requests = [{'insertText': {'location': {'index': 1}, 'text': params['content']}}]
        service.documents().batchUpdate(documentId=doc['documentId'], body={'requests': requests}).execute()
    
    return {'doc_id': doc['documentId'], 'url': f"https://docs.google.com/document/d/{doc['documentId']}/edit"}

async def read_google_doc(params):
    """Read content from a Google Doc"""
    service = _get_docs_service()
    doc = service.documents().get(documentId=params['doc_id']).execute()
    
    content = ''
    for element in doc.get('body', {}).get('content', []):
        if 'paragraph' in element:
            for text_run in element['paragraph'].get('elements', []):
                if 'textRun' in text_run:
                    content += text_run['textRun'].get('content', '')
    
    return {'title': doc['title'], 'content': content}

async def append_to_google_doc(params):
    """Append text to an existing Google Doc"""
    service = _get_docs_service()
    doc = service.documents().get(documentId=params['doc_id']).execute()
    end_index = doc['body']['content'][-1]['endIndex'] - 1
    
    requests = [{'insertText': {'location': {'index': end_index}, 'text': '\n' + params['text']}}]
    service.documents().batchUpdate(documentId=params['doc_id'], body={'requests': requests}).execute()
    
    return {'success': True, 'doc_id': params['doc_id']}

def get_tool_definitions():
    """Return tool definitions for Nova Sonic"""
    return [
        {
            "toolSpec": {
                "name": "create_google_doc",
                "description": "Create a new Google Doc",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Document title"},
                            "content": {"type": "string", "description": "Initial content (optional)"}
                        },
                        "required": ["title"]
                    }
                }
            }
        },
        {
            "toolSpec": {
                "name": "read_google_doc",
                "description": "Read content from a Google Doc",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "doc_id": {"type": "string", "description": "Document ID from URL"}
                        },
                        "required": ["doc_id"]
                    }
                }
            }
        },
        {
            "toolSpec": {
                "name": "append_to_google_doc",
                "description": "Append text to an existing Google Doc",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "doc_id": {"type": "string", "description": "Document ID"},
                            "text": {"type": "string", "description": "Text to append"}
                        },
                        "required": ["doc_id", "text"]
                    }
                }
            }
        }
    ]
