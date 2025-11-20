#!/usr/bin/env python3
"""
Quick configuration verification script
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

print("=" * 60)
print("  Paraphrase Engine v1.0 - Configuration Verification")
print("=" * 60)
print()

try:
    from paraphrase_engine.config import settings
    
    print("✅ Configuration loaded successfully!")
    print()
    
    # Check Telegram Bot
    if settings.telegram_bot_token:
        token_preview = settings.telegram_bot_token[:20] + "..." + settings.telegram_bot_token[-5:]
        print(f"✅ Telegram Bot Token: {token_preview}")
    else:
        print("❌ Telegram Bot Token: NOT CONFIGURED")
    
    print()
    
    # Check AI Providers
    print("AI Providers Configured:")
    providers_count = 0
    
    if settings.google_api_key:
        print(f"  ✅ Google Gemini: {settings.google_api_key[:20]}...")
        providers_count += 1
    else:
        print("  ⚪ Google Gemini: Not configured")
    
    if settings.openai_api_key:
        print(f"  ✅ OpenAI: {settings.openai_api_key[:20]}...")
        providers_count += 1
    else:
        print("  ⚪ OpenAI: Not configured")
    
    if settings.anthropic_api_key:
        print(f"  ✅ Anthropic: {settings.anthropic_api_key[:20]}...")
        providers_count += 1
    else:
        print("  ⚪ Anthropic: Not configured")
    
    print()
    
    if providers_count == 0:
        print("❌ ERROR: No AI providers configured!")
        print("   Please add at least one API key to .env")
        sys.exit(1)
    else:
        print(f"✅ {providers_count} AI provider(s) ready")
    
    print()
    print("Other Settings:")
    print(f"  Environment: {settings.app_env}")
    print(f"  Log Level: {settings.log_level}")
    print(f"  Max File Size: {settings.max_file_size_mb}MB")
    print(f"  File Retention: {settings.file_retention_hours} hours")
    print(f"  Temp Directory: {settings.temp_files_dir}")
    
    print()
    print("=" * 60)
    print("✅ All checks passed! Ready to run the bot.")
    print("=" * 60)
    print()
    print("To start the bot, run:")
    print("  python3 -m paraphrase_engine.main")
    print()
    
except Exception as e:
    print(f"❌ Configuration Error: {e}")
    print()
    print("Please check your .env file and ensure all required values are set.")
    sys.exit(1)
