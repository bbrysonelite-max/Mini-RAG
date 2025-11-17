"""
Vector store implementation using pgvector.

Handles:
- Storing embeddings in PostgreSQL
- Vector similarity search
- Batch operations for efficiency
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from database import Database, get_database

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Vector storage and retrieval using pgvector.
    
    Provides efficient storage and similarity search for chunk embeddings.
    """
    
    def __init__(self, db: Optional[Database] = None):
        """
        Initialize vector store.
        
        Args:
            db: Database instance (uses global if not provided)
        """
        self.db = db or get_database()
    
    async def insert_embedding(
        self,
        chunk_id: str,
        embedding: List[float],
        model_id: str
    ) -> bool:
        """
        Insert a single embedding.
        
        Args:
            chunk_id: UUID of the chunk
            embedding: Embedding vector
            model_id: Model used to generate embedding
            
        Returns:
            True if successful
        """
        try:
            query = """
                INSERT INTO chunk_embeddings (chunk_id, embedding, model_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (chunk_id) DO UPDATE
                SET embedding = EXCLUDED.embedding,
                    model_id = EXCLUDED.model_id,
                    created_at = NOW()
            """
            
            await self.db.execute(query, (chunk_id, embedding, model_id))
            return True
        
        except Exception as e:
            logger.error(f"Failed to insert embedding for chunk {chunk_id}: {e}")
            return False
    
    async def insert_embeddings_batch(
        self,
        embeddings: List[Tuple[str, List[float], str]]
    ) -> Dict[str, Any]:
        """
        Insert multiple embeddings in batch.
        
        Args:
            embeddings: List of (chunk_id, embedding, model_id) tuples
            
        Returns:
            Dictionary with insertion stats
        """
        if not embeddings:
            return {'inserted': 0, 'errors': 0}
        
        try:
            query = """
                INSERT INTO chunk_embeddings (chunk_id, embedding, model_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (chunk_id) DO UPDATE
                SET embedding = EXCLUDED.embedding,
                    model_id = EXCLUDED.model_id,
                    created_at = NOW()
            """
            
            await self.db.execute_many(query, embeddings)
            
            logger.info(f"Batch inserted {len(embeddings)} embeddings")
            
            return {
                'inserted': len(embeddings),
                'errors': 0
            }
        
        except Exception as e:
            logger.error(f"Failed to batch insert embeddings: {e}")
            return {
                'inserted': 0,
                'errors': len(embeddings),
                'error_message': str(e)
            }
    
    async def search_similar(
        self,
        query_embedding: List[float],
        project_id: str,
        k: int = 40,
        similarity_threshold: float = 0.3,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks using vector similarity.
        
        Args:
            query_embedding: Query embedding vector
            project_id: Project ID to filter by
            k: Number of results to return
            similarity_threshold: Minimum similarity score (0-1)
            filters: Optional filters (source_type, confidentiality, etc.)
            
        Returns:
            List of chunks with similarity scores
        """
        try:
            # Build query with optional filters
            query = """
                SELECT 
                    c.id,
                    c.text,
                    c.tags,
                    c.position,
                    c.start_offset,
                    c.end_offset,
                    c.created_at,
                    1 - (ce.embedding <=> %s::vector) AS similarity
                FROM chunk_embeddings ce
                JOIN chunks c ON ce.chunk_id = c.id
                WHERE c.project_id = %s
                    AND 1 - (ce.embedding <=> %s::vector) >= %s
            """
            
            params = [query_embedding, project_id, query_embedding, similarity_threshold]
            
            # Add tag filters if provided
            if filters:
                if filters.get('source_type'):
                    query += " AND %s = ANY(c.tags)"
                    params.append(f"source_type:{filters['source_type']}")
                
                if filters.get('confidentiality'):
                    query += " AND %s = ANY(c.tags)"
                    params.append(f"confidentiality:{filters['confidentiality']}")
                
                if filters.get('agent_hint'):
                    query += " AND %s = ANY(c.tags)"
                    params.append(f"agent_hint:{filters['agent_hint']}")
            
            query += """
                ORDER BY ce.embedding <=> %s::vector
                LIMIT %s
            """
            params.extend([query_embedding, k])
            
            results = await self.db.fetch_all(query, tuple(params))
            
            return results
        
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    async def get_embedding(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """
        Get embedding for a specific chunk.
        
        Args:
            chunk_id: Chunk UUID
            
        Returns:
            Dictionary with embedding and metadata, or None
        """
        try:
            query = """
                SELECT chunk_id, embedding, model_id, created_at
                FROM chunk_embeddings
                WHERE chunk_id = %s
            """
            
            result = await self.db.fetch_one(query, (chunk_id,))
            return result
        
        except Exception as e:
            logger.error(f"Failed to get embedding for chunk {chunk_id}: {e}")
            return None
    
    async def delete_embedding(self, chunk_id: str) -> bool:
        """
        Delete embedding for a chunk.
        
        Args:
            chunk_id: Chunk UUID
            
        Returns:
            True if successful
        """
        try:
            query = "DELETE FROM chunk_embeddings WHERE chunk_id = %s"
            await self.db.execute(query, (chunk_id,))
            return True
        
        except Exception as e:
            logger.error(f"Failed to delete embedding for chunk {chunk_id}: {e}")
            return False
    
    async def delete_embeddings_by_project(self, project_id: str) -> int:
        """
        Delete all embeddings for a project.
        
        Args:
            project_id: Project UUID
            
        Returns:
            Number of embeddings deleted
        """
        try:
            query = """
                DELETE FROM chunk_embeddings
                WHERE chunk_id IN (
                    SELECT id FROM chunks WHERE project_id = %s
                )
            """
            
            result = await self.db.execute(query, (project_id,))
            logger.info(f"Deleted embeddings for project {project_id}")
            return 0  # psycopg3 doesn't return rowcount in async mode easily
        
        except Exception as e:
            logger.error(f"Failed to delete embeddings for project {project_id}: {e}")
            return 0
    
    async def count_embeddings(self, project_id: Optional[str] = None) -> int:
        """
        Count embeddings in the store.
        
        Args:
            project_id: Optional project ID to filter by
            
        Returns:
            Number of embeddings
        """
        try:
            if project_id:
                query = """
                    SELECT COUNT(*) as count
                    FROM chunk_embeddings ce
                    JOIN chunks c ON ce.chunk_id = c.id
                    WHERE c.project_id = %s
                """
                result = await self.db.fetch_one(query, (project_id,))
            else:
                query = "SELECT COUNT(*) as count FROM chunk_embeddings"
                result = await self.db.fetch_one(query)
            
            return result['count'] if result else 0
        
        except Exception as e:
            logger.error(f"Failed to count embeddings: {e}")
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector store.
        
        Returns:
            Dictionary with stats
        """
        try:
            stats_query = """
                SELECT 
                    COUNT(*) as total_embeddings,
                    COUNT(DISTINCT model_id) as unique_models,
                    MIN(created_at) as oldest_embedding,
                    MAX(created_at) as newest_embedding
                FROM chunk_embeddings
            """
            
            stats = await self.db.fetch_one(stats_query)
            
            # Get per-project counts
            project_query = """
                SELECT 
                    c.project_id,
                    COUNT(*) as count
                FROM chunk_embeddings ce
                JOIN chunks c ON ce.chunk_id = c.id
                GROUP BY c.project_id
                ORDER BY count DESC
                LIMIT 10
            """
            
            projects = await self.db.fetch_all(project_query)
            
            return {
                'total_embeddings': stats['total_embeddings'] if stats else 0,
                'unique_models': stats['unique_models'] if stats else 0,
                'oldest_embedding': stats['oldest_embedding'] if stats else None,
                'newest_embedding': stats['newest_embedding'] if stats else None,
                'top_projects': projects
            }
        
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                'total_embeddings': 0,
                'error': str(e)
            }
    
    async def rebuild_index(self) -> bool:
        """
        Rebuild the HNSW index for vector search.
        
        This can improve search performance after bulk insertions.
        
        Returns:
            True if successful
        """
        try:
            # Drop and recreate index
            query = """
                DROP INDEX IF EXISTS idx_chunk_embeddings_vector;
                CREATE INDEX idx_chunk_embeddings_vector 
                    ON chunk_embeddings USING hnsw (embedding vector_cosine_ops);
            """
            
            logger.info("Rebuilding vector index...")
            await self.db.execute(query)
            logger.info("Vector index rebuilt successfully")
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to rebuild index: {e}")
            return False

