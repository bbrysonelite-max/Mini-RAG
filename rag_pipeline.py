"""
RAG Pipeline - Hybrid retrieval with BM25 + vector search.

Implements the RAG pipeline as specified:
- Hybrid retrieval (BM25 + vector similarity)
- Optional reranking
- Filtering by project, source_type, confidentiality, agent_hint
- Abstention when data is insufficient
"""

import logging
from typing import List, Dict, Any, Optional, Literal, TypedDict, Tuple
from retrieval import SimpleIndex, load_chunks

logger = logging.getLogger(__name__)

# Optional pgvector support
try:
    from vector_store import VectorStore
    PGVECTOR_AVAILABLE = True
except ImportError:
    logger.warning("VectorStore not available - install psycopg[binary] for pgvector support")
    PGVECTOR_AVAILABLE = False
    VectorStore = None


# Type definitions

class Chunk(TypedDict, total=False):
    """
    Chunk representation matching the domain model.
    
    A small, retrievable unit in the index.
    """
    id: str
    documentId: str
    projectId: str
    text: str
    position: int
    startOffset: Optional[int]
    endOffset: Optional[int]
    tags: List[str]  # e.g., ['project:slug', 'source_type:youtube', 'confidentiality:public']
    ttlExpiresAt: Optional[str]  # ISO date string
    indexVersion: int
    createdAt: Optional[str]  # ISO date string


class RetrieveFilters(TypedDict, total=False):
    """Optional filters for retrieval."""
    source_type: Optional[str]  # e.g., 'youtube', 'pdf', 'url'
    confidentiality: Optional[Literal['public', 'internal', 'restricted']]
    agent_hint: Optional[Literal['blueprint', 'pdr', 'workflow', 'build_plan']]
    # date_range: Optional[Dict[str, str]]  # Future feature


class RetrieveOptions(TypedDict, total=False):
    """Options for RAG retrieval."""
    projectId: str
    userQuery: str
    filters: Optional[RetrieveFilters]
    topK_bm25: Optional[int]  # Default: 20
    topK_vector: Optional[int]  # Default: 40
    maxChunksForContext: Optional[int]  # Default: 15
    useReranker: Optional[bool]  # Default: False
    rerankerModelId: Optional[str]  # Optional reranker model override
    metadata: Optional[Dict[str, Any]]  # For logging


class ChunkWithScore(TypedDict):
    """Chunk with relevance score."""
    chunk: Chunk
    score: float
    source: Literal['bm25', 'vector', 'reranked']  # Which retrieval method found it


class RetrieveResult(TypedDict, total=False):
    """Result from RAG retrieval."""
    chunks: List[ChunkWithScore]  # Top-N chunks with scores
    totalCandidates: int  # Total candidates before filtering/truncation
    abstained: bool  # True if retrieval abstained due to low relevance
    abstentionReason: Optional[str]  # Explanation if abstained
    metadata: Optional[Dict[str, Any]]  # Retrieval metadata (latency, etc.)


# RAG Pipeline Interface

