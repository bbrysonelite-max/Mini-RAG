"""
Concrete ModelService Implementation.

Implements the ModelService interface with real provider calls to:
- OpenAI (ChatGPT, embeddings)
- Anthropic (Claude)
"""

import os
from typing import List, Optional
import logging

from model_service import (
    ModelService,
    GenerateOptions,
    GenerateResult,
    EmbedOptions,
    EmbedResult,
    RerankOptions,
    RerankResultItem,
    Message
)
from model_config import ModelRegistry, get_registry, ModelConfig

logger = logging.getLogger(__name__)


class ConcreteModelService(ModelService):
    """
    Concrete implementation of ModelService.
    
    Routes requests to appropriate providers based on:
    - Profile (cheap/balanced/premium) for generation
    - Specific modelId overrides
    - Model configurations in ModelRegistry
    """
    
    def __init__(self, registry: Optional[ModelRegistry] = None):
        """
        Initialize ModelService with a model registry.
        
        Args:
            registry: Optional ModelRegistry (defaults to global registry)
        """
        self.registry = registry or get_registry()
        self._openai_client = None
        self._anthropic_client = None
    
    def _get_openai_client(self):
        """Lazy-load OpenAI client."""
        if self._openai_client is None:
            try:
                import openai
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    self._openai_client = openai.OpenAI(api_key=api_key)
                else:
                    logger.warning("OPENAI_API_KEY not set")
            except ImportError:
                logger.warning("openai package not installed")
        return self._openai_client
    
    def _get_anthropic_client(self):
        """Lazy-load Anthropic client."""
        if self._anthropic_client is None:
            try:
                import anthropic
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if api_key:
                    self._anthropic_client = anthropic.Anthropic(api_key=api_key)
                else:
                    logger.warning("ANTHROPIC_API_KEY not set")
            except ImportError:
                logger.warning("anthropic package not installed")
        return self._anthropic_client
    
    async def generate(self, opts: GenerateOptions) -> GenerateResult:
        """
        Generate text using a chat model.
        
        Process:
        1. Resolve modelProfile or modelId to a ModelConfig
        2. Get API client for the provider
        3. Call provider with messages and parameters
        4. Return GenerateResult
        
        Args:
            opts: Generation options
            
        Returns:
            GenerateResult with generated content
            
        Raises:
            ValueError: If model not found or provider not supported
            RuntimeError: If API call fails
        """
        # Resolve model
        config = self._resolve_model(opts)
        if not config:
            raise ValueError(
                f"Could not resolve model for profile={opts.get('modelProfile')} "
                f"or modelId={opts.get('modelId')}"
            )
        
        # Extract options
        messages = opts.get('messages', [])
        max_tokens = opts.get('maxTokens', config.maxTokens)
        temperature = opts.get('temperature', 0.7)
        
        # Route to provider
        if config.provider == 'openai':
            return await self._generate_openai(config, messages, max_tokens, temperature)
        elif config.provider == 'anthropic':
            return await self._generate_anthropic(config, messages, max_tokens, temperature)
        else:
            raise ValueError(f"Unsupported provider: {config.provider}")
    
    def _resolve_model(self, opts: GenerateOptions) -> Optional[ModelConfig]:
        """Resolve model config from options."""
        # Explicit modelId takes precedence
        model_id = opts.get('modelId')
        if model_id:
            return self.registry.get_model(model_id)
        
        # Fall back to profile
        profile = opts.get('modelProfile')
        if profile:
            return self.registry.get_model_by_profile(profile)
        
        return None
    
    async def _generate_openai(
        self,
        config: ModelConfig,
        messages: List[Message],
        max_tokens: int,
        temperature: float
    ) -> GenerateResult:
        """Generate using OpenAI API."""
        client = self._get_openai_client()
        if not client:
            raise RuntimeError("OpenAI client not available")
        
        try:
            # Convert messages to OpenAI format
            openai_messages = [
                {"role": msg["role"], "content": msg["content"]}
                for msg in messages
            ]
            
            response = client.chat.completions.create(
                model=config.modelName,
                messages=openai_messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            content = response.choices[0].message.content or ""
            
            return GenerateResult(
                content=content,
                raw=response.model_dump() if hasattr(response, 'model_dump') else None
            )
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise RuntimeError(f"OpenAI generation failed: {str(e)}")
    
    async def _generate_anthropic(
        self,
        config: ModelConfig,
        messages: List[Message],
        max_tokens: int,
        temperature: float
    ) -> GenerateResult:
        """Generate using Anthropic API."""
        client = self._get_anthropic_client()
        if not client:
            raise RuntimeError("Anthropic client not available")
        
        try:
            # Extract system message if present
            system_message = None
            anthropic_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    anthropic_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            # Call Anthropic API
            kwargs = {
                "model": config.modelName,
                "max_tokens": max_tokens,
                "messages": anthropic_messages,
                "temperature": temperature
            }
            if system_message:
                kwargs["system"] = system_message
            
            response = client.messages.create(**kwargs)
            
            content = response.content[0].text if response.content else ""
            
            return GenerateResult(
                content=content,
                raw=response.model_dump() if hasattr(response, 'model_dump') else None
            )
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise RuntimeError(f"Anthropic generation failed: {str(e)}")
    
    async def embed(self, opts: EmbedOptions) -> EmbedResult:
        """
        Generate embeddings for text(s).
        
        Args:
            opts: Embedding options
            
        Returns:
            EmbedResult with embedding vectors
            
        Raises:
            ValueError: If model not found or not an embedding model
            RuntimeError: If API call fails
        """
        # Resolve embedding model
        model_id = opts.get('modelId')
        config = self.registry.get_embedding_model(model_id)
        
        if not config:
            raise ValueError(f"Could not find embedding model: {model_id}")
        
        if config.type != 'embedding':
            raise ValueError(f"Model {config.id} is not an embedding model")
        
        texts = opts.get('texts', [])
        if not texts:
            return EmbedResult(vectors=[])
        
        # Route to provider
        if config.provider == 'openai':
            return await self._embed_openai(config, texts)
        else:
            raise ValueError(f"Unsupported embedding provider: {config.provider}")
    
    async def _embed_openai(self, config: ModelConfig, texts: List[str]) -> EmbedResult:
        """Generate embeddings using OpenAI API."""
        client = self._get_openai_client()
        if not client:
            raise RuntimeError("OpenAI client not available")
        
        try:
            response = client.embeddings.create(
                model=config.modelName,
                input=texts
            )
            
            vectors = [item.embedding for item in response.data]
            
            return EmbedResult(vectors=vectors)
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            raise RuntimeError(f"OpenAI embedding failed: {str(e)}")
    
    async def rerank(self, opts: RerankOptions) -> List[RerankResultItem]:
        """
        Rerank items based on query relevance.
        
        Note: This is a placeholder implementation.
        Real reranking would use a dedicated reranker model (e.g., Cohere rerank).
        For now, returns items with score=0.5 (no actual reranking).
        
        Args:
            opts: Rerank options
            
        Returns:
            List of items with scores (unchanged order for now)
        """
        items = opts.get('items', [])
        
        # Placeholder: return items with neutral score
        # TODO: Implement real reranking with Cohere or similar
        logger.warning("Reranking not yet implemented - returning items unchanged")
        
        return [
            RerankResultItem(
                id=item['id'],
                text=item['text'],
                score=0.5  # Neutral score
            )
            for item in items
        ]



