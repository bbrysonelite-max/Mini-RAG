"""
Model Configuration - Maps profiles to actual models.

Defines which models are used for cheap/balanced/premium profiles.
Configuration can be loaded from environment variables or config files.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from model_service import ModelProfile, ModelProvider, ModelType


@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    id: str
    provider: ModelProvider
    type: ModelType
    profile: Optional[ModelProfile]
    modelName: str
    apiKeyRef: str  # Environment variable name
    maxTokens: int
    costPer1kTokens: Optional[float] = None
    extraConfig: Optional[Dict[str, Any]] = None


# Default model configurations
DEFAULT_MODELS: Dict[str, ModelConfig] = {
    # ------------------------
    # Chat models (Anthropic)
    # ------------------------
    "claude-3-haiku": ModelConfig(
        id="claude-3-haiku",
        provider="anthropic",
        type="chat",
        profile="cheap",
        modelName="claude-3-haiku-20240307",
        apiKeyRef="ANTHROPIC_API_KEY",
        maxTokens=4096,
        costPer1kTokens=0.001,  # example pricing
    ),
    "claude-3-sonnet": ModelConfig(
        id="claude-3-sonnet",
        provider="anthropic",
        type="chat",
        profile="balanced",
        modelName="claude-3-5-sonnet-20241022",
        apiKeyRef="ANTHROPIC_API_KEY",
        maxTokens=8192,
        costPer1kTokens=0.003,
    ),
    "claude-3-opus": ModelConfig(
        id="claude-3-opus",
        provider="anthropic",
        type="chat",
        profile="premium",
        modelName="claude-3-opus-20240229",
        apiKeyRef="ANTHROPIC_API_KEY",
        maxTokens=4096,
        costPer1kTokens=0.015,
    ),

    # ------------------------
    # Embedding models
    # (still OpenAI for now; easier to leave as-is)
    # ------------------------
    "text-embedding-3-small": ModelConfig(
        id="text-embedding-3-small",
        provider="openai",
        type="embedding",
        profile=None,
        modelName="text-embedding-3-small",
        apiKeyRef="OPENAI_API_KEY",
        maxTokens=8192,
        costPer1kTokens=0.00002,
    ),
    "text-embedding-3-large": ModelConfig(
        id="text-embedding-3-large",
        provider="openai",
        type="embedding",
        profile=None,
        modelName="text-embedding-3-large",
        apiKeyRef="OPENAI_API_KEY",
        maxTokens=8192,
        costPer1kTokens=0.00013,
    ),
}


# Profile to model mappings (can be overridden via environment)
DEFAULT_PROFILE_MAPPINGS: Dict[ModelProfile, str] = {
    "cheap": os.getenv("MODEL_CHEAP", "claude-3-haiku"),
    "balanced": os.getenv("MODEL_BALANCED", "claude-3-sonnet"),
    "premium": os.getenv("MODEL_PREMIUM", "claude-3-opus"),
}


# Default embedding model
DEFAULT_EMBEDDING_MODEL = os.getenv("MODEL_EMBEDDING", "text-embedding-3-small")


class ModelRegistry:
    """
    Registry for model configurations.

    Provides lookup for models by ID or by profile.
    """

    def __init__(self, models: Optional[Dict[str, ModelConfig]] = None):
        """
        Initialize model registry.

        Args:
            models: Optional custom model configurations (defaults to DEFAULT_MODELS)
        """
        self.models = models or DEFAULT_MODELS.copy()
        self.profile_mappings = DEFAULT_PROFILE_MAPPINGS.copy()
        self.default_embedding = DEFAULT_EMBEDDING_MODEL

    def get_model(self, model_id: str) -> Optional[ModelConfig]:
        """Get model configuration by ID."""
        return self.models.get(model_id)

    def get_model_by_profile(self, profile: ModelProfile) -> Optional[ModelConfig]:
        """
        Get model configuration by profile (cheap/balanced/premium).
        """
        model_id = self.profile_mappings.get(profile)
        if not model_id:
            return None
        return self.get_model(model_id)

    def get_embedding_model(self, model_id: Optional[str] = None) -> Optional[ModelConfig]:
        """
        Get embedding model configuration.
        """
        target_id = model_id or self.default_embedding
        return self.get_model(target_id)

    def get_api_key(self, config: ModelConfig) -> Optional[str]:
        """
        Get API key for a model from environment.
        """
        return os.getenv(config.apiKeyRef)

    def register_model(self, config: ModelConfig) -> None:
        """Register a new model configuration."""
        self.models[config.id] = config

    def set_profile_mapping(self, profile: ModelProfile, model_id: str) -> None:
        """
        Set which model to use for a profile.
        """
        self.profile_mappings[profile] = model_id


# Global registry instance
_global_registry: Optional[ModelRegistry] = None


def get_registry() -> ModelRegistry:
    """Get the global model registry instance."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ModelRegistry()
    return _global_registry
