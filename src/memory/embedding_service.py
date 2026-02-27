"""
Embedding and content processing services for the MCP Memory Server.

This module handles text embedding generation and content hashing,
extracted from the monolithic memory_manager.py for better separation of concerns.
"""

import hashlib
import logging
import uuid
from typing import List
from sentence_transformers import SentenceTransformer
from ..config import Config

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for handling text embeddings and content processing."""

    def __init__(self):
        """Initialize the embedding service."""
        self.embedding_model = None

    async def initialize(self) -> None:
        """Initialize the embedding model."""
        try:
            # Initialize embedding model
            self.embedding_model = SentenceTransformer(Config.EMBEDDING_MODEL)
            logger.info(f"✅ Loaded embedding model: {Config.EMBEDDING_MODEL}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize embedding model: {e}")
            raise

    def _embed_text(self, text: str) -> List[float]:
        """Generate embeddings for text content."""
        if not self.embedding_model:
            raise ValueError("Embedding model not initialized")

        try:
            # Generate embeddings
            embedding = self.embedding_model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"❌ Failed to generate embedding: {e}")
            raise

    def _generate_content_hash(self, content: str) -> str:
        """Generate a deterministic UUID for content to use as Qdrant point ID.

        Qdrant only accepts UUID-format strings or unsigned 64-bit integers as
        point IDs.  We use uuid5 (SHA-1 based, deterministic) so the same
        content always maps to the same ID, preserving deduplication semantics.

        The namespace UUID matches GenericMemoryService._generate_content_hash
        so both code paths produce identical IDs for the same content.
        """
        try:
            namespace = uuid.UUID("12345678-1234-5678-1234-123456789abc")
            return str(uuid.uuid5(namespace, content))
        except Exception as e:
            logger.error(f"❌ Failed to generate content hash: {e}")
            raise

    def embed_text(self, text: str) -> List[float]:
        """Public interface for text embedding."""
        return self._embed_text(text)

    def generate_content_hash(self, content: str) -> str:
        """Public interface for content hashing."""
        return self._generate_content_hash(content)

    async def cleanup(self) -> None:
        """Cleanup embedding model resources."""
        try:
            if self.embedding_model:
                self.embedding_model = None
                logger.info("🧹 Cleaned up embedding model")
        except Exception as e:
            logger.error(f"⚠️ Error during embedding service cleanup: {e}")
