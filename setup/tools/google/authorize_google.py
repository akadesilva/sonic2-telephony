#!/usr/bin/env python3
"""
One-time OAuth2 authorization for Google APIs.
Run this locally to generate token.json, then copy token.json to your agent.
"""
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import os

SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/spreadsheets'
]

def authorize():
    """Authorize and save credentials"""
    creds = None
    
    # Check if token.json exists
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If no valid credentials, do OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("ERROR: credentials.json not found!")
                print("\nSteps to get credentials.json:")
                print("1. Go to https://console.cloud.google.com/")
                print("2. Create a project (or select existing)")
                print("3. Enable APIs: Calendar, Docs, Sheets")
                print("4. Go to 'Credentials' → 'Create Credentials' → 'OAuth client ID'")
                print("5. Choose 'Desktop app'")
                print("6. Download JSON and save as 'credentials.json'")
                return
            
            print("Starting OAuth flow...")
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
        print("✅ Authorization successful! token.json created.")
        print("\nNext steps:")
        print("1. Copy token.json to your agent directory")
        print("2. Deploy your agent with: agentcore launch")
    else:
        print("✅ Already authorized! token.json is valid.")

if __name__ == '__main__':
    authorize()
