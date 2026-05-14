import hashlib
import logging
from typing import Any, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class SemanticCache:
    """
    Implements a semantic L2 cache using embeddings and vector similarity search.

    Uses Sentence Transformers to generate embeddings and Qdrant as the vector
    database for high-speed similarity lookups. This allows the gateway to
    return cached responses for prompts that are semantically identical but
    not string-equal.
    """

    def __init__(
        self,
        embedding_model: str = "all-MiniLM-L6-v2",
        similarity_threshold: float = 0.95,
        qdrant_url: str = "http://localhost:6333",
        collection_name: str = "llm_cache",
    ):
        self.embedding_model_name = embedding_model
        self.similarity_threshold = similarity_threshold
        self.collection_name = collection_name
        self.qdrant_url = qdrant_url
        self._model: Optional[SentenceTransformer] = None
        self._client: Optional[QdrantClient] = None
        self._initialized = False

    def _lazy_init(self) -> None:
        """
        Lazily initialize the embedding model and vector DB client.

        This prevents heavy model loading during class instantiation.
        """
        if self._initialized:
            return

        try:
            # Initialize embedding model
            self._model = SentenceTransformer(self.embedding_model_name)
            logger.info(f"Loaded semantic embedding model: {self.embedding_model_name}")

            # Initialize Qdrant client
            self._client = QdrantClient(url=self.qdrant_url)
            self._ensure_collection()
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize semantic cache backend: {e}")
            self._model = None
            self._client = None

    def _ensure_collection(self) -> None:
        """
        Create the required Qdrant collection if it doesn't already exist.
        """
        if not self._client:
            return
        try:
            collections = self._client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            if not exists:
                self._client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
                )
                logger.info(f"Created new Qdrant collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to verify/create Qdrant collection: {e}")

    def _get_embedding(self, text: str) -> List[float]:
        """Generate a numerical embedding vector for the given text."""
        if not self._model:
            return []
        return self._model.encode(text).tolist()

    def _get_cache_key(self, prompt: str, tenant_id: str) -> str:
        """Generate a deterministic point ID for Qdrant storage."""
        content = f"{tenant_id}:{prompt}"
        return hashlib.sha256(content.encode()).hexdigest()

    async def get(self, prompt: str, tenant_id: str) -> Optional[Any]:
        """
        Perform a semantic search to find a similar cached response.

        Args:
            prompt: The user's input text.
            tenant_id: The ID of the requesting tenant.

        Returns:
            The cached response if similarity exceeds threshold, else None.
        """
        self._lazy_init()
        if not self._client or not self._model:
            return None

        try:
            embedding = self._get_embedding(prompt)
            if not embedding:
                return None

            # Search for similar vectors with tenant isolation filter
            search_result = self._client.search(
                collection_name=self.collection_name,
                query_vector=embedding,
                query_filter=Filter(
                    must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))]
                ),
                limit=1,
            )

            if search_result and search_result[0].score >= self.similarity_threshold:
                point_id = search_result[0].id
                points = self._client.retrieve(
                    collection_name=self.collection_name, ids=[point_id], with_payload=True
                )
                if points:
                    return points[0].payload.get("response")
            return None
        except Exception as e:
            logger.error(f"Error during semantic cache retrieval: {e}")
            return None

    async def set(
        self, prompt: str, tenant_id: str, response: Any, ttl: Optional[int] = None
    ) -> None:
        """
        Store a prompt-response pair in the semantic cache.

        Args:
            prompt: The user's input text.
            tenant_id: The ID of the requesting tenant.
            response: The result to cache.
            ttl: Time-to-live (not fully supported by Qdrant, used for metadata).
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
                    "prompt": prompt[:500],
                    "response": response,
                    "created_at": time.time(),
                },
            )

            self._client.upsert(collection_name=self.collection_name, points=[point])
            logger.debug(f"Successfully stored entry in semantic cache (ID: {cache_key[:8]})")
        except Exception as e:
            logger.error(f"Error storing entry in semantic cache: {e}")

    async def invalidate_tenant(self, tenant_id: str) -> bool:
        """
        Delete all cached entries belonging to a specific tenant.

        Returns:
            True if the operation completed successfully.
        """
        self._lazy_init()
        if not self._client:
            return False
        try:
            self._client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))]
                ),
            )
            return True
        except Exception as e:
            logger.error(f"Error invalidating tenant cache: {e}")
            return False
