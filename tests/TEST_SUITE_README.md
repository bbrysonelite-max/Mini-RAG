# Mini-RAG / Second Brain Test Suite

Comprehensive test suite for quality assurance, functionality testing, and stress testing of the Mini-RAG system.

## Quick Start

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-timeout httpx aiohttp

# Run all tests
python tests/run_tests.py

# Run quick tests (skip slow/stress tests)
python tests/run_tests.py --quick

# Run with coverage
python tests/run_tests.py --coverage
```

## Test Categories

### 1. Quality Assurance Tests (`test_suite_comprehensive.py`)

Tests API contracts, input validation, error handling, and security:

- **TestAPIContract**: Verifies API response formats, required endpoints, OpenAPI spec
- **TestInputValidation**: Tests input sanitization, parameter bounds, file type validation
- **TestErrorHandling**: Tests 404/405 responses, invalid JSON, graceful degradation
- **TestSecurityHeaders**: Verifies security headers, CORS, sensitive data protection

```bash
python tests/run_tests.py --qa
```

### 2. App Functionality Tests (`test_suite_comprehensive.py`)

Tests core RAG pipeline functionality:

- **TestRAGPipeline**: BM25 search, retrieval with filters, pipeline initialization
- **TestIngestion**: Document ingestion, metadata preservation, chunking
- **TestWorkspaceIsolation**: Multi-tenant data isolation
- **TestChunkBackup**: Backup creation and restore

```bash
pytest tests/test_suite_comprehensive.py -k "TestRAG or TestIngestion" -v
```

### 3. Stress Tests (`test_stress_advanced.py`)

Load testing and resource limit testing:

- **TestConcurrentLoad**: 100+ concurrent requests, mixed endpoint load, sustained load
- **TestMemoryStress**: Large chunk volumes, memory usage monitoring, leak detection
- **TestFileIOStress**: Concurrent file writes, rapid read/write cycles
- **TestSearchStress**: Extreme k values, special characters, throughput measurement
- **TestPipelineStress**: Concurrent pipeline queries, filter performance
- **TestRecoveryStress**: Corrupted file handling, empty file handling
- **TestEdgeCaseStress**: Very long documents, many small documents

```bash
python tests/run_tests.py --stress
```

### 4. Model Service Tests (`test_model_service_comprehensive.py`)

Tests LLM provider integration:

- **TestModelConfig**: Model profiles, configuration validation
- **TestModelServiceInterface**: Service instantiation, method contracts
- **TestLLMProviders**: Provider availability, error handling
- **TestEmbeddings**: Single/batch embedding, long text handling
- **TestResponseGeneration**: System prompts, context, conversation history
- **TestErrorHandling**: API key errors, rate limits, network errors

```bash
pytest tests/test_model_service_comprehensive.py -v
```

### 5. Database & Vector Store Tests (`test_database_vector_store.py`)

Tests database operations and vector storage:

- **TestDatabaseConnection**: Connection handling, CRUD operations
- **TestVectorStore**: Chunk storage, similarity search, deletion
- **TestChunkDatabase**: JSONL migration, export
- **TestDatabaseSchema**: Schema validation
- **TestDatabaseWorkspaceIsolation**: Workspace-level data isolation
- **TestDatabasePerformance**: Bulk inserts, query performance
- **TestConnectionPool**: Concurrent connections
- **TestDatabaseErrorHandling**: Connection/query errors

```bash
pytest tests/test_database_vector_store.py -v
```

## Running Specific Tests

```bash
# Run a specific test class
pytest tests/test_suite_comprehensive.py::TestAPIContract -v

# Run a specific test method
pytest tests/test_suite_comprehensive.py::TestAPIContract::test_health_returns_correct_format -v

# Run tests matching a pattern
pytest tests/ -k "health" -v

# Run tests with specific markers
pytest tests/ -m "not slow" -v
pytest tests/ -m "requires_api_key" -v
```

## Test Markers

- `@pytest.mark.slow` - Long-running tests (stress tests)
- `@pytest.mark.requires_api_key` - Tests needing OPENAI_API_KEY or ANTHROPIC_API_KEY
- `@pytest.mark.requires_db` - Tests needing DATABASE_URL
- `@pytest.mark.asyncio` - Async tests

## Environment Variables

Tests use these environment variables:

```bash
# Required for testing (set automatically)
ALLOW_INSECURE_DEFAULTS=true
LOCAL_MODE=true

# Optional - for live API tests
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=postgresql://user:pass@host/db
```

## Test Output

```bash
# Verbose output with short tracebacks
pytest tests/ -v --tb=short

# Show print statements
pytest tests/ -v -s

# Stop on first failure
pytest tests/ -v -x

# Show slowest tests
pytest tests/ -v --durations=10
```

## Coverage Reports

```bash
# Generate coverage report
pytest tests/ --cov=. --cov-report=html

