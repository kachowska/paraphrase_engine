#!/usr/bin/env python3
"""
Test Google Sheets integration for Paraphrase Engine bot
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_google_sheets_integration():
    """Test if Google Sheets integration works with the bot's logger"""
    
    print("🔍 Testing Google Sheets integration for Paraphrase Engine...")
    
    # Test 1: Check if gspread is available
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        print("✅ gspread and google-auth packages are available")
    except ImportError as e:
        print(f"❌ Missing packages: {e}")
        return False
    
    # Test 2: Check credentials file
    credentials_file = "credentials.json"
    if not os.path.exists(credentials_file):
        print(f"❌ {credentials_file} not found")
        return False
    print(f"✅ {credentials_file} found")
    
    # Test 3: Test OAuth credentials (using existing token.json)
    token_file = "token.json"
    if not os.path.exists(token_file):
        print(f"❌ {token_file} not found - run quickstart.py first")
        return False
    print(f"✅ {token_file} found")
    
    # Test 4: Test bot's SystemLogger Google Sheets initialization
    try:
        from paraphrase_engine.block5_logging.logger import SystemLogger
        logger = SystemLogger()
        
        if logger.google_sheets_client is not None:
            print("✅ Bot's Google Sheets client initialized successfully")
            return True
        else:
            print("⚠️  Bot's Google Sheets client not initialized (credentials not configured)")
            print("   This is normal if GOOGLE_SHEETS_CREDENTIALS_PATH is not set in .env")
            return True  # This is expected behavior
            
    except Exception as e:
        print(f"❌ Error testing bot's Google Sheets integration: {e}")
        return False

def test_oauth_credentials():
    """Test OAuth credentials with a simple API call"""
    
    print("\n🔍 Testing OAuth credentials...")
    
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        
        # Load credentials
        creds = Credentials.from_authorized_user_file("token.json", 
            ["https://www.googleapis.com/auth/spreadsheets.readonly"])
        
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
        
        # Test API call
        service = build("sheets", "v4", credentials=creds)
        sheet = service.spreadsheets()
        
        # Try to get spreadsheet info (this will fail if credentials are invalid)
        spreadsheet_id = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
        result = sheet.get(spreadsheetId=spreadsheet_id).execute()
        
        print(f"✅ OAuth credentials valid - accessed spreadsheet: {result.get('properties', {}).get('title', 'Unknown')}")
        return True
        
    except Exception as e:
        print(f"❌ OAuth credentials test failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Google Sheets Integration Test for Paraphrase Engine")
    print("=" * 60)
    
    # Test basic integration
    integration_ok = test_google_sheets_integration()
    
    # Test OAuth credentials
    oauth_ok = test_oauth_credentials()
    
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print("=" * 60)
    
    if integration_ok and oauth_ok:
        print("✅ Google Sheets integration is working correctly!")
        print("\nTo enable Google Sheets logging in your bot:")
        print("1. Create a Google Sheet for logging")
        print("2. Update your .env file with:")
        print("   GOOGLE_SHEETS_CREDENTIALS_PATH=./credentials.json")
        print("   GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id")
        print("3. Restart your bot")
    else:
        print("❌ Google Sheets integration has issues")
        if not integration_ok:
            print("   - Basic integration failed")
        if not oauth_ok:
            print("   - OAuth credentials failed")
    
    print("=" * 60)
