#!/usr/bin/env python3
"""
Test imports to identify the error
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

print("Testing imports...")

try:
    print("1. Testing config import...")
    from paraphrase_engine.config import settings
    print("✅ Config loaded successfully")
except Exception as e:
    print(f"❌ Config error: {e}")
    sys.exit(1)

try:
    print("2. Testing SystemLogger import...")
    from paraphrase_engine.block5_logging.logger import SystemLogger
    print("✅ SystemLogger imported successfully")
except Exception as e:
    print(f"❌ SystemLogger error: {e}")
    sys.exit(1)

try:
    print("3. Testing SystemLogger initialization...")
    logger = SystemLogger()
    print("✅ SystemLogger initialized successfully")
except Exception as e:
    print(f"❌ SystemLogger init error: {e}")
    sys.exit(1)

try:
    print("4. Testing AI providers import...")
    from paraphrase_engine.block3_paraphrasing.ai_providers import GoogleGeminiProvider
    print("✅ AI providers imported successfully")
except Exception as e:
    print(f"❌ AI providers error: {e}")
    sys.exit(1)

try:
    print("5. Testing GoogleGeminiProvider initialization...")
    provider = GoogleGeminiProvider(api_key=settings.google_api_key)
    print("✅ GoogleGeminiProvider initialized successfully")
except Exception as e:
    print(f"❌ GoogleGeminiProvider init error: {e}")
    sys.exit(1)

try:
    print("6. Testing ParaphrasingAgent import...")
    from paraphrase_engine.block3_paraphrasing.agent_core import ParaphrasingAgent
    print("✅ ParaphrasingAgent imported successfully")
except Exception as e:
    print(f"❌ ParaphrasingAgent error: {e}")
    sys.exit(1)

try:
    print("7. Testing ParaphrasingAgent initialization...")
    agent = ParaphrasingAgent()
    print("✅ ParaphrasingAgent initialized successfully")
except Exception as e:
    print(f"❌ ParaphrasingAgent init error: {e}")
    sys.exit(1)

try:
    print("8. Testing TaskManager import...")
    from paraphrase_engine.block2_orchestrator.task_manager import TaskManager
    print("✅ TaskManager imported successfully")
except Exception as e:
    print(f"❌ TaskManager error: {e}")
    sys.exit(1)

try:
    print("9. Testing TaskManager initialization...")
    task_manager = TaskManager()
    print("✅ TaskManager initialized successfully")
except Exception as e:
    print(f"❌ TaskManager init error: {e}")
    sys.exit(1)

print("\n🎉 All imports and initializations successful!")
