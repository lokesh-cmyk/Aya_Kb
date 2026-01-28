"""
Embedding Service
=================

Text embedding generation using sentence-transformers.
Supports caching and batch processing for efficiency.
"""

import hashlib
import logging
from typing import Any, Dict, List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Text embedding service using sentence-transformers.
    
    Provides efficient embedding generation with optional caching
    and batch processing support.
    """
    
    def __init__(self):
        """Initialize the embedding service."""
        self._model: Optional[SentenceTransformer] = None
        self._model_name = settings.EMBEDDING_MODEL
        self._cache: Dict[str, List[float]] = {}
        self._cache_enabled = settings.EMBEDDING_CACHE_ENABLED
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the embedding model."""
        if self._initialized:
            return
        
        logger.info(f"Loading embedding model: {self._model_name}")
        
        try:
            self._model = SentenceTransformer(self._model_name)
            
            # Warm up the model with a test embedding
            _ = self._model.encode("test", convert_to_numpy=True)
            
            self._initialized = True
            logger.info(
                f"Embedding model loaded successfully. "
                f"Dimension: {self._model.get_sentence_embedding_dimension()}"
            )
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def _get_model(self) -> SentenceTransformer:
        """Get the embedding model, loading if necessary."""
        if self._model is None:
            self._model = SentenceTransformer(self._model_name)
        return self._model
    
    def _get_cache_key(self, text: str) -> str:
        """Generate a cache key for the given text."""
        return hashlib.md5(text.encode()).hexdigest()
    
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        # Check cache first
        if self._cache_enabled:
            cache_key = self._get_cache_key(text)
            if cache_key in self._cache:
                return self._cache[cache_key]
        
        model = self._get_model()
        
        # Generate embedding
        embedding = model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        
        embedding_list = embedding.tolist()
        
        # Store in cache
        if self._cache_enabled:
            self._cache[cache_key] = embedding_list
            # Simple cache size management
            if len(self._cache) > 10000:
                # Remove oldest entries (simple FIFO)
                keys_to_remove = list(self._cache.keys())[:5000]
                for key in keys_to_remove:
                    del self._cache[key]
        
        return embedding_list
    
    async def embed_texts(
        self,
        texts: List[str],
        batch_size: int = 32,
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        model = self._get_model()
        
        # Check cache for existing embeddings
        embeddings = []
        texts_to_embed = []
        text_indices = []
        
        for i, text in enumerate(texts):
            if self._cache_enabled:
                cache_key = self._get_cache_key(text)
                if cache_key in self._cache:
                    embeddings.append((i, self._cache[cache_key]))
                    continue
            texts_to_embed.append(text)
            text_indices.append(i)
        
        # Generate embeddings for uncached texts
        if texts_to_embed:
            logger.info(f"Generating embeddings for {len(texts_to_embed)} texts")
            
            new_embeddings = model.encode(
                texts_to_embed,
                batch_size=batch_size,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=len(texts_to_embed) > 100,
            )
            
            # Store in cache and result
            for idx, embedding in zip(text_indices, new_embeddings):
                embedding_list = embedding.tolist()
                embeddings.append((idx, embedding_list))
                
                if self._cache_enabled:
                    cache_key = self._get_cache_key(texts[idx])
                    self._cache[cache_key] = embedding_list
        
        # Sort by original index and return
        embeddings.sort(key=lambda x: x[0])
        return [emb for _, emb in embeddings]
    
    async def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a search query.
        
        This is a convenience method that wraps embed_text.
        Some models may benefit from query-specific processing.
        
        Args:
            query: Search query text
            
        Returns:
            Query embedding vector
        """
        return await self.embed_text(query)
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embedding vectors."""
        model = self._get_model()
        return model.get_sentence_embedding_dimension()
    
    async def compute_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float],
    ) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score (0 to 1)
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # Cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def clear_cache(self) -> int:
        """Clear the embedding cache. Returns number of entries cleared."""
        count = len(self._cache)
        self._cache.clear()
        return count


# Global instance
embedding_service = EmbeddingService()