class RAGPipeline:
    """
    RAG Pipeline for hybrid retrieval.
    
    Implements:
    1. Hybrid retrieval (BM25 + vector similarity)
    2. Optional reranking via ModelService
    3. Filtering by project, source_type, confidentiality
    4. Abstention when data is insufficient
    """
    
    def __init__(
        self,
        chunks_path: str,
        model_service: Optional[Any] = None,  # ModelService instance
        vector_store: Optional[Any] = None,  # VectorStore instance (pgvector)
        topK_bm25: int = 20,
        topK_vector: int = 40,
        maxChunksForContext: int = 15,
        useReranker: bool = False,
        use_pgvector: bool = True
    ):
        """
        Initialize RAG Pipeline.
        
        Args:
            chunks_path: Path to chunks JSONL file
            model_service: Optional ModelService instance for embeddings/reranking
            vector_store: Optional VectorStore instance for pgvector (auto-created if use_pgvector=True)
            topK_bm25: Number of top BM25 results to retrieve
            topK_vector: Number of top vector results to retrieve
            maxChunksForContext: Maximum chunks to return after filtering
            useReranker: Whether to use reranker (requires model_service)
            use_pgvector: Whether to use pgvector (True) or in-memory vectors (False)
        """
        self.chunks_path = chunks_path
        self.model_service = model_service
        self.topK_bm25 = topK_bm25
        self.topK_vector = topK_vector
        self.maxChunksForContext = maxChunksForContext
        self.useReranker = useReranker
        self.use_pgvector = use_pgvector and PGVECTOR_AVAILABLE
        
        # Load chunks and build BM25 index
        self.chunks: List[Dict[str, Any]] = []
        self.bm25_index: Optional[SimpleIndex] = None
        
        # Vector storage (pgvector or in-memory fallback)
        if self.use_pgvector:
            self.vector_store_db = vector_store or (VectorStore() if PGVECTOR_AVAILABLE else None)
            self.vector_store_memory: Dict[str, List[float]] = {}  # Fallback
        else:
            self.vector_store_db = None
            self.vector_store_memory: Dict[str, List[float]] = {}  # In-memory storage
        
        self._load_index()
    
    async def build_vector_index(
        self,
        batch_size: int = 50,
        model_id: str = "text-embedding-3-small"
    ) -> Dict[str, Any]:
        """
        Build vector index by generating embeddings for all chunks.
        
        Args:
            batch_size: Number of chunks to embed at once
            model_id: Model ID to use for embeddings
            
        Returns:
            Dictionary with stats (chunks_embedded, errors, etc.)
        """
        if not self.model_service:
            return {"error": "No model service available"}
        
        if not self.chunks:
            return {"error": "No chunks loaded"}
        
        logger.info(f"Building vector index for {len(self.chunks)} chunks (pgvector={self.use_pgvector})...")
        
        embedded_count = 0
        error_count = 0
        
        # Process chunks in batches
        for i in range(0, len(self.chunks), batch_size):
            batch = self.chunks[i:i+batch_size]
            batch_texts = [c.get('content', '') for c in batch]
            batch_ids = [c.get('id', '') for c in batch]
            
            try:
                result = await self.model_service.embed({"texts": batch_texts})
                vectors = result.vectors
                
                # Store embeddings (pgvector or memory)
                if self.use_pgvector and self.vector_store_db:
                    # Batch insert to pgvector
                    embeddings_batch = [
                        (chunk_id, vector, model_id)
                        for chunk_id, vector in zip(batch_ids, vectors)
                        if chunk_id and vector
                    ]
                    
                    insert_result = await self.vector_store_db.insert_embeddings_batch(embeddings_batch)
                    embedded_count += insert_result.get('inserted', 0)
                    error_count += insert_result.get('errors', 0)
                else:
                    # Store in memory
                    for chunk_id, vector in zip(batch_ids, vectors):
                        if chunk_id and vector:
                            self.vector_store_memory[chunk_id] = vector
                            embedded_count += 1
                
                logger.info(f"Embedded batch {i//batch_size + 1}: {len(vectors)} vectors")
                
            except Exception as e:
                logger.error(f"Error embedding batch {i//batch_size + 1}: {e}")
                error_count += len(batch)
        
        storage_type = "pgvector" if self.use_pgvector else "memory"
        logger.info(f"Vector index built ({storage_type}): {embedded_count} chunks embedded, {error_count} errors")
        
        return {
            "chunks_embedded": embedded_count,
            "errors": error_count,
            "total_chunks": len(self.chunks),
            "storage_type": storage_type,
            "vector_store_size": embedded_count
        }
    
    def _load_index(self) -> None:
        """Load chunks and build BM25 index."""
        try:
            self.chunks = load_chunks(self.chunks_path)
            if self.chunks:
                self.bm25_index = SimpleIndex(self.chunks)
                logger.info(f"Loaded {len(self.chunks)} chunks from {self.chunks_path}")
            else:
                logger.warning(f"No chunks loaded from {self.chunks_path}")
        except Exception as e:
            logger.error(f"Failed to load chunks: {e}")
            self.chunks = []
            self.bm25_index = None
    
    async def retrieve(self, opts: RetrieveOptions) -> RetrieveResult:
        """
        Retrieve relevant chunks using hybrid search.
        
        Steps:
        1. Candidate Retrieval: BM25 + vector similarity
        2. Merge & Dedupe: Combine results, remove duplicates
        3. Optional Re-ranking: Use ModelService.rerank if enabled
        4. Filter & Truncate: Apply filters, limit to maxChunksForContext
        5. Abstention check: Return empty if relevance too low
        
        Args:
            opts: Retrieval options including projectId, query, filters
            
        Returns:
            RetrieveResult with chunks, scores, and metadata
            
        Raises:
            NotImplementedError: This is a skeleton - not yet implemented
        """
        # Skeleton implementation - returns empty result
        # In real implementation, this would:
        # 1. Query BM25 index for topK_bm25 chunks
        # 2. Query vector store for topK_vector chunks
        # 3. Merge and dedupe by chunk.id
        # 4. Optionally rerank using model_service.rerank()
        # 5. Apply filters (projectId, source_type, confidentiality)
        # 6. Truncate to maxChunksForContext
        # 7. Check relevance threshold and abstain if needed
        
        project_id = opts.get('projectId', '')
        query = opts.get('userQuery', '')
        filters = opts.get('filters', {})
        
        topK_bm25 = opts.get('topK_bm25', self.topK_bm25)
        topK_vector = opts.get('topK_vector', self.topK_vector)
        maxChunks = opts.get('maxChunksForContext', self.maxChunksForContext)
        useReranker = opts.get('useReranker', self.useReranker)
        
        # Step 1: BM25 retrieval
        bm25_candidates = await self._retrieve_bm25(query, topK_bm25)
        
        # Step 2: Vector retrieval (if model service available)
        vector_candidates = []
        if self.model_service:
            vector_candidates = await self._retrieve_vector(
                query, topK_vector, project_id, filters
            )
        
        # Step 3: Merge and dedupe
        merged = self._merge_candidates(bm25_candidates, vector_candidates)
        
        # Step 4: Apply filters
        filtered = self._apply_filters(merged, project_id, filters)
        
        # Step 5: Optional reranking
        if useReranker and self.model_service and filtered:
            filtered = await self._rerank_candidates(query, filtered, opts.get('rerankerModelId'))
        
        # Step 6: Truncate to maxChunks
        final_chunks = filtered[:maxChunks]
        
        # Step 7: Check abstention
        should_abstain, abstention_reason = self._should_abstain(final_chunks)
        
        return RetrieveResult(
            chunks=final_chunks,
            totalCandidates=len(merged),
            abstained=should_abstain,
            abstentionReason=abstention_reason,
            metadata={
                'projectId': project_id,
                'query': query,
                'topK_bm25': topK_bm25,
                'topK_vector': topK_vector,
                'maxChunksForContext': maxChunks,
                'useReranker': useReranker,
                'bm25_results': len(bm25_candidates),
                'vector_results': len(vector_candidates),
                'after_merge': len(merged),
                'after_filter': len(filtered),
                'final_count': len(final_chunks)
            }
        )
    
    async def _retrieve_bm25(self, query: str, k: int) -> List[ChunkWithScore]:
        """Retrieve using BM25."""
        if not self.bm25_index:
            return []
        
        try:
            results = self.bm25_index.search(query, k=k)
            candidates = []
            for idx, score in results:
                if idx < len(self.chunks):
                    chunk_data = self.chunks[idx]
                    candidates.append(ChunkWithScore(
                        chunk=self._convert_to_chunk(chunk_data),
                        score=float(score),
                        source='bm25'
                    ))
            return candidates
        except Exception as e:
            logger.error(f"BM25 retrieval error: {e}")
            return []
    
    async def _retrieve_vector(
        self,
        query: str,
        k: int,
        project_id: str = 'default',
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ChunkWithScore]:
        """Retrieve using vector similarity."""
        if not self.model_service:
            logger.debug("Vector retrieval skipped - no model service")
            return []
        
        # Check if we have any vectors (pgvector or memory)
        has_vectors = (
            (self.use_pgvector and self.vector_store_db) or
            (not self.use_pgvector and self.vector_store_memory)
        )
        
        if not has_vectors:
            logger.debug("Vector retrieval skipped - no vector store")
            return []
        
        try:
            # Generate embedding for query
            embed_result = await self.model_service.embed({"texts": [query]})

            # ConcreteModelService.embed returns an object with a .vectors list
            vectors = embed_result.vectors
            if not vectors:
                logger.warning("Failed to generate query embedding")
                return []

            query_vector = vectors[0]
            
            # Route to pgvector or in-memory search
            if self.use_pgvector and self.vector_store_db:
                return await self._retrieve_vector_pgvector(query_vector, k, project_id, filters)
            else:
                return await self._retrieve_vector_memory(query_vector, k)
            
        except Exception as e:
            logger.error(f"Vector retrieval error: {e}")
            return []
    
    async def _retrieve_vector_pgvector(
        self,
        query_vector: List[float],
        k: int,
        project_id: str,
        filters: Optional[Dict[str, Any]]
    ) -> List[ChunkWithScore]:
        """Retrieve using pgvector database."""
        try:
            results = await self.vector_store_db.search_similar(
                query_embedding=query_vector,
                project_id=project_id,
                k=k,
                similarity_threshold=0.3,
                filters=filters
            )
            
            # Convert to ChunkWithScore format
            candidates = []
            for result in results:
                chunk = Chunk(
                    id=str(result['id']),
                    documentId='',
                    projectId=project_id,
                    text=result['text'],
                    position=result.get('position', 0),
                    startOffset=result.get('start_offset'),
                    endOffset=result.get('end_offset'),
                    tags=result.get('tags', []),
                    ttlExpiresAt=None,
                    indexVersion=1,
                    createdAt=result.get('created_at')
                )
                
                candidates.append(ChunkWithScore(
                    chunk=chunk,
                    score=float(result['similarity']),
                    source='vector'
                ))
            
            return candidates
        
        except Exception as e:
            logger.error(f"pgvector retrieval error: {e}")
            return []
    
    async def _retrieve_vector_memory(
        self,
        query_vector: List[float],
        k: int
    ) -> List[ChunkWithScore]:
        """Retrieve using in-memory vector storage."""
        try:
            # Compute cosine similarity with all stored vectors
            similarities = []
            for chunk_id, chunk_vector in self.vector_store_memory.items():
                similarity = self._cosine_similarity(query_vector, chunk_vector)
                similarities.append((chunk_id, similarity))
            
            # Sort by similarity and take top-k
            similarities.sort(key=lambda x: x[1], reverse=True)
            top_similarities = similarities[:k]
            
            # Build result list
            candidates = []
            chunk_id_map = {c.get('id'): c for c in self.chunks}
            
            for chunk_id, score in top_similarities:
                if chunk_id in chunk_id_map:
                    chunk_data = chunk_id_map[chunk_id]
                    candidates.append(ChunkWithScore(
                        chunk=self._convert_to_chunk(chunk_data),
                        score=float(score),
                        source='vector'
                    ))
            
            return candidates
        
        except Exception as e:
            logger.error(f"Memory vector retrieval error: {e}")
            return []
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def _merge_candidates(
        self,
        bm25_results: List[ChunkWithScore],
        vector_results: List[ChunkWithScore]
    ) -> List[ChunkWithScore]:
        """Merge and dedupe BM25 and vector results."""
        seen_ids = set()
        merged = []
        
        # Combine both lists
        all_candidates = bm25_results + vector_results
        
        # Dedupe by chunk ID, keeping highest score
        chunk_scores: Dict[str, ChunkWithScore] = {}
        for candidate in all_candidates:
            chunk_id = candidate['chunk'].get('id', '')
            if not chunk_id:
                continue
            
            if chunk_id not in chunk_scores or candidate['score'] > chunk_scores[chunk_id]['score']:
                chunk_scores[chunk_id] = candidate
        
        # Sort by score descending
        merged = sorted(chunk_scores.values(), key=lambda x: x['score'], reverse=True)
        return merged
    
    def _convert_to_chunk(self, chunk_data: Dict[str, Any]) -> Chunk:
        """Convert raw chunk data to Chunk TypedDict."""
        # Extract tags from metadata or create basic tags
        metadata = chunk_data.get('metadata', {})
        source = chunk_data.get('source', {})
        
        tags = []
        # Add source_type tag
        source_type = source.get('type', 'unknown')
        tags.append(f"source_type:{source_type}")
        
        # Add language tag
        language = metadata.get('language', 'en')
        tags.append(f"language:{language}")
        
        # Default confidentiality
        tags.append("confidentiality:public")
        
        return Chunk(
            id=chunk_data.get('id', ''),
            documentId='',  # Not in current schema
            projectId='default',  # Not in current schema
            text=chunk_data.get('content', ''),
            position=metadata.get('chunk_index', 0),
            startOffset=metadata.get('start_sec'),
            endOffset=metadata.get('end_sec'),
            tags=tags,
            ttlExpiresAt=None,
            indexVersion=1,
            createdAt=metadata.get('created_at')
        )
    
    def _apply_filters(
        self,
        candidates: List[ChunkWithScore],
        project_id: str,
        filters: Optional[RetrieveFilters]
    ) -> List[ChunkWithScore]:
        """Apply filters to candidates."""
        if not filters and not project_id:
            return candidates
        
        filtered = []
        for candidate in candidates:
            chunk = candidate['chunk']
            tags = chunk.get('tags', [])
            
            # Filter by project (if specified and not 'default')
            if project_id and project_id != 'default':
                if f"project:{project_id}" not in tags:
                    continue
            
            # Filter by source_type
            if filters and filters.get('source_type'):
                source_type_tag = f"source_type:{filters['source_type']}"
                if source_type_tag not in tags:
                    continue
            
            # Filter by confidentiality
            if filters and filters.get('confidentiality'):
                conf_tag = f"confidentiality:{filters['confidentiality']}"
                if conf_tag not in tags:
                    continue
            
            # Filter by agent_hint
            if filters and filters.get('agent_hint'):
                hint_tag = f"agent_hint:{filters['agent_hint']}"
                if hint_tag not in tags:
                    continue
            
            filtered.append(candidate)
        
        return filtered
    
    async def _rerank_candidates(
        self,
        query: str,
        candidates: List[ChunkWithScore],
        reranker_model_id: Optional[str]
    ) -> List[ChunkWithScore]:
        """Rerank candidates using ModelService."""
        if not self.model_service or not candidates:
            return candidates
        
        try:
            # Prepare items for reranking
            from model_service import RerankItem
            items = [
                RerankItem(
                    id=c['chunk'].get('id', ''),
                    text=c['chunk'].get('text', '')
                )
                for c in candidates
            ]
            
            # Call reranker
            reranked = await self.model_service.rerank({
                'query': query,
                'items': items,
                'modelId': reranker_model_id
            })
            
            # Map reranked scores back to candidates
            score_map = {item.id: item.score for item in reranked}
            
            # Update scores and resort
            for candidate in candidates:
                chunk_id = candidate['chunk'].get('id', '')
                if chunk_id in score_map:
                    candidate['score'] = score_map[chunk_id]
                    candidate['source'] = 'reranked'
            
            # Sort by new scores
            return sorted(candidates, key=lambda x: x['score'], reverse=True)
            
        except Exception as e:
            logger.error(f"Reranking error: {e}")
            return candidates  # Return original order on error
    
    def _should_abstain(
        self,
        chunks: List[ChunkWithScore],
        min_relevance_threshold: float = 0.3
    ) -> Tuple[bool, Optional[str]]:
        """
        Determine if retrieval should abstain due to low relevance.
        
        Args:
            chunks: Retrieved chunks with scores
            min_relevance_threshold: Minimum average score to not abstain
            
        Returns:
            Tuple of (should_abstain, reason)
        """
        if not chunks:
            return True, "No chunks retrieved"
        
        avg_score = sum(c['score'] for c in chunks) / len(chunks)
        if avg_score < min_relevance_threshold:
            return True, f"Average relevance score {avg_score:.3f} below threshold {min_relevance_threshold}"
        
        return False, None

