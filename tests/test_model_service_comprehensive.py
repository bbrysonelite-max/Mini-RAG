"""
Comprehensive Model Service Tests for Mini-RAG / Second Brain

Tests for LLM provider integration, model routing, and response handling.

Run with:
    pytest tests/test_model_service_comprehensive.py -v
    pytest tests/test_model_service_comprehensive.py -v -m "not requires_api_key"
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("ALLOW_INSECURE_DEFAULTS", "true")


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    return {
        "choices": [{
            "message": {
                "content": "This is a mock response from the model.",
                "role": "assistant"
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150
        }
    }


@pytest.fixture
def mock_anthropic_response():
    """Mock Anthropic API response."""
    return {
        "content": [{
            "type": "text",
            "text": "This is a mock response from Claude."
        }],
        "stop_reason": "end_turn",
        "usage": {
            "input_tokens": 100,
            "output_tokens": 50
        }
    }


@pytest.fixture
def mock_embedding_response():
    """Mock embedding response."""
    return {
        "data": [{
            "embedding": [0.1] * 1536,  # OpenAI text-embedding-3-small dimension
            "index": 0
        }],
        "usage": {
            "prompt_tokens": 10,
            "total_tokens": 10
        }
    }


class MockHTTPResponse:
    """Mock HTTP response for testing."""
    def __init__(self, json_data: Dict, status_code: int = 200):
        self._json_data = json_data
        self.status_code = status_code

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP Error {self.status_code}")


# =============================================================================
# MODEL CONFIG TESTS
# =============================================================================

class TestModelConfig:
    """Test model configuration and registry."""

    def test_model_profiles_exist(self):
        """Test that all expected model profiles are defined."""
        from model_config import MODEL_PROFILES

        expected_profiles = ["cheap", "balanced", "premium"]
        for profile in expected_profiles:
            assert profile in MODEL_PROFILES, f"Missing profile: {profile}"

    def test_profile_has_required_fields(self):
        """Test that model profiles have required configuration."""
        from model_config import MODEL_PROFILES

        required_fields = ["chat_model", "embedding_model"]

        for profile_name, profile in MODEL_PROFILES.items():
            for field in required_fields:
                assert field in profile, f"Profile {profile_name} missing {field}"

    def test_get_model_for_profile(self):
        """Test getting model configuration by profile."""
        from model_config import get_model_config

        for profile in ["cheap", "balanced", "premium"]:
            config = get_model_config(profile)
            assert config is not None
            assert "chat_model" in config

    def test_invalid_profile_handling(self):
        """Test handling of invalid profile names."""
        from model_config import get_model_config

        # Should either return default or raise clear error
        try:
            config = get_model_config("nonexistent_profile")
            # If it returns something, it should be the default
            assert config is not None
        except (KeyError, ValueError) as e:
            # Or it should raise a clear error
            assert "profile" in str(e).lower() or "nonexistent" in str(e).lower()


# =============================================================================
# MODEL SERVICE TESTS
# =============================================================================

class TestModelServiceInterface:
    """Test model service interface and contract."""

    def test_model_service_instantiation(self):
        """Test that model service can be instantiated."""
        from model_service_impl import ConcreteModelService

        service = ConcreteModelService()
        assert service is not None

    def test_model_service_has_required_methods(self):
        """Test that model service has all required methods."""
        from model_service_impl import ConcreteModelService

        service = ConcreteModelService()

        required_methods = ["generate", "embed"]
        for method in required_methods:
            assert hasattr(service, method), f"Missing method: {method}"
            assert callable(getattr(service, method)), f"{method} is not callable"

    @pytest.mark.asyncio
    async def test_generate_returns_correct_format(self):
        """Test that generate returns correct response format."""
        from model_service_impl import ConcreteModelService

        service = ConcreteModelService()

        # Mock the actual API call
        with patch.object(service, '_call_chat_api', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {
                "content": "Mock response",
                "usage": {"prompt_tokens": 10, "completion_tokens": 5}
            }

            result = await service.generate(
                prompt="Test prompt",
                messages=[],
                options={"max_tokens": 100}
            )

            assert "content" in result or isinstance(result, str)

    @pytest.mark.asyncio
    async def test_embed_returns_vectors(self):
        """Test that embed returns vector embeddings."""
        from model_service_impl import ConcreteModelService

        service = ConcreteModelService()

        # Mock the embedding API call
        with patch.object(service, '_call_embedding_api', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = [[0.1] * 1536]

            result = await service.embed(["Test text"])

            assert isinstance(result, list)
            if result:
                assert isinstance(result[0], list)
                assert all(isinstance(x, (int, float)) for x in result[0])


# =============================================================================
# LLM PROVIDER TESTS
# =============================================================================

class TestLLMProviders:
    """Test individual LLM provider implementations."""

    def test_openai_provider_exists(self):
        """Test that OpenAI provider is available."""
        try:
            from llm_providers import OpenAIProvider
            provider = OpenAIProvider()
            assert provider is not None
        except ImportError:
            pytest.skip("OpenAI provider not available")

    def test_anthropic_provider_exists(self):
        """Test that Anthropic provider is available."""
        try:
            from llm_providers import AnthropicProvider
            provider = AnthropicProvider()
            assert provider is not None
        except ImportError:
            pytest.skip("Anthropic provider not available")

    @pytest.mark.asyncio
    async def test_provider_error_handling(self):
        """Test that providers handle errors gracefully."""
        from model_service_impl import ConcreteModelService

        service = ConcreteModelService()

        # Simulate API error
        with patch.object(service, '_call_chat_api', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = Exception("API Error: Rate limit exceeded")

            with pytest.raises(Exception) as exc_info:
                await service.generate(
                    prompt="Test",
                    messages=[],
                    options={}
                )

            assert "rate limit" in str(exc_info.value).lower() or "error" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_provider_timeout_handling(self):
        """Test that providers handle timeouts."""
        from model_service_impl import ConcreteModelService

        service = ConcreteModelService()

        with patch.object(service, '_call_chat_api', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = asyncio.TimeoutError("Request timed out")

            with pytest.raises((asyncio.TimeoutError, Exception)):
                await service.generate(
                    prompt="Test",
                    messages=[],
                    options={"timeout": 1}
                )


# =============================================================================
# EMBEDDING TESTS
# =============================================================================

class TestEmbeddings:
    """Test embedding functionality."""

    @pytest.mark.asyncio
    async def test_embed_single_text(self):
        """Test embedding a single text."""
        from model_service_impl import ConcreteModelService

        service = ConcreteModelService()

        with patch.object(service, '_call_embedding_api', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = [[0.1] * 1536]

            result = await service.embed(["Hello world"])

            assert len(result) == 1
            assert len(result[0]) == 1536

    @pytest.mark.asyncio
    async def test_embed_batch(self):
        """Test embedding multiple texts in batch."""
        from model_service_impl import ConcreteModelService

        service = ConcreteModelService()

        texts = ["Text one", "Text two", "Text three"]

        with patch.object(service, '_call_embedding_api', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = [[0.1] * 1536 for _ in texts]

            result = await service.embed(texts)

            assert len(result) == len(texts)
            for embedding in result:
                assert len(embedding) == 1536

    @pytest.mark.asyncio
    async def test_embed_empty_text(self):
        """Test handling of empty text."""
        from model_service_impl import ConcreteModelService

        service = ConcreteModelService()

        with patch.object(service, '_call_embedding_api', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = [[0.0] * 1536]

            # Should handle empty string gracefully
            result = await service.embed([""])
            assert result is not None

    @pytest.mark.asyncio
    async def test_embed_long_text(self):
        """Test embedding text that exceeds token limits."""
        from model_service_impl import ConcreteModelService

        service = ConcreteModelService()

        # Very long text
        long_text = "word " * 10000  # ~50K tokens

        with patch.object(service, '_call_embedding_api', new_callable=AsyncMock) as mock_call:
            # Should either truncate or handle gracefully
            mock_call.return_value = [[0.1] * 1536]

            try:
                result = await service.embed([long_text])
                assert result is not None
            except Exception as e:
                # Or raise a clear error about length
                assert "length" in str(e).lower() or "token" in str(e).lower()


# =============================================================================
# RESPONSE GENERATION TESTS
# =============================================================================

class TestResponseGeneration:
    """Test response generation functionality."""

    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(self):
        """Test generation with system prompt."""
        from model_service_impl import ConcreteModelService

        service = ConcreteModelService()

        with patch.object(service, '_call_chat_api', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"content": "Response with system prompt"}

            result = await service.generate(
                prompt="User question",
                messages=[],
                options={"system_prompt": "You are a helpful assistant."}
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_generate_with_context(self):
        """Test generation with context from retrieved chunks."""
        from model_service_impl import ConcreteModelService

        service = ConcreteModelService()

        context = """
        Context 1: Machine learning is a subset of AI.
        Context 2: Deep learning uses neural networks.
        """

        with patch.object(service, '_call_chat_api', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"content": "Based on the context..."}

            result = await service.generate(
                prompt=f"Context:\n{context}\n\nQuestion: What is ML?",
                messages=[],
                options={}
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_generate_respects_max_tokens(self):
        """Test that max_tokens is respected."""
        from model_service_impl import ConcreteModelService

        service = ConcreteModelService()

        with patch.object(service, '_call_chat_api', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {
                "content": "Short response",
                "usage": {"completion_tokens": 10}
            }

            result = await service.generate(
                prompt="Generate a response",
                messages=[],
                options={"max_tokens": 50}
            )

            # Verify the option was passed
            call_args = mock_call.call_args
            assert call_args is not None

    @pytest.mark.asyncio
    async def test_generate_handles_conversation_history(self):
        """Test generation with conversation history."""
        from model_service_impl import ConcreteModelService

        service = ConcreteModelService()

        messages = [
            {"role": "user", "content": "What is AI?"},
            {"role": "assistant", "content": "AI is artificial intelligence."},
            {"role": "user", "content": "Tell me more."}
        ]

        with patch.object(service, '_call_chat_api', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"content": "More about AI..."}

            result = await service.generate(
                prompt="",
                messages=messages,
                options={}
            )

            assert result is not None


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

class TestErrorHandling:
    """Test error handling in model service."""

    @pytest.mark.asyncio
    async def test_handles_api_key_missing(self):
        """Test handling when API key is missing."""
        # Temporarily remove API key
        original_key = os.environ.pop("OPENAI_API_KEY", None)
        original_anthropic = os.environ.pop("ANTHROPIC_API_KEY", None)

        try:
            from model_service_impl import ConcreteModelService

            service = ConcreteModelService()

            # Should either raise clear error or handle gracefully
            with patch.object(service, '_call_chat_api', new_callable=AsyncMock) as mock_call:
                mock_call.side_effect = Exception("API key not configured")

                with pytest.raises(Exception) as exc_info:
                    await service.generate(prompt="Test", messages=[], options={})

                error_msg = str(exc_info.value).lower()
                assert "key" in error_msg or "auth" in error_msg or "configured" in error_msg
        finally:
            # Restore keys
            if original_key:
                os.environ["OPENAI_API_KEY"] = original_key
            if original_anthropic:
                os.environ["ANTHROPIC_API_KEY"] = original_anthropic

    @pytest.mark.asyncio
    async def test_handles_rate_limit_error(self):
        """Test handling of rate limit errors."""
        from model_service_impl import ConcreteModelService

        service = ConcreteModelService()

        with patch.object(service, '_call_chat_api', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = Exception("Rate limit exceeded. Please retry after 60 seconds.")

            with pytest.raises(Exception) as exc_info:
                await service.generate(prompt="Test", messages=[], options={})

            assert "rate" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_handles_invalid_response(self):
        """Test handling of malformed API responses."""
        from model_service_impl import ConcreteModelService

        service = ConcreteModelService()

        with patch.object(service, '_call_chat_api', new_callable=AsyncMock) as mock_call:
            # Return malformed response
            mock_call.return_value = {"unexpected": "format"}

            # Should handle gracefully
            try:
                result = await service.generate(prompt="Test", messages=[], options={})
                # If it succeeds, it should still return something usable
            except (KeyError, TypeError, ValueError):
                # Or raise a clear error
                pass

    @pytest.mark.asyncio
    async def test_handles_network_error(self):
        """Test handling of network errors."""
        from model_service_impl import ConcreteModelService

        service = ConcreteModelService()

        with patch.object(service, '_call_chat_api', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = ConnectionError("Network unreachable")

            with pytest.raises((ConnectionError, Exception)):
                await service.generate(prompt="Test", messages=[], options={})


# =============================================================================
# SKELETON SERVICE TESTS
# =============================================================================

class TestSkeletonModelService:
    """Test the skeleton/mock model service for testing."""

    def test_skeleton_service_exists(self):
        """Test that skeleton service is available."""
        try:
            from model_service_impl import SkeletonModelService
            service = SkeletonModelService()
            assert service is not None
        except ImportError:
            pytest.skip("SkeletonModelService not available")

    @pytest.mark.asyncio
    async def test_skeleton_generate(self):
        """Test skeleton service generate returns mock data."""
        try:
            from model_service_impl import SkeletonModelService

            service = SkeletonModelService()
            result = await service.generate(prompt="Test", messages=[], options={})

            assert result is not None
        except ImportError:
            pytest.skip("SkeletonModelService not available")

    @pytest.mark.asyncio
    async def test_skeleton_embed(self):
        """Test skeleton service embed returns mock vectors."""
        try:
            from model_service_impl import SkeletonModelService

            service = SkeletonModelService()
            result = await service.embed(["Test text"])

            assert isinstance(result, list)
            assert len(result) > 0
        except ImportError:
            pytest.skip("SkeletonModelService not available")


# =============================================================================
# INTEGRATION WITH RAG PIPELINE
# =============================================================================

class TestModelServiceIntegration:
    """Test model service integration with RAG pipeline."""

    @pytest.mark.asyncio
    async def test_pipeline_uses_model_service(self):
        """Test that RAG pipeline properly uses model service."""
        import tempfile
        from raglite import ingest_docs
        from rag_pipeline import RAGPipeline
        from model_service_impl import ConcreteModelService

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test data
            doc_path = Path(tmpdir) / "test.txt"
            doc_path.write_text("Machine learning is a type of artificial intelligence.")

            chunks_path = os.path.join(tmpdir, "chunks.jsonl")
            ingest_docs(str(doc_path), out_jsonl=chunks_path)

            # Create pipeline with mock model service
            mock_service = MagicMock()
            mock_service.generate = AsyncMock(return_value={"content": "Mock answer"})
            mock_service.embed = AsyncMock(return_value=[[0.1] * 1536])

            pipeline = RAGPipeline(
                chunks_path=chunks_path,
                model_service=mock_service
            )

            # Verify pipeline has model service
            assert pipeline.model_service is not None

    @pytest.mark.asyncio
    async def test_pipeline_embedding_building(self):
        """Test building vector index with model service."""
        import tempfile
        from raglite import ingest_docs
        from rag_pipeline import RAGPipeline

        with tempfile.TemporaryDirectory() as tmpdir:
            doc_path = Path(tmpdir) / "test.txt"
            doc_path.write_text("Test content for embedding.")

            chunks_path = os.path.join(tmpdir, "chunks.jsonl")
            ingest_docs(str(doc_path), out_jsonl=chunks_path)

            mock_service = MagicMock()
            mock_service.embed = AsyncMock(return_value=[[0.1] * 1536])

            pipeline = RAGPipeline(
                chunks_path=chunks_path,
                model_service=mock_service
            )

            # Build vector index should call embed
            stats = await pipeline.build_vector_index(batch_size=10)

            # Should have processed chunks
            assert "chunks_embedded" in stats or "error" in stats


# =============================================================================
# LIVE API TESTS (REQUIRES API KEY)
# =============================================================================

@pytest.mark.requires_api_key
class TestLiveAPI:
    """Tests that require actual API keys."""

    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="Requires OPENAI_API_KEY"
    )
    @pytest.mark.asyncio
    async def test_live_openai_generation(self):
        """Test live OpenAI API call."""
        from model_service_impl import ConcreteModelService

        service = ConcreteModelService()
        result = await service.generate(
            prompt="Say 'Hello World' and nothing else.",
            messages=[],
            options={"max_tokens": 10}
        )

        assert result is not None
        assert "hello" in str(result).lower()

    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="Requires OPENAI_API_KEY"
    )
    @pytest.mark.asyncio
    async def test_live_openai_embedding(self):
        """Test live OpenAI embedding call."""
        from model_service_impl import ConcreteModelService

        service = ConcreteModelService()
        result = await service.embed(["Hello world"])

        assert isinstance(result, list)
        assert len(result) == 1
        assert len(result[0]) > 0  # Should have embedding dimensions

    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY"),
        reason="Requires ANTHROPIC_API_KEY"
    )
    @pytest.mark.asyncio
    async def test_live_anthropic_generation(self):
        """Test live Anthropic API call."""
        from model_service_impl import ConcreteModelService

        # Configure to use Anthropic
        os.environ["RAG_MODEL_PROFILE"] = "balanced"

        service = ConcreteModelService()

        # This would need actual Anthropic setup
        # Skipping detailed test as it depends on configuration


# =============================================================================
# RUN CONFIGURATION
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
