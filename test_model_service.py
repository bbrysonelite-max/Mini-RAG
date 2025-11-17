"""
Test script for ModelService implementation.

Simple validation that the ModelService can:
1. Generate text using different profiles (cheap/balanced/premium)
2. Generate embeddings
3. Handle errors gracefully

Run with: python test_model_service.py
"""

import asyncio
import os
import sys
from typing import List

from model_service import Message
from model_service_impl import ConcreteModelService
from model_config import get_registry


async def test_generation(service: ConcreteModelService):
    """Test text generation with different profiles."""
    print("\n=== Testing Text Generation ===\n")
    
    test_messages: List[Message] = [
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="What is 2+2? Answer in one sentence.")
    ]
    
    profiles = ['cheap', 'balanced', 'premium']
    
    for profile in profiles:
        print(f"\nTesting {profile} profile...")
        try:
            result = await service.generate({
                'modelProfile': profile,
                'messages': test_messages,
                'maxTokens': 100,
                'temperature': 0.7
            })
            print(f"✓ {profile}: {result['content'][:100]}")
        except Exception as e:
            print(f"✗ {profile} failed: {str(e)}")


async def test_embeddings(service: ConcreteModelService):
    """Test embedding generation."""
    print("\n\n=== Testing Embeddings ===\n")
    
    test_texts = [
        "The quick brown fox jumps over the lazy dog.",
        "Machine learning is a subset of artificial intelligence."
    ]
    
    try:
        result = await service.embed({
            'texts': test_texts
        })
        vectors = result['vectors']
        print(f"✓ Generated {len(vectors)} embeddings")
        print(f"  Vector dimensions: {len(vectors[0]) if vectors else 0}")
        print(f"  First few values: {vectors[0][:5] if vectors and vectors[0] else 'N/A'}")
    except Exception as e:
        print(f"✗ Embedding failed: {str(e)}")


async def test_specific_model(service: ConcreteModelService):
    """Test generation with specific model ID."""
    print("\n\n=== Testing Specific Model Override ===\n")
    
    test_messages: List[Message] = [
        Message(role="user", content="Say 'Hello' in one word.")
    ]
    
    try:
        result = await service.generate({
            'modelId': 'gpt-3.5-turbo',
            'messages': test_messages,
            'maxTokens': 50,
            'temperature': 0.5
        })
        print(f"✓ Specific model (gpt-3.5-turbo): {result['content']}")
    except Exception as e:
        print(f"✗ Specific model failed: {str(e)}")


async def test_error_handling(service: ConcreteModelService):
    """Test error handling with invalid inputs."""
    print("\n\n=== Testing Error Handling ===\n")
    
    # Test invalid profile
    try:
        result = await service.generate({
            'modelProfile': 'invalid',  # type: ignore
            'messages': [Message(role="user", content="Test")]
        })
        print("✗ Should have raised error for invalid profile")
    except Exception as e:
        print(f"✓ Correctly handled invalid profile: {type(e).__name__}")
    
    # Test invalid model ID
    try:
        result = await service.generate({
            'modelId': 'nonexistent-model',
            'messages': [Message(role="user", content="Test")]
        })
        print("✗ Should have raised error for invalid model")
    except Exception as e:
        print(f"✓ Correctly handled invalid model: {type(e).__name__}")


def check_api_keys():
    """Check if required API keys are set."""
    print("\n=== Checking API Keys ===\n")
    
    keys_to_check = {
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
        'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY')
    }
    
    all_set = True
    for key_name, key_value in keys_to_check.items():
        if key_value:
            print(f"✓ {key_name}: Set (length={len(key_value)})")
        else:
            print(f"✗ {key_name}: Not set")
            all_set = False
    
    if not all_set:
        print("\n⚠ Warning: Some API keys are not set. Tests may fail.")
        print("Set them in your .env file or environment variables.")
    
    return all_set


async def main():
    """Run all tests."""
    print("=" * 60)
    print("ModelService Integration Test")
    print("=" * 60)
    
    # Check API keys
    keys_ok = check_api_keys()
    
    if not keys_ok:
        print("\n⚠ Proceeding with tests, but some may fail due to missing keys...")
        await asyncio.sleep(2)
    
    # Initialize service
    print("\n=== Initializing ModelService ===\n")
    registry = get_registry()
    service = ConcreteModelService(registry)
    print("✓ Service initialized")
    
    # Run tests
    await test_generation(service)
    await test_embeddings(service)
    await test_specific_model(service)
    await test_error_handling(service)
    
    print("\n" + "=" * 60)
    print("Tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    # Check if we have asyncio support
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