# View coverage
open htmlcov/index.html
```

## Test File Structure

```
tests/
├── conftest.py                        # Shared fixtures
├── run_tests.py                       # Test runner script
├── TEST_SUITE_README.md               # This file
│
├── test_suite_comprehensive.py        # Main test suite
│   ├── TestAPIContract                # API contract tests
│   ├── TestInputValidation            # Input validation
│   ├── TestErrorHandling              # Error handling
│   ├── TestSecurityHeaders            # Security tests
│   ├── TestRAGPipeline                # RAG functionality
│   ├── TestIngestion                  # Document ingestion
│   ├── TestWorkspaceIsolation         # Multi-tenancy
│   ├── TestChunkBackup                # Backup/restore
│   ├── TestLoadStress                 # Load testing
│   ├── TestResourceLimits             # Resource limits
│   ├── TestEndToEndWorkflows          # Integration tests
│   ├── TestAuthenticationFlow         # Auth tests
│   ├── TestMetricsAndObservability    # Metrics tests
│   ├── TestQuotaService               # Quota enforcement
│   ├── TestRateLimiting               # Rate limits
│   ├── TestCacheService               # Caching
│   └── TestDataIntegrity              # Data integrity
│
├── test_stress_advanced.py            # Advanced stress tests
│   ├── TestConcurrentLoad             # Concurrent requests
│   ├── TestMemoryStress               # Memory pressure
│   ├── TestFileIOStress               # File I/O stress
│   ├── TestSearchStress               # Search stress
│   ├── TestPipelineStress             # Pipeline stress
│   ├── TestRecoveryStress             # Recovery tests
│   └── TestEdgeCaseStress             # Edge cases
│
├── test_model_service_comprehensive.py # Model service tests
│   ├── TestModelConfig                # Configuration
│   ├── TestModelServiceInterface      # Interface tests
│   ├── TestLLMProviders               # Provider tests
│   ├── TestEmbeddings                 # Embedding tests
│   ├── TestResponseGeneration         # Generation tests
│   ├── TestErrorHandling              # Error handling
│   ├── TestSkeletonModelService       # Mock service
│   ├── TestModelServiceIntegration    # Integration
│   └── TestLiveAPI                    # Live API tests
│
└── test_database_vector_store.py      # Database tests
    ├── TestDatabaseConnection         # Connection tests
    ├── TestVectorStore                # Vector store
    ├── TestChunkDatabase              # Chunk operations
    ├── TestDatabaseSchema             # Schema validation
    ├── TestMigrations                 # Migration tests
    ├── TestDatabaseWorkspaceIsolation # Workspace isolation
    ├── TestDatabasePerformance        # Performance
    ├── TestConnectionPool             # Connection pooling
    ├── TestDatabaseErrorHandling      # Error handling
    └── TestLiveDatabase               # Live DB tests
```

## Writing New Tests

### Basic Test Structure

```python
import pytest
from pathlib import Path

class TestMyFeature:
    """Test description."""

    def test_basic_functionality(self, client):
        """Test that feature works correctly."""
        response = client.get("/endpoint")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_async_operation(self):
        """Test async functionality."""
        result = await some_async_function()
        assert result is not None

    @pytest.mark.slow
    def test_performance(self):
        """Performance test (marked slow)."""
        # Long-running test
        pass
```

### Using Fixtures

```python
@pytest.fixture
def sample_data(temp_dir):
    """Create sample data for tests."""
    doc = Path(temp_dir) / "test.txt"
    doc.write_text("Test content")
    return str(doc)

def test_with_sample_data(sample_data):
    """Test using sample data fixture."""
    assert os.path.exists(sample_data)
```

## CI/CD Integration

```yaml
# GitHub Actions example
- name: Run Tests
  run: |
    pip install pytest pytest-asyncio pytest-timeout httpx
    python tests/run_tests.py --quick

- name: Run Full Test Suite
  run: |
    python tests/run_tests.py --coverage
```

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure you're running from the project root
   ```bash
   cd /path/to/mini-rag
   python tests/run_tests.py
   ```

2. **Async test failures**: Install pytest-asyncio
   ```bash
   pip install pytest-asyncio
   ```

3. **Timeout errors**: Increase timeout for slow tests
   ```bash
   pytest tests/ --timeout=300
   ```

4. **Database tests failing**: Set DATABASE_URL or skip with
   ```bash
   pytest tests/ -m "not requires_db"
   ```

## Performance Benchmarks

Expected performance on standard hardware:

| Test Category | Tests | Duration |
|---------------|-------|----------|
| Quick tests | ~50 | <30s |
| Full suite | ~150 | <5min |
| Stress tests | ~30 | <10min |

## Contributing

When adding new tests:

1. Follow existing naming conventions (`test_*.py`, `Test*` classes, `test_*` methods)
2. Add appropriate markers (`@pytest.mark.slow`, etc.)
3. Include docstrings describing what's being tested
4. Use fixtures for shared setup
5. Keep tests independent and idempotent
