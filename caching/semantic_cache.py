import os
import logging
import asyncio
import hashlib
from typing import Optional, Any, List, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

logger = logging.getLogger(__name__)

class SemanticCache:
    """
    Semantic cache using embeddings and vector similarity search.
    Uses Qdrant as vector database.
    """

    def __init__(
        self,
        embedding_model: str = "all-MiniLM-L6-v2",
        similarity_threshold: float = 0.95,
        qdrant_url: str = "http://localhost:6333",
        collection_name: str = "llm_cache"
    ):
        self.similarity_threshold = similarity_threshold
        self.collection_name = collection_name
        self.qdrant_url = qdrant_url
        self._model: Optional[SentenceTransformer] = None
        self._client: Optional[QdrantClient] = None
        self._initialized = False

    def _lazy_init(self):
        """Lazy initialization of model and client."""
        if self._initialized:
            return

        try:
            # Initialize embedding model
            self._model = SentenceTransformer(embedding_model)
            logger.info(f"Loaded embedding model: {embedding_model}")

            # Initialize Qdrant client
            self._client = QdrantClient(url=self.qdrant_url)
            self._ensure_collection()
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize semantic cache: {e}")
            self._model = None
            self._client = None

    def _ensure_collection(self):
        """Create collection if not exists."""
        if not self._client:
            return
        try:
            collections = self._client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            if not exists:
                self._client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to ensure collection: {e}")

    def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text."""
        if not self._model:
            return []
        return self._model.encode(text).tolist()

    def _get_cache_key(self, prompt: str, tenant_id: str) -> str:
        """Generate deterministic cache key."""
        content = f"{tenant_id}:{prompt}"
        return hashlib.sha256(content.encode()).hexdigest()

    async def get(self, prompt: str, tenant_id: str) -> Optional[Any]:
        """
        Find semantically similar cached response.
        Returns cached value if similarity > threshold.
        """
        self._lazy_init()
        if not self._client or not self._model:
            return None

        try:
            embedding = self._get_embedding(prompt)
            if not embedding:
                return None

            # Search for similar vectors with tenant filter
            search_result = self._client.search(
                collection_name=self.collection_name,
                query_vector=embedding,
                query_filter=Filter(
                    must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))]
                ),
                limit=1
            )

            if search_result and search_result[0].score >= self.similarity_threshold:
                point_id = search_result[0].id
                # Retrieve full payload
                points = self._client.retrieve(
                    collection_name=self.collection_name,
                    ids=[point_id],
                    with_payload=True
                )
                if points:
                    return points[0].payload.get("response")
            return None
        except Exception as e:
            logger.error(f"Semantic cache get error: {e}")
            return None

    async def set(self, prompt: str, tenant_id: str, response: Any, ttl: Optional[int] = None):
        """
        Store prompt-response pair with embedding.
        """
        self._lazy_init()
        if not self._client or not self._model:
            return

        try:
            embedding = self._get_embedding(prompt)
            if not embedding:
                return

            cache_key = self._get_cache_key(prompt, tenant_id)
            point = PointStruct(
                id=cache_key,
                vector=embedding,
                payload={
                    "tenant_id": tenant_id,
                    "prompt": prompt[:500],  # Truncate for storage
                    "response": response,
                    "created_at": asyncio.get_event_loop().time()
                }
            )

            self._client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            logger.debug(f"Stored in semantic cache: {cache_key[:8]}...")
        except Exception as e:
            logger.error(f"Semantic cache set error: {e}")

    async def invalidate_tenant(self, tenant_id: str) -> int:
        """Delete all cache entries for a tenant."""
        self._lazy_init()
        if not self._client:
            return 0
        try:
            result = self._client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))]
                )
            )
            return result.status == "completed"
        except Exception as e:
            logger.error(f"Semantic cache invalidation error: {e}")
            return 0
