# ModelService Implementation

This implementation provides the **Model Flex Layer** as specified in the architecture docs, enabling profile-based routing to different LLM providers.

## What Was Built

### 1. Core Interface (`model_service.py`)
- Abstract `ModelService` base class
- Type definitions for all operations:
  - `generate()` - Chat/text generation
  - `embed()` - Embedding generation
  - `rerank()` - Result reranking
- Complete type safety with TypedDict definitions

### 2. Configuration System (`model_config.py`)
- `ModelConfig` dataclass for model definitions
- `ModelRegistry` for managing model configurations
- Profile mappings: `cheap` → `balanced` → `premium`
- Environment-based configuration:
  - `MODEL_CHEAP` - Override cheap profile model
  - `MODEL_BALANCED` - Override balanced profile model
  - `MODEL_PREMIUM` - Override premium profile model
  - `MODEL_EMBEDDING` - Override embedding model

### 3. Concrete Implementation (`model_service_impl.py`)
- `ConcreteModelService` - Full implementation
- Provider support:
  - ✅ OpenAI (chat + embeddings)
  - ✅ Anthropic (chat)
  - ⏳ Reranking (placeholder - ready for Cohere/similar)
- Lazy client initialization
- Error handling and logging

### 4. Test Suite (`test_model_service.py`)
- Validates all three profiles
- Tests embedding generation
- Tests specific model overrides
- Tests error handling
- Checks API key configuration

## Default Model Mappings

| Profile    | Default Model        | Provider   |
|------------|---------------------|------------|
| `cheap`    | gpt-3.5-turbo       | OpenAI     |
| `balanced` | claude-3-sonnet     | Anthropic  |
| `premium`  | claude-3-opus       | Anthropic  |
| embedding  | text-embedding-3-small | OpenAI  |

## Usage Examples

### Basic Generation with Profile

```python
import asyncio
from model_service_impl import ConcreteModelService
from model_service import Message

async def example():
    service = ConcreteModelService()
    
    result = await service.generate({
        'modelProfile': 'cheap',  # or 'balanced' or 'premium'
        'messages': [
            Message(role='system', content='You are a helpful assistant.'),
            Message(role='user', content='Explain RAG in one sentence.')
        ],
        'maxTokens': 100,
        'temperature': 0.7
    })
    
    print(result['content'])

asyncio.run(example())
```

### Generate Embeddings

```python
async def embed_example():
    service = ConcreteModelService()
    
    result = await service.embed({
        'texts': [
            'First document to embed',
            'Second document to embed'
        ]
    })
    
    print(f"Generated {len(result['vectors'])} embeddings")
    print(f"Dimension: {len(result['vectors'][0])}")
```

### Override with Specific Model

```python
async def specific_model():
    service = ConcreteModelService()
    
    result = await service.generate({
        'modelId': 'gpt-4',  # Bypass profile, use specific model
        'messages': [
            Message(role='user', content='Complex reasoning task...')
        ]
    })
```

## Configuration

### Environment Variables Required

```bash
# In your .env file
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Optional: Override default profile mappings
MODEL_CHEAP=gpt-3.5-turbo
MODEL_BALANCED=gpt-4
MODEL_PREMIUM=claude-3-opus-20240229
MODEL_EMBEDDING=text-embedding-3-large
```

### Custom Model Registration

```python
from model_config import get_registry, ModelConfig

registry = get_registry()

# Add a custom model
registry.register_model(ModelConfig(
    id="my-custom-model",
    provider="openai",
    type="chat",
    profile="balanced",
    modelName="gpt-4-turbo",
    apiKeyRef="OPENAI_API_KEY",
    maxTokens=8192
))

# Update profile mapping
registry.set_profile_mapping('balanced', 'my-custom-model')
```

## Running Tests

```bash
# Make sure API keys are set in .env
python test_model_service.py
```

## Integration with Existing Code

This implementation is **self-contained** and does NOT modify existing behavior:

- ✅ `llm_providers.py` - Still works as before
- ✅ `server.py` - No changes
- ✅ `raglite.py` - No changes

To integrate:

1. **For new features**: Use `ConcreteModelService` directly
2. **For existing code**: Gradually migrate when ready
3. **For RAG pipeline**: Pass `ConcreteModelService` to `RAGPipeline`

## Architecture Alignment

This implementation follows:
- ✅ `docs/02-Architecture-Blueprint.md` - Model Flex Layer section
- ✅ `docs/04-Model-Flex-Layer-Spec.md` - Complete spec
- ✅ Single abstraction for all LLM usage
- ✅ Profile-based routing (cheap/balanced/premium)
- ✅ Provider abstraction (OpenAI, Anthropic, extensible)

## Next Steps

Recommended follow-ups:

1. **Connect to RAG Pipeline**: Pass `ConcreteModelService` to `RAGPipeline` for embeddings
2. **Add Reranking**: Implement real reranker (Cohere, Jina, etc.)
3. **Database Integration**: Store model usage logs, costs, latency
4. **Rate Limiting**: Add per-profile rate limits and quotas
5. **Caching**: Cache embeddings for repeated texts



