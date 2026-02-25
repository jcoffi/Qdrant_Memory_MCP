"""
Generic Memory Service - Replaces rigid memory types with flexible collections

Provides a modern, flexible memory API that works with any user-defined
collections instead of being locked to global/learned/agent types.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from .collection_manager import CollectionManager, CollectionPermissions

logger = logging.getLogger(__name__)


class GenericMemoryService:
    """
    Generic memory service supporting flexible, user-defined collections.

    Replaces the rigid global/learned/agent memory types with dynamic
    collections that users can create and organize as needed.

    Provides backward compatibility methods for legacy MCP server integration.
    """

    def __init__(self):
        """Initialize generic memory service."""
        self.client: Optional[QdrantClient] = None
        self.collection_manager: Optional[CollectionManager] = None
        self.embedding_model = None

        # Legacy collection mappings for backward compatibility
        self.legacy_collections = {
            "global": "global_memory",  # Maps to actual legacy collection
            "learned": "learned_memory",  # Maps to actual legacy collection
            "agent": "agent_memory",  # Maps to agent collections
        }
        self.initialized = False
        self.current_user = "system"  # Current user context

    async def initialize(self) -> Dict[str, Any]:
        """Initialize the memory service and collection manager."""
        try:
            # Initialize Qdrant client (use existing memory manager)
            from .memory_manager import QdrantMemoryManager
            from .config import Config

            qdrant_manager = QdrantMemoryManager()

            self.client = qdrant_manager.client

            # Initialize collection manager
            config = Config()
            self.collection_manager = CollectionManager(
                qdrant_client=self.client,
                embedding_dimension=config.EMBEDDING_DIMENSION,
            )

            # Initialize embedding model
            from sentence_transformers import SentenceTransformer

            self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

            self.initialized = True

            logger.info("✅ Generic memory service initialized successfully")
            return {"success": True, "message": "Memory service initialized"}

        except Exception as e:
            logger.error(f"❌ Failed to initialize memory service: {e}")
            return {"success": False, "error": str(e)}

    def set_user_context(self, user_id: str) -> None:
        """Set the current user context for operations."""
        self.current_user = user_id

    # Collection Management API

    async def create_collection(
        self,
        name: str,
        description: str = "",
        tags: List[str] = None,
        category: str = None,
        project: str = None,
        permissions: Dict[str, List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new memory collection.

        Args:
            name: Collection name (e.g., "project-alpha", "meeting-notes")
            description: Human-readable description
            tags: List of tags for organization
            category: Collection category (optional)
            project: Associated project (optional)
            permissions: Dict with "read", "write", "admin" keys (optional)

        Returns:
            Success/error response
        """
        if not self._ensure_initialized():
            return {"success": False, "error": "Service not initialized"}

        # Convert permissions dict to CollectionPermissions object
        perm_obj = None
        if permissions:
            perm_obj = CollectionPermissions(
                read=permissions.get("read", ["*"]),
                write=permissions.get("write", [self.current_user]),
                admin=permissions.get("admin", [self.current_user]),
            )

        return self.collection_manager.create_collection(
            name=name,
            description=description,
            tags=tags or [],
            category=category,
            project=project,
            permissions=perm_obj,
            created_by=self.current_user,
        )

    async def list_collections(
        self,
        filter_by_tags: List[str] = None,
        filter_by_category: str = None,
        filter_by_project: str = None,
        include_stats: bool = True,
    ) -> Dict[str, Any]:
        """List collections with optional filtering."""
        if not self._ensure_initialized():
            return {"success": False, "error": "Service not initialized"}

        if hasattr(self.collection_manager, "list_collections"):
            return self.collection_manager.list_collections(
                filter_by_tags=filter_by_tags,
                filter_by_category=filter_by_category,
                filter_by_project=filter_by_project,
                owned_by=None,  # Show all accessible collections
            )

        try:
            collections = []
            for collection in self.client.get_collections().collections:
                stats: Dict[str, Any] = {}
                if include_stats:
                    try:
                        info = self.client.get_collection(collection.name)
                        stats = {
                            "document_count": info.points_count or 0,
                            "vectors_count": info.vectors_count or 0,
                        }
                    except Exception:
                        stats = {"document_count": 0, "vectors_count": 0}

                collections.append(
                    {
                        "name": collection.name,
                        "description": "",
                        "tags": [],
                        "metadata": {},
                        "stats": stats,
                    }
                )

            return {
                "success": True,
                "collections": collections,
                "total_count": len(collections),
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to list collections: {e}"}

    async def get_collection(self, name: str) -> Dict[str, Any]:
        """Get detailed information about a collection."""
        if not self._ensure_initialized():
            return {"success": False, "error": "Service not initialized"}

        return self.collection_manager.get_collection(name)

    async def update_collection(
        self,
        name: str,
        description: str = None,
        tags: List[str] = None,
        category: str = None,
        project: str = None,
    ) -> Dict[str, Any]:
        """Update collection metadata."""
        if not self._ensure_initialized():
            return {"success": False, "error": "Service not initialized"}

        return self.collection_manager.update_collection(
            name=name,
            description=description,
            tags=tags,
            category=category,
            project=project,
            updated_by=self.current_user,
        )

    async def delete_collection(
        self, name: str, confirm: bool = False
    ) -> Dict[str, Any]:
        """Delete a collection."""
        if not self._ensure_initialized():
            return {"success": False, "error": "Service not initialized"}

        return self.collection_manager.delete_collection(
            name=name, deleted_by=self.current_user, confirm=confirm
        )

    # Memory Content API

    async def add_memory(
        self,
        collection: str,
        content: str,
        metadata: Dict[str, Any] = None,
        tags: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Add content to a specific collection.

        Args:
            collection: Collection name to add to
            content: Content to store
            metadata: Additional metadata (optional)
            tags: Content-specific tags (optional)

        Returns:
            Success/error response with memory ID
        """
        if not self._ensure_initialized():
            return {"success": False, "error": "Service not initialized"}

        try:
            # Check if collection exists and user has write permission
            collection_info = self.collection_manager.get_collection(collection)
            if not collection_info.get("success"):
                return {
                    "success": False,
                    "error": f"Collection '{collection}' not found",
                }

            # TODO: Add permission check here

            # Generate embedding
            embedding = self._embed_text(content)

            # Prepare metadata
            full_metadata = {
                "content": content,
                "collection": collection,
                "added_by": self.current_user,
                "timestamp": datetime.now().isoformat(),
                "tags": tags or [],
                **(metadata or {}),
            }

            # Generate unique ID
            content_hash = self._generate_content_hash(content)

            # Create point
            point = PointStruct(
                id=content_hash, vector=embedding, payload=full_metadata
            )

            # Store in Qdrant
            self.client.upsert(collection_name=collection, points=[point])

            logger.info(f"✅ Added memory to collection '{collection}'")
            return {
                "success": True,
                "memory_id": content_hash,
                "collection": collection,
                "message": "Memory added successfully",
            }

        except Exception as e:
            logger.error(f"❌ Failed to add memory: {e}")
            return {"success": False, "error": str(e)}

    async def search_memory(
        self,
        query: str,
        collections: List[str] = None,
        limit: int = 10,
        min_score: float = 0.3,
        filters: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Search for memories across one or more collections.

        Args:
            query: Search query text
            collections: List of collection names to search (all if None)
            limit: Maximum number of results
            min_score: Minimum similarity score
            filters: Additional filters for metadata

        Returns:
            Search results with scores and metadata
        """
        if not self._ensure_initialized():
            return {"success": False, "error": "Service not initialized"}

        try:
            # If no collections specified, search all accessible collections
            if collections is None:
                all_collections = await self.list_collections()
                if all_collections.get("success"):
                    collections = [
                        col["name"] for col in all_collections["collections"]
                    ]
                else:
                    collections = []

            # Generate query embedding
            query_embedding = self._embed_text(query)

            all_results = []

            # Search each collection
            for collection_name in collections:
                try:
                    # Check if collection exists
                    collection_info = self.collection_manager.get_collection(
                        collection_name
                    )
                    if not collection_info.get("success"):
                        continue

                    # TODO: Add permission check here

                    # Perform search
                    search_results = self.client.search(
                        collection_name=collection_name,
                        query_vector=query_embedding,
                        limit=limit,
                        score_threshold=min_score,
                    )

                    # Process results
                    for result in search_results:
                        all_results.append(
                            {
                                "id": result.id,
                                "score": result.score,
                                "collection": collection_name,
                                "payload": result.payload,
                            }
                        )

                except Exception as e:
                    logger.warning(
                        f"Failed to search collection {collection_name}: {e}"
                    )
                    continue

            # Sort by score and limit
            all_results.sort(key=lambda x: x["score"], reverse=True)
            all_results = all_results[:limit]

            return {
                "success": True,
                "results": all_results,
                "query": query,
                "collections_searched": collections,
                "total_results": len(all_results),
            }

        except Exception as e:
            logger.error(f"❌ Failed to search memory: {e}")
            return {"success": False, "error": str(e)}

    async def get_memory(self, memory_id: str, collection: str) -> Dict[str, Any]:
        """Get a specific memory by ID."""
        if not self._ensure_initialized():
            return {"success": False, "error": "Service not initialized"}

        try:
            result = self.client.retrieve(collection_name=collection, ids=[memory_id])

            if result:
                memory = result[0]
                return {
                    "success": True,
                    "memory": {
                        "id": memory.id,
                        "collection": collection,
                        "payload": memory.payload,
                    },
                }
            else:
                return {"success": False, "error": "Memory not found"}

        except Exception as e:
            logger.error(f"❌ Failed to get memory: {e}")
            return {"success": False, "error": str(e)}

    async def delete_memory(self, memory_id: str, collection: str) -> Dict[str, Any]:
        """Delete a specific memory."""
        if not self._ensure_initialized():
            return {"success": False, "error": "Service not initialized"}

        try:
            # TODO: Add permission check here

            self.client.delete(collection_name=collection, points_selector=[memory_id])

            return {"success": True, "message": "Memory deleted successfully"}

        except Exception as e:
            logger.error(f"❌ Failed to delete memory: {e}")
            return {"success": False, "error": str(e)}

    # Collection Statistics & Analytics

    async def get_collection_stats(self, collection: str) -> Dict[str, Any]:
        """Get detailed statistics for a collection."""
        if not self._ensure_initialized():
            return {"success": False, "error": "Service not initialized"}

        try:
            # Get basic collection info
            collection_info = self.collection_manager.get_collection(collection)
            if not collection_info.get("success"):
                return collection_info

            # Get additional stats from Qdrant
            info = self.client.get_collection(collection)

            # Get recent activity (last 100 memories)
            recent_memories = self.client.scroll(
                collection_name=collection, limit=100, with_payload=True
            )

            # Analyze tags and metadata
            tag_counts = {}
            content_sizes = []
            users = set()

            for point in recent_memories[0]:
                payload = point.payload

                # Count tags
                for tag in payload.get("tags", []):
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1

                # Track content size
                content = payload.get("content", "")
                content_sizes.append(len(content))

                # Track users
                users.add(payload.get("added_by", "unknown"))

            stats = {
                "success": True,
                "collection": collection,
                "basic_stats": {
                    "total_memories": info.points_count,
                    "vectors_count": info.vectors_count,
                    "status": info.status.value if info.status else "unknown",
                },
                "content_analysis": {
                    "avg_content_size": (
                        sum(content_sizes) / len(content_sizes) if content_sizes else 0
                    ),
                    "total_contributors": len(users),
                    "top_tags": sorted(
                        tag_counts.items(), key=lambda x: x[1], reverse=True
                    )[:10],
                },
                "metadata": collection_info["collection"],
            }

            return stats

        except Exception as e:
            logger.error(f"❌ Failed to get collection stats: {e}")
            return {"success": False, "error": str(e)}

    # =================================================================
    # BACKWARD COMPATIBILITY METHODS FOR MCP SERVER
    # =================================================================

    def add_to_global_memory(
        self, content: str, category: str = "general", importance: float = 0.5
    ) -> Dict[str, Any]:
        """
        Legacy compatibility method for MCP server.
        Maps to shared-knowledge collection.
        """
        if not self._ensure_initialized():
            return {"success": False, "error": "Service not initialized"}

        try:
            # Use the actual global_memory collection directly
            collection_name = self.legacy_collections["global"]

            # Add content with legacy-compatible metadata
            metadata = {
                "category": category,
                "importance": importance,
                "memory_type": "global",  # For legacy compatibility
                "legacy_source": "add_to_global_memory",
            }

            result = self._add_memory_sync(
                collection_name=collection_name, content=content, metadata=metadata
            )

            if result["success"]:
                return {
                    "success": True,
                    "message": (f"Added to global memory (category: {category})"),
                    "content_hash": result.get("memory_id", "unknown"),
                }
            else:
                return result

        except Exception as e:
            logger.error(f"❌ add_to_global_memory failed: {e}")
            return {"success": False, "error": str(e)}

    def add_to_learned_memory(
        self, content: str, pattern_type: str = "insight", confidence: float = 0.7
    ) -> Dict[str, Any]:
        """
        Legacy compatibility method for MCP server.
        Maps to learned-patterns collection.
        """
        if not self._ensure_initialized():
            return {"success": False, "error": "Service not initialized"}

        try:
            # Use the actual learned_memory collection directly
            collection_name = self.legacy_collections["learned"]

            # Add content with legacy-compatible metadata
            metadata = {
                "pattern_type": pattern_type,
                "confidence": confidence,
                "memory_type": "learned",  # For legacy compatibility
                "legacy_source": "add_to_learned_memory",
            }

            result = self._add_memory_sync(
                collection_name=collection_name, content=content, metadata=metadata
            )

            if result["success"]:
                return {
                    "success": True,
                    "message": (f"Added to learned memory (pattern: {pattern_type})"),
                    "content_hash": result.get("memory_id", "unknown"),
                }
            else:
                return result

        except Exception as e:
            logger.error(f"❌ add_to_learned_memory failed: {e}")
            return {"success": False, "error": str(e)}

    def add_to_agent_memory(
        self, content: str, agent_id: Optional[str] = None, memory_type: str = "general"
    ) -> Dict[str, Any]:
        """
        Legacy compatibility method for MCP server.
        Maps to agent-context collection.
        """
        if not self._ensure_initialized():
            return {"success": False, "error": "Service not initialized"}

        try:
            # Use provided agent_id or default
            target_agent_id = agent_id or "default"

            # For agent memory, use agent-specific collection if it exists
            # Otherwise, fall back to a general agent collection
            collection_name = f"agent_specific_memory_{target_agent_id}"

            # Try to use existing agent-specific collection, otherwise use first available
            try:
                # Check if this specific agent collection exists
                self.client.get_collection(collection_name)
            except:
                # Fall back to any available agent collection
                # This maintains backward compatibility
                available_collections = self.client.get_collections().collections
                agent_collections = [
                    c.name
                    for c in available_collections
                    if c.name.startswith("agent_specific_memory_")
                ]
                if agent_collections:
                    collection_name = agent_collections[0]  # Use first available
                else:
                    # No agent collection found, create a default one
                    collection_name = "agent_specific_memory_default"

            # Add content with legacy-compatible metadata
            metadata = {
                "agent_id": target_agent_id,
                "memory_type": memory_type,
                "legacy_source": "add_to_agent_memory",
            }

            result = self._add_memory_sync(
                collection_name=collection_name, content=content, metadata=metadata
            )

            if result["success"]:
                return {
                    "success": True,
                    "message": (f"Added to agent memory (agent: {target_agent_id})"),
                    "content_hash": result.get("memory_id", "unknown"),
                }
            else:
                return result

        except Exception as e:
            logger.error(f"❌ add_to_agent_memory failed: {e}")
            return {"success": False, "error": str(e)}

    def query_memory(
        self,
        query: str,
        memory_types: Optional[List[str]] = None,
        limit: int = 10,
        min_score: float = 0.3,
    ) -> Dict[str, Any]:
        """
        Legacy compatibility method for MCP server.
        Maps memory types to corresponding collections.
        """
        if not self._ensure_initialized():
            return {"success": False, "error": "Service not initialized"}

        try:
            # Map legacy memory types to collection names
            if memory_types is None:
                memory_types = ["global", "learned", "agent"]

            collection_names = []
            for mem_type in memory_types:
                if mem_type == "global":
                    collection_names.append("global_memory")
                elif mem_type == "learned":
                    collection_names.append("learned_memory")
                elif mem_type == "agent":
                    # For agent, search all agent-specific collections
                    available_collections = self.client.get_collections().collections
                    agent_collections = [
                        c.name
                        for c in available_collections
                        if c.name.startswith("agent_specific_memory_")
                    ]
                    collection_names.extend(agent_collections)
                else:
                    logger.warning(f"Unknown legacy memory type: {mem_type}")

            if not collection_names:
                return {
                    "success": False,
                    "error": (
                        f"No valid collections found for memory types: {memory_types}"
                    ),
                }

            # Search across collections using sync wrapper
            result = self._search_memory_sync(
                collection_names=collection_names,
                query=query,
                limit=limit,
                min_score=min_score,
            )

            if result["success"]:
                # Add memory_type to results for legacy compatibility
                for memory in result["results"]:
                    collection_name = memory.get("collection", "")
                    if collection_name == "global_memory":
                        memory["memory_type"] = "global"
                    elif collection_name == "learned_memory":
                        memory["memory_type"] = "learned"
                    elif collection_name.startswith("agent_specific_memory_"):
                        memory["memory_type"] = "agent"
                    else:
                        memory["memory_type"] = "unknown"

                return {
                    "success": True,
                    "results": result["results"],
                    "total_results": result["total_results"],
                    "memory_types_searched": memory_types,
                    "collections_searched": collection_names,
                }
            else:
                return result

        except Exception as e:
            logger.error(f"❌ query_memory failed: {e}")
            return {"success": False, "error": str(e)}

    def compare_against_learned_memory(
        self, situation: str, comparison_type: str = "similarity", limit: int = 5
    ) -> Dict[str, Any]:
        """
        Legacy compatibility method for MCP server.
        Searches only learned-patterns collection.
        """
        if not self._ensure_initialized():
            return {"success": False, "error": "Service not initialized"}

        try:
            collection_name = "learned_memory"  # Use actual collection name

            # Search learned patterns using sync wrapper
            result = self._search_memory_sync(
                collection_names=[collection_name],
                query=situation,
                limit=limit,
                min_score=0.3,  # Lower threshold for pattern matching
            )

            if result["success"]:
                # Format results for legacy compatibility
                patterns = []
                for memory in result["results"]:
                    patterns.append(
                        {
                            "content": memory["content"],
                            "similarity_score": memory["score"],
                            "pattern_type": memory["metadata"].get(
                                "pattern_type", "insight"
                            ),
                            "confidence": memory["metadata"].get("confidence", 0.7),
                            "timestamp": memory["metadata"].get("timestamp"),
                        }
                    )

                return {
                    "success": True,
                    "results": patterns,
                    "total_patterns": len(patterns),
                    "comparison_type": comparison_type,
                    "situation_analyzed": situation,
                }
            else:
                return result

        except Exception as e:
            logger.error(f"❌ compare_against_learned_memory failed: {e}")
            return {"success": False, "error": str(e)}

    # Helper methods

    def _ensure_initialized(self) -> bool:
        """Ensure service is initialized."""
        return (
            self.initialized
            and self.client is not None
            and self.collection_manager is not None
            and self.embedding_model is not None
        )

    def _embed_text(self, text: str) -> List[float]:
        """Generate embedding for text."""
        if not self.embedding_model:
            raise RuntimeError("Embedding model not initialized")
        return self.embedding_model.encode(text).tolist()

    def _generate_content_hash(self, content: str) -> str:
        """Generate unique hash for content as valid UUID."""
        import uuid

        # Generate a deterministic UUID5 from content
        # Use a fixed namespace UUID for consistency
        namespace = uuid.UUID("12345678-1234-5678-1234-123456789abc")
        return str(uuid.uuid5(namespace, content))

    def _add_memory_sync(
        self, collection_name: str, content: str, metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Sync wrapper for add_memory method."""
        try:
            # Generate embedding
            embedding = self._embed_text(content)
            memory_id = self._generate_content_hash(content)

            # Prepare metadata
            if metadata is None:
                metadata = {}

            metadata.update(
                {
                    "content": content,
                    "timestamp": datetime.now().isoformat(),
                    "added_by": self.current_user,
                }
            )

            # Create point for storage
            point = PointStruct(id=memory_id, vector=embedding, payload=metadata)

            # Store in Qdrant
            self.client.upsert(collection_name=collection_name, points=[point])

            return {
                "success": True,
                "memory_id": memory_id,
                "message": f"Memory added to {collection_name}",
            }

        except Exception as e:
            logger.error(f"Failed to add memory to {collection_name}: {e}")
            return {"success": False, "error": str(e)}

    def _search_memory_sync(
        self,
        collection_names: List[str],
        query: str,
        limit: int = 10,
        min_score: float = 0.3,
    ) -> Dict[str, Any]:
        """Sync wrapper for search_memory method."""
        try:
            query_embedding = self._embed_text(query)
            all_results = []

            for collection_name in collection_names:
                try:
                    results = self.client.search(
                        collection_name=collection_name,
                        query_vector=query_embedding,
                        limit=limit,
                        score_threshold=min_score,
                    )

                    for result in results:
                        all_results.append(
                            {
                                "content": result.payload.get("content", ""),
                                "score": result.score,
                                "collection": collection_name,
                                "metadata": result.payload,
                            }
                        )

                except Exception as e:
                    logger.warning(f"Failed to search {collection_name}: {e}")
                    continue

            # Sort by score
            all_results.sort(key=lambda x: x["score"], reverse=True)

            return {
                "success": True,
                "results": all_results[:limit],
                "query": query,
                "total_results": len(all_results),
            }

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {"success": False, "error": str(e)}