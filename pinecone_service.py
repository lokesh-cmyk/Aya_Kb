"""
Pinecone Vector Database Service
================================

Vector storage and retrieval using Pinecone.
Supports dense vectors for semantic search.
"""

import logging
from typing import Any, Dict, List, Optional

from pinecone import Pinecone, ServerlessSpec

from app.core.config import settings
from app.schemas.api_schemas import SearchResult

logger = logging.getLogger(__name__)


class PineconeService:
    """
    Pinecone vector database service.
    
    Provides vector storage, retrieval, and semantic search
    capabilities for the knowledge base.
    """
    
    def __init__(self):
        """Initialize the Pinecone service."""
        self._client: Optional[Pinecone] = None
        self._index = None
        self._index_name = settings.PINECONE_INDEX_NAME
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize Pinecone client and ensure index exists."""
        if self._initialized:
            return
        
        if not settings.PINECONE_API_KEY:
            logger.warning("PINECONE_API_KEY not set, Pinecone service disabled")
            return
        
        logger.info("Initializing Pinecone client...")
        
        try:
            # Initialize client
            self._client = Pinecone(api_key=settings.PINECONE_API_KEY)
            
            # Check if index exists, create if not
            existing_indexes = [idx.name for idx in self._client.list_indexes()]
            
            if self._index_name not in existing_indexes:
                logger.info(f"Creating Pinecone index: {self._index_name}")
                self._client.create_index(
                    name=self._index_name,
                    dimension=settings.EMBEDDING_DIMENSION,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region=settings.PINECONE_ENVIRONMENT,
                    ),
                )
                logger.info(f"Index {self._index_name} created successfully")
            
            # Get index reference
            self._index = self._client.Index(self._index_name)
            
            # Verify connection
            stats = self._index.describe_index_stats()
            logger.info(
                f"Pinecone connected. Index stats: "
                f"{stats.total_vector_count} vectors"
            )
            
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {e}")
            raise
    
    async def close(self) -> None:
        """Close Pinecone connection."""
        self._index = None
        self._client = None
        self._initialized = False
        logger.info("Pinecone connection closed")
    
    def _get_index(self):
        """Get the Pinecone index, ensuring it's initialized."""
        if self._index is None:
            if not settings.PINECONE_API_KEY:
                raise ValueError("Pinecone API key not configured")
            
            self._client = Pinecone(api_key=settings.PINECONE_API_KEY)
            self._index = self._client.Index(self._index_name)
        
        return self._index
    
    async def upsert_vectors(
        self,
        vectors: List[Dict[str, Any]],
        namespace: str = None,
    ) -> int:
        """
        Upsert vectors into Pinecone.
        
        Args:
            vectors: List of vectors with format:
                {
                    "id": str,
                    "values": List[float],
                    "metadata": Dict[str, Any]
                }
            namespace: Pinecone namespace (uses default if not specified)
            
        Returns:
            Number of vectors upserted
        """
        if not vectors:
            return 0
        
        namespace = namespace or settings.PINECONE_NAMESPACE
        index = self._get_index()
        
        # Prepare vectors for upsert
        upsert_data = []
        for vec in vectors:
            upsert_data.append({
                "id": vec["id"],
                "values": vec["values"],
                "metadata": vec.get("metadata", {}),
            })
        
        # Upsert in batches of 100
        batch_size = 100
        total_upserted = 0
        
        for i in range(0, len(upsert_data), batch_size):
            batch = upsert_data[i:i + batch_size]
            response = index.upsert(
                vectors=batch,
                namespace=namespace,
            )
            total_upserted += response.upserted_count
        
        logger.info(f"Upserted {total_upserted} vectors to namespace '{namespace}'")
        return total_upserted
    
    async def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        namespace: str = None,
        filter: Dict[str, Any] = None,
        include_metadata: bool = True,
    ) -> List[SearchResult]:
        """
        Search for similar vectors.
        
        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            namespace: Pinecone namespace
            filter: Metadata filter
            include_metadata: Include metadata in results
            
        Returns:
            List of SearchResult objects
        """
        namespace = namespace or settings.PINECONE_NAMESPACE
        index = self._get_index()
        
        # Execute search
        response = index.query(
            vector=query_vector,
            top_k=top_k,
            namespace=namespace,
            filter=filter,
            include_metadata=include_metadata,
        )
        
        # Convert to SearchResult objects
        results = []
        for match in response.matches:
            metadata = match.metadata or {}
            
            result = SearchResult(
                document_id=metadata.get("document_id", ""),
                chunk_id=match.id,
                content=metadata.get("content", ""),
                score=match.score,
                metadata=metadata,
                page_number=metadata.get("page_number"),
                section_title=metadata.get("section_title"),
            )
            results.append(result)
        
        return results
    
    async def delete_vectors(
        self,
        ids: List[str] = None,
        filter: Dict[str, Any] = None,
        namespace: str = None,
        delete_all: bool = False,
    ) -> bool:
        """
        Delete vectors from Pinecone.
        
        Args:
            ids: List of vector IDs to delete
            filter: Metadata filter for deletion
            namespace: Pinecone namespace
            delete_all: Delete all vectors in namespace
            
        Returns:
            True if deletion successful
        """
        namespace = namespace or settings.PINECONE_NAMESPACE
        index = self._get_index()
        
        try:
            if delete_all:
                index.delete(delete_all=True, namespace=namespace)
                logger.info(f"Deleted all vectors in namespace '{namespace}'")
            elif ids:
                index.delete(ids=ids, namespace=namespace)
                logger.info(f"Deleted {len(ids)} vectors from namespace '{namespace}'")
            elif filter:
                index.delete(filter=filter, namespace=namespace)
                logger.info(f"Deleted vectors matching filter in namespace '{namespace}'")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete vectors: {e}")
            return False
    
    async def delete_by_document(
        self,
        document_id: str,
        namespace: str = None,
    ) -> bool:
        """
        Delete all vectors associated with a document.
        
        Args:
            document_id: Document ID
            namespace: Pinecone namespace
            
        Returns:
            True if deletion successful
        """
        return await self.delete_vectors(
            filter={"document_id": {"$eq": document_id}},
            namespace=namespace,
        )
    
    async def get_index_stats(
        self,
        namespace: str = None,
    ) -> Dict[str, Any]:
        """
        Get index statistics.
        
        Args:
            namespace: Pinecone namespace (None for all)
            
        Returns:
            Index statistics dictionary
        """
        index = self._get_index()
        stats = index.describe_index_stats()
        
        result = {
            "dimension": stats.dimension,
            "index_fullness": stats.index_fullness,
            "total_vector_count": stats.total_vector_count,
            "namespaces": {},
        }
        
        if stats.namespaces:
            for ns_name, ns_stats in stats.namespaces.items():
                result["namespaces"][ns_name] = {
                    "vector_count": ns_stats.vector_count,
                }
        
        return result
    
    async def fetch_vectors(
        self,
        ids: List[str],
        namespace: str = None,
    ) -> Dict[str, Any]:
        """
        Fetch vectors by ID.
        
        Args:
            ids: List of vector IDs
            namespace: Pinecone namespace
            
        Returns:
            Dictionary of vector data
        """
        namespace = namespace or settings.PINECONE_NAMESPACE
        index = self._get_index()
        
        response = index.fetch(ids=ids, namespace=namespace)
        
        return {
            vid: {
                "id": vec.id,
                "values": vec.values,
                "metadata": vec.metadata,
            }
            for vid, vec in response.vectors.items()
        }


# Global instance
pinecone_service = PineconeService()