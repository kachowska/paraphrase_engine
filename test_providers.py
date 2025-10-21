#!/usr/bin/env python3
"""
Test script to verify AI provider configuration
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from paraphrase_engine.config import settings
from paraphrase_engine.block3_paraphrasing import ParaphrasingAgent


async def test_providers():
    """Test all configured AI providers"""
    print("=" * 60)
    print("Testing AI Provider Configuration")
    print("=" * 60)
    
    try:
        # Initialize paraphrasing agent
        agent = ParaphrasingAgent()
        
        print(f"\nInitialized {len(agent.providers)} provider(s):")
        for provider in agent.providers:
            print(f"  - {provider.name} (Model: {provider.model})")
        
        print("\nTesting providers...")
        results = await agent.test_providers()
        
        print("\nTest Results:")
        for provider, success in results.items():
            status = "✅ OK" if success else "❌ FAILED"
            print(f"  {provider}: {status}")
        
        # Test paraphrasing
        print("\n" + "=" * 60)
        print("Testing Paraphrasing Pipeline")
        print("=" * 60)
        
        test_text = (
            "The implementation of artificial intelligence in modern healthcare "
            "systems has demonstrated significant potential for improving diagnostic "
            "accuracy and treatment outcomes."
        )
        
        print(f"\nOriginal text:\n{test_text}")
        print("\nProcessing...")
        
        paraphrased = await agent.paraphrase(
            text=test_text,
            style="scientific-legal"
        )
        
        print(f"\nParaphrased text:\n{paraphrased}")
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        return False
    
    return True


async def test_document_builder():
    """Test document builder functionality"""
    from paraphrase_engine.block4_document import DocumentBuilder
    
    print("\n" + "=" * 60)
    print("Testing Document Builder")
    print("=" * 60)
    
    builder = DocumentBuilder()
    
    # Test document validation
    test_file = "test_document.docx"
    if Path(test_file).exists():
        is_valid, error = await builder.validate_document(test_file)
        if is_valid:
            print(f"✅ Document {test_file} is valid")
        else:
            print(f"❌ Document validation failed: {error}")
    else:
        print(f"ℹ️  No test document found at {test_file}")
    
    return True


async def main():
    """Main test function"""
    print("\n🚀 Paraphrase Engine v1.0 - System Test\n")
    
    # Check configuration
    print("Configuration Check:")
    print(f"  Environment: {settings.app_env}")
    print(f"  Log Level: {settings.log_level}")
    
    if not settings.telegram_bot_token:
        print("  ⚠️  Warning: Telegram bot token not configured")
    else:
        print("  ✅ Telegram bot token configured")
    
    # Test providers
    provider_test = await test_providers()
    
    # Test document builder
    doc_test = await test_document_builder()
    
    if provider_test and doc_test:
        print("\n✅ All systems operational!")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check configuration.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
