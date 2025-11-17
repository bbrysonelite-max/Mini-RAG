"""
Model Flex Layer - Single abstraction for all model usage.

Provides a unified interface for:
- Chat models (generation)
- Embedding models
- Reranker models

All LLM usage goes through this layer (no direct SDK calls in business logic).
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Literal, TypedDict


# Type definitions

ModelProfile = Literal['cheap', 'balanced', 'premium']
ModelProvider = Literal['openai', 'anthropic', 'gateway', 'local']
ModelType = Literal['chat', 'embedding', 'reranker']


class Message(TypedDict):
    """Chat message with role and content."""
    role: Literal['system', 'user', 'assistant']
    content: str


class GenerateOptions(TypedDict, total=False):
    """Options for text generation."""
    modelProfile: Optional[ModelProfile]  # Route to cheap/balanced/premium
    modelId: Optional[str]  # Optional override to specific model
    messages: List[Message]
    maxTokens: Optional[int]
    temperature: Optional[float]
    metadata: Optional[Dict[str, Any]]  # For logging


class GenerateResult(TypedDict, total=False):
    """Result from text generation."""
    content: str
    raw: Optional[Any]  # Raw provider response for debugging


class EmbedOptions(TypedDict, total=False):
    """Options for embedding generation."""
    modelId: Optional[str]  # Usually a dedicated embedding model
    texts: List[str]
    metadata: Optional[Dict[str, Any]]  # For logging


class EmbedResult(TypedDict):
    """Result from embedding generation."""
    vectors: List[List[float]]  # List of embedding vectors


class RerankItem(TypedDict):
    """Item to be reranked."""
    id: str
    text: str


class RerankOptions(TypedDict, total=False):
    """Options for reranking."""
    modelId: Optional[str]
    query: str
    items: List[RerankItem]
    metadata: Optional[Dict[str, Any]]  # For logging


class RerankResultItem(TypedDict):
    """Reranked item with score."""
    id: str
    text: str
    score: float


# ModelService Interface

class ModelService(ABC):
    """
    Abstract base class for the Model Flex Layer.
    
    All LLM operations (generation, embedding, reranking) go through this interface.
    Supports profile-based routing (cheap/balanced/premium) and provider abstraction.
    """
    
    @abstractmethod
    async def generate(self, opts: GenerateOptions) -> GenerateResult:
        """
        Generate text using a chat model.
        
        Args:
            opts: Generation options including messages, profile, and parameters
            
        Returns:
            GenerateResult with content and optional raw response
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("generate must be implemented by subclass")
    
    @abstractmethod
    async def embed(self, opts: EmbedOptions) -> EmbedResult:
        """
        Generate embeddings for text(s).
        
        Args:
            opts: Embedding options including texts and optional modelId
            
        Returns:
            EmbedResult with list of embedding vectors
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("embed must be implemented by subclass")
    
    @abstractmethod
    async def rerank(self, opts: RerankOptions) -> List[RerankResultItem]:
        """
        Rerank items based on query relevance.
        
        Args:
            opts: Rerank options including query and items to rank
            
        Returns:
            List of reranked items with scores (sorted by relevance)
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("rerank must be implemented by subclass")


# Skeleton Implementation

class SkeletonModelService(ModelService):
    """
    Skeleton implementation of ModelService.
    
    This is a placeholder that returns empty/placeholder results.
    Does not call actual LLM providers - for structure only.
    """
    
    async def generate(self, opts: GenerateOptions) -> GenerateResult:
        """
        Placeholder implementation - returns empty content.
        
        In a real implementation, this would:
        1. Resolve modelProfile to a specific modelId
        2. Call the appropriate provider (OpenAI, Anthropic, etc.)
        3. Return the generated content
        """
        return GenerateResult(
            content="",
            raw=None
        )
    
    async def embed(self, opts: EmbedOptions) -> EmbedResult:
        """
        Placeholder implementation - returns empty vectors.
        
        In a real implementation, this would:
        1. Use the specified modelId or default embedding model
        2. Call the embedding provider
        3. Return vectors for each input text
        """
        return EmbedResult(
            vectors=[[] for _ in opts.get('texts', [])]
        )
    
    async def rerank(self, opts: RerankOptions) -> List[RerankResultItem]:
        """
        Placeholder implementation - returns items with zero scores.
        
        In a real implementation, this would:
        1. Use the specified modelId or default reranker
        2. Score each item against the query
        3. Return sorted list by relevance score
        """
        items = opts.get('items', [])
        return [
            RerankResultItem(
                id=item['id'],
                text=item['text'],
                score=0.0
            )
            for item in items
        ]

