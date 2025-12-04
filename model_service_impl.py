"""
Concrete ModelService Implementation.

Implements the ModelService interface with real provider calls to:
- OpenAI (ChatGPT, embeddings)
- Anthropic (Claude)
"""

import os
from typing import List, Optional
import logging

from config_utils import ensure_not_placeholder
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
                api_key = ensure_not_placeholder(
                    "OPENAI_API_KEY",
                    os.getenv("OPENAI_API_KEY"),
                    {"sk_test_placeholder", "sk-openai-placeholder"},
                    required=False,
                )
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
                api_key = ensure_not_placeholder(
                    "ANTHROPIC_API_KEY",
                    os.getenv("ANTHROPIC_API_KEY"),
                    {"anthropic-placeholder"},
                    required=False,
                )
                if api_key:
                    self._anthropic_client = anthropic.Anthropic(api_key=api_key)
                else:
                    logger.warning("ANTHROPIC_API_KEY not set")
            except ImportError:
                logger.warning("anthropic package not installed")
        return self._anthropic_client
    
    async def generate(self, opts: GenerateOptions) -> GenerateResult:
        """
        Generate text using configured model with automatic fallback.
        
        Tries providers in order: user preference > OpenAI > Anthropic
        
        Args:
            opts: Generation options
            
        Returns:
            GenerateResult with generated content
            
        Raises:
            RuntimeError: If ALL providers fail
        """
        # Extract options
        messages = opts.get('messages', [])
        max_tokens = opts.get('maxTokens', 4096)
        temperature = opts.get('temperature', 0.7)
        
        # Resolve model if specified
        config = self._resolve_model(opts)
        
        # Build provider chain: requested provider first, then fallbacks
        providers_to_try = []
        if config:
            providers_to_try.append(config.provider)
        
        # Always add fallbacks (OpenAI then Anthropic)
        for provider in ['openai', 'anthropic']:
            if provider not in providers_to_try:
                providers_to_try.append(provider)
        
        errors = []
        for provider in providers_to_try:
            try:
                if provider == 'openai':
                    # Get or create OpenAI config
                    openai_config = config if (config and config.provider == 'openai') else self.registry.get_model('gpt-4o')
                    if openai_config and self._get_openai_client():
                        result = await self._generate_openai(openai_config, messages, max_tokens, temperature)
                        logger.info(f"Generation succeeded with OpenAI ({openai_config.modelName})")
                        return result
                    else:
                        errors.append("OpenAI: API key not configured")
                        
                elif provider == 'anthropic':
                    # Get or create Anthropic config
                    anthropic_config = config if (config and config.provider == 'anthropic') else self.registry.get_model('claude-3-sonnet')
                    if anthropic_config and self._get_anthropic_client():
                        result = await self._generate_anthropic(anthropic_config, messages, max_tokens, temperature)
                        logger.info(f"Generation succeeded with Anthropic ({anthropic_config.modelName})")
                        return result
                    else:
                        errors.append("Anthropic: API key not configured")
                        
            except Exception as e:
                error_msg = f"{provider}: {str(e)}"
                errors.append(error_msg)
                logger.warning(f"Provider {provider} failed: {e}")
                continue
        
        # All providers failed
        error_summary = "; ".join(errors)
        raise RuntimeError(f"All LLM providers failed. {error_summary}")
    
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
            
            # Use client directly - extra_headers can cause compatibility issues
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
            # Use client directly - extra_headers can cause compatibility issues
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
        Rerank items based on query relevance using Cohere or OpenAI fallback.
        
        Uses state-of-the-art cross-encoder reranking:
        1. Cohere rerank-v3.5 (if COHERE_API_KEY available) - Best quality
        2. OpenAI-based relevance scoring (fallback)
        
        Args:
            opts: Rerank options with query and items
            
        Returns:
            List of items sorted by relevance score (highest first)
        """
        query = opts.get('query', '')
        items = opts.get('items', [])
        
        if not items:
            return []
        
        # Try Cohere first (state-of-the-art reranker)
        cohere_key = os.environ.get('COHERE_API_KEY')
        if cohere_key:
            try:
                return await self._rerank_cohere(query, items, cohere_key)
            except Exception as e:
                logger.warning(f"Cohere rerank failed, falling back to OpenAI: {e}")
        
        # Fallback to OpenAI-based reranking
        try:
            return await self._rerank_openai(query, items)
        except Exception as e:
            logger.error(f"OpenAI rerank failed: {e}")
            # Last resort: return items with BM25-like keyword scoring
            return self._rerank_keyword_fallback(query, items)
    
    async def _rerank_cohere(self, query: str, items: List, api_key: str) -> List[RerankResultItem]:
        """Rerank using Cohere's rerank-v3.5 model (best-in-class)."""
        import httpx
        
        documents = [item.get('text', '') for item in items]
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.cohere.ai/v1/rerank",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "rerank-v3.5",
                    "query": query,
                    "documents": documents,
                    "top_n": len(documents),
                    "return_documents": False
                }
            )
            response.raise_for_status()
            data = response.json()
        
        # Map results back to items
        results = []
        for result in data.get('results', []):
            idx = result['index']
            score = result['relevance_score']
            item = items[idx]
            results.append(RerankResultItem(
                id=item.get('id', ''),
                text=item.get('text', ''),
                score=score
            ))
        
        # Sort by score descending
        results.sort(key=lambda x: x['score'], reverse=True)
        logger.info(f"Cohere reranked {len(results)} items")
        return results
    
    async def _rerank_openai(self, query: str, items: List) -> List[RerankResultItem]:
        """Rerank using OpenAI by scoring relevance of each document."""
        import asyncio
        
        client = self._get_openai_client()
        if not client:
            raise RuntimeError("OpenAI client not available")
        
        # Score each item's relevance to the query
        results = []
        for item in items:
            text = item.get('text', '')[:500]  # Truncate for efficiency
            
            # Run sync OpenAI call in thread pool
            def call_openai():
                return client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Rate the relevance of the document to the query on a scale of 0.0 to 1.0. Reply with ONLY a decimal number."},
                        {"role": "user", "content": f"Query: {query}\n\nDocument: {text}"}
                    ],
                    max_tokens=10,
                    temperature=0
                )
            
            response = await asyncio.to_thread(call_openai)
            
            try:
                score = float(response.choices[0].message.content.strip())
                score = max(0.0, min(1.0, score))  # Clamp to 0-1
            except (ValueError, AttributeError):
                score = 0.5
            
            results.append(RerankResultItem(
                id=item.get('id', ''),
                text=item.get('text', ''),
                score=score
            ))
        
        # Sort by score descending
        results.sort(key=lambda x: x['score'], reverse=True)
        logger.info(f"OpenAI reranked {len(results)} items")
        return results
    
    def _rerank_keyword_fallback(self, query: str, items: List) -> List[RerankResultItem]:
        """Simple keyword-based fallback reranking."""
        query_terms = set(query.lower().split())
        
        results = []
        for item in items:
            text = item.get('text', '').lower()
            # Count matching terms
            matches = sum(1 for term in query_terms if term in text)
            score = matches / max(len(query_terms), 1)
            
            results.append(RerankResultItem(
                id=item.get('id', ''),
                text=item.get('text', ''),
                score=score
            ))
        
        results.sort(key=lambda x: x['score'], reverse=True)
        logger.info(f"Keyword fallback reranked {len(results)} items")
        return results



