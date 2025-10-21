#!/usr/bin/env python3
"""
Create Google Sheets for Paraphrase Engine Bot Logging
Creates a new spreadsheet with proper structure for bot logging
"""

import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Scopes for creating and managing spreadsheets
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def get_credentials():
    """Get valid user credentials from storage or prompt user to log in."""
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def create_spreadsheet(title):
    """
    Creates a new Google Sheet with proper structure for bot logging.
    """
    try:
        # Get credentials
        creds = get_credentials()
        
        # Build the service
        service = build("sheets", "v4", credentials=creds)
        
        # Create the spreadsheet
        spreadsheet = {
            "properties": {
                "title": title,
                "locale": "en_US",
                "timeZone": "UTC"
            },
            "sheets": [
                {
                    "properties": {
                        "title": "Tasks",
                        "gridProperties": {
                            "rowCount": 1000,
                            "columnCount": 8
                        }
                    }
                },
                {
                    "properties": {
                        "title": "Operations", 
                        "gridProperties": {
                            "rowCount": 1000,
                            "columnCount": 7
                        }
                    }
                },
                {
                    "properties": {
                        "title": "Results",
                        "gridProperties": {
                            "rowCount": 1000,
                            "columnCount": 7
                        }
                    }
                },
                {
                    "properties": {
                        "title": "Errors",
                        "gridProperties": {
                            "rowCount": 1000,
                            "columnCount": 6
                        }
                    }
                }
            ]
        }
        
        # Create the spreadsheet
        result = service.spreadsheets().create(body=spreadsheet).execute()
        spreadsheet_id = result.get('spreadsheetId')
        
        print(f"✅ Created spreadsheet: {title}")
        print(f"📊 Spreadsheet ID: {spreadsheet_id}")
        print(f"🔗 URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
        
        # Add headers to each sheet
        setup_sheet_headers(service, spreadsheet_id)
        
        return spreadsheet_id
        
    except HttpError as error:
        print(f"❌ An error occurred: {error}")
        return None
    except Exception as error:
        print(f"❌ Unexpected error: {error}")
        return None

def setup_sheet_headers(service, spreadsheet_id):
    """Set up headers for each worksheet"""
    
    # Define headers for each sheet
    headers = {
        "Tasks": [
            "Timestamp", "Task ID", "Chat ID", "User", "Status",
            "Fragments Count", "Processing Time", "Error"
        ],
        "Operations": [
            "Timestamp", "Task ID", "Operation", "Provider", "Duration",
            "Success", "Error Message"
        ],
        "Results": [
            "Timestamp", "Task ID", "Fragment Index", "Original Text",
            "Paraphrased Text", "Provider Used", "Score"
        ],
        "Errors": [
            "Timestamp", "Chat ID", "Operation", "Error Type",
            "Error Message", "Stack Trace"
        ]
    }
    
    try:
        # Add headers to each sheet
        for sheet_name, header_row in headers.items():
            range_name = f"{sheet_name}!A1"
            body = {
                "values": [header_row]
            }
            
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                body=body
            ).execute()
            
            print(f"✅ Added headers to {sheet_name} sheet")
            
    except Exception as error:
        print(f"⚠️  Warning: Could not add headers: {error}")

def main():
    """Main function to create the bot logging spreadsheet"""
    
    print("=" * 60)
    print("Creating Google Sheets for Paraphrase Engine Bot Logging")
    print("=" * 60)
    
    # Create the spreadsheet
    spreadsheet_id = create_spreadsheet("Paraphrase Engine Bot Logs")
    
    if spreadsheet_id:
        print("\n" + "=" * 60)
        print("✅ SUCCESS!")
        print("=" * 60)
        print(f"📊 Spreadsheet ID: {spreadsheet_id}")
        print(f"🔗 URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
        print("\n📋 Next steps:")
        print("1. Copy the Spreadsheet ID above")
        print("2. Update your .env file:")
        print(f"   GOOGLE_SHEETS_CREDENTIALS_PATH=./credentials.json")
        print(f"   GOOGLE_SHEETS_SPREADSHEET_ID={spreadsheet_id}")
        print("3. Restart your bot: ./run_bot.sh restart")
        print("=" * 60)
    else:
        print("\n❌ Failed to create spreadsheet")
        print("Please check your credentials and try again.")

if __name__ == "__main__":
    main()
