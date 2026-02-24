"""
System and collections handlers for MCP Memory Server.
Handles system health monitoring and generic collection operations.
"""

from typing import Dict, Any
from datetime import datetime

try:
    from ..server_config import get_logger
    from ..error_handler import error_handler
except ImportError:
    # Fallback for standalone usage
    import logging

    def get_logger(name: str):
        return logging.getLogger(name)

    class MockErrorHandler:
        def get_error_stats(self):
            return {"total_errors": 0}

    error_handler = MockErrorHandler()

logger = get_logger("system-collections-handlers")


class SystemAndCollectionsHandlers:
    """Handles system health and generic collection operations."""

    def __init__(self, memory_manager, markdown_processor=None):
        """Initialize with memory manager and optional processors."""
        self.memory_manager = memory_manager
        self.markdown_processor = markdown_processor

    def handle_system_health(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system health check tool call."""
        try:
            # Get health information
            health_info = {
                "timestamp": str(datetime.now()),
                "memory_manager": {
                    "available": self.memory_manager is not None,
                    "initialized": (
                        self.memory_manager is not None
                        and getattr(
                            self.memory_manager, "collections_initialized", False
                        )
                    ),
                },
                "error_statistics": error_handler.get_error_stats(),
                "components": {
                    "markdown_processor": self.markdown_processor is not None
                },
            }

            # Test basic connectivity if memory manager is available
            if self.memory_manager:
                try:
                    if (
                        hasattr(self.memory_manager, "client")
                        and self.memory_manager.client
                    ):
                        collections = self.memory_manager.client.get_collections()
                        health_info["components"]["qdrant"] = {
                            "status": "healthy",
                            "collections_count": len(collections.collections),
                        }
                    else:
                        health_info["components"]["qdrant"] = {
                            "status": "unavailable",
                            "error": "No Qdrant client",
                        }

                    if (
                        hasattr(self.memory_manager, "embedding_model")
                        and self.memory_manager.embedding_model
                    ):
                        health_info["components"]["embedding_model"] = {
                            "status": "healthy",
                            "model": str(self.memory_manager.embedding_model),
                        }
                    else:
                        health_info["components"]["embedding_model"] = {
                            "status": "unavailable"
                        }

                except Exception as e:
                    health_info["components"]["qdrant"] = {
                        "status": "error",
                        "error": str(e),
                    }

            # Determine overall health status
            component_issues = []
            for component, info in health_info["components"].items():
                if isinstance(info, dict) and info.get("status") in [
                    "unavailable",
                    "error",
                ]:
                    component_issues.append(component)

            if not component_issues:
                overall_status = "healthy"
                status_text = "✅ All systems operational"
            elif len(component_issues) == len(health_info["components"]):
                overall_status = "critical"
                status_text = (
                    f"❌ Critical: All components have issues: "
                    f"{', '.join(component_issues)}"
                )
            else:
                overall_status = "degraded"
                status_text = f"⚠️ Degraded: Issues with: {', '.join(component_issues)}"

            health_info["overall_status"] = overall_status

            # Format health info for display
            health_text = f"""# System Health Report

**Status:** {status_text}  
**Timestamp:** {health_info["timestamp"]}

## Component Status

### Memory Manager
- **Available:** {"✅" if health_info["memory_manager"]["available"] else "❌"}
- **Initialized:** {"✅" if health_info["memory_manager"]["initialized"] else "❌"}

### Components
"""

            for component, info in health_info["components"].items():
                if isinstance(info, dict):
                    status = info.get("status", "unknown")
                    if status == "healthy":
                        status_icon = "✅"
                    elif status == "unavailable":
                        status_icon = "⚠️"
                    else:
                        status_icon = "❌"

                    health_text += (
                        f"- **{component.replace('_', ' ').title()}:** "
                        f"{status_icon} {status}\n"
                    )

                    if "error" in info:
                        health_text += f"  - Error: {info['error']}\n"
                else:
                    health_text += (
                        f"- **{component.replace('_', ' ').title()}:** "
                        f"{ '✅' if info else '❌' }\n"
                    )

            # Add error statistics if available
            error_stats = health_info.get("error_statistics", {})
            if error_stats.get("total_errors", 0) > 0:
                health_text += f"""
## Error Statistics
- **Total Errors:** {error_stats.get("total_errors", 0)}
- **Recovery Attempts:** {error_stats.get("recovery_attempts", 0)}
- **Successful Recoveries:** {error_stats.get("successful_recoveries", 0)}
"""

                if error_stats.get("errors_by_category"):
                    health_text += "\n### Errors by Category\n"
                    for category, count in error_stats["errors_by_category"].items():
                        health_text += f"- **{category.title()}:** {count}\n"

            return {"content": [{"type": "text", "text": health_text}]}

        except Exception as e:
            logger.error(f"Error in system health check: {e}")
            return {
                "isError": True,
                "content": [
                    {"type": "text", "text": f"❌ Health check failed: {str(e)}"}
                ],
            }

    # Generic Collection Tools
    async def handle_create_collection(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle create_collection tool call."""
        try:
            collection_name = arguments.get("collection_name")
            description = arguments.get("description", "")
            metadata = arguments.get("metadata", {})

            if not collection_name:
                return {
                    "isError": True,
                    "content": [
                        {"type": "text", "text": "Collection name is required"}
                    ],
                }

            # Use the GenericMemoryService to create the collection
            result = await self.memory_manager.generic_service.create_collection(
                collection_name, description, metadata
            )

            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Successfully created collection '{collection_name}'",
                    }
                ]
            }
        except Exception as e:
            logger.error(f"Error creating collection: {e}")
            return {
                "isError": True,
                "content": [
                    {"type": "text", "text": f"Failed to create collection: {str(e)}"}
                ],
            }

    async def handle_list_collections(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle list_collections tool call."""
        try:
            include_stats = arguments.get("include_stats", True)

            # Get collections from GenericMemoryService
            collections_result = (
                await self.memory_manager.generic_service.list_collections(
                    include_stats=include_stats
                )
            )

            if not collections_result.get("success"):
                return {
                    "isError": True,
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Failed to list collections: "
                                f"{collections_result.get('error', 'unknown error')}"
                            ),
                        }
                    ],
                }

            collections = collections_result.get("collections", [])
            result_text = f"Found {len(collections)} collections:\n\n"

            for collection in collections:
                name = collection.get("name", "unknown")
                description = collection.get("description")
                metadata = collection.get("metadata") or {}
                stats = collection.get("stats") or {}

                result_text += f"**{name}**\n"
                if description:
                    result_text += f"  Description: {description}\n"

                if include_stats:
                    document_count = (
                        stats.get("document_count")
                        or stats.get("total_memories")
                        or stats.get("vectors_count")
                        or 0
                    )
                    result_text += f"  Documents: {document_count}\n"

                if metadata:
                    result_text += f"  Metadata: {metadata}\n"
                result_text += "\n"

            return {"content": [{"type": "text", "text": result_text}]}
        except Exception as e:
            logger.error(f"Error listing collections: {e}")
            return {
                "isError": True,
                "content": [
                    {"type": "text", "text": f"Failed to list collections: {str(e)}"}
                ],
            }

    async def handle_add_to_collection(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle add_to_collection tool call."""
        try:
            collection_name = arguments.get("collection_name")
            content = arguments.get("content")
            metadata = arguments.get("metadata", {})
            importance = arguments.get("importance", 0.5)

            if not collection_name or not content:
                return {
                    "isError": True,
                    "content": [
                        {
                            "type": "text",
                            "text": "Collection name and content are required",
                        }
                    ],
                }

            # Use the GenericMemoryService to add content
            memory_id = await self.memory_manager.generic_service.add_to_collection(
                collection_name, content, metadata, importance
            )

            return {
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Successfully added content to collection "
                            f"'{collection_name}' with ID: {memory_id}"
                        ),
                    }
                ]
            }
        except Exception as e:
            logger.error(f"Error adding to collection: {e}")
            return {
                "isError": True,
                "content": [
                    {"type": "text", "text": f"Failed to add to collection: {str(e)}"}
                ],
            }

    async def handle_query_collection(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle query_collection tool call."""
        try:
            collection_name = arguments.get("collection_name")
            query = arguments.get("query")
            limit = arguments.get("limit", 10)
            min_score = arguments.get("min_score", 0.3)
            include_metadata = arguments.get("include_metadata", True)

            if not collection_name or not query:
                return {
                    "isError": True,
                    "content": [
                        {
                            "type": "text",
                            "text": "Collection name and query are required",
                        }
                    ],
                }

            # Use the GenericMemoryService to query the collection
            results = await self.memory_manager.generic_service.query_collection(
                collection_name, query, limit, min_score
            )

            if not results:
                result_text = (
                    f"No results found in collection '{collection_name}' "
                    f"for query: '{query}'"
                )
            else:
                result_text = (
                    f"Found {len(results)} results in collection "
                    f"'{collection_name}':\n\n"
                )

                for i, result in enumerate(results, 1):
                    result_text += (
                        f"**Result {i}** (Score: {result.get('score', 'N/A'):.3f})\n"
                    )
                    result_text += f"{result['content']}\n"

                    if include_metadata and result.get("metadata"):
                        result_text += f"Metadata: {result['metadata']}\n"
                    result_text += "\n"

            return {"content": [{"type": "text", "text": result_text}]}
        except Exception as e:
            logger.error(f"Error querying collection: {e}")
            return {
                "isError": True,
                "content": [
                    {"type": "text", "text": f"Failed to query collection: {str(e)}"}
                ],
            }

    async def handle_delete_collection(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle delete_collection tool call."""
        try:
            collection_name = arguments.get("collection_name")
            confirm = arguments.get("confirm", False)

            if not collection_name:
                return {
                    "isError": True,
                    "content": [
                        {"type": "text", "text": "Collection name is required"}
                    ],
                }

            if not confirm:
                return {
                    "isError": True,
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Confirmation required: set 'confirm' to true "
                                "to delete the collection"
                            ),
                        }
                    ],
                }

            # Use the GenericMemoryService to delete the collection
            await self.memory_manager.generic_service.delete_collection(collection_name)

            return {
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Successfully deleted collection '{collection_name}' "
                            f"and all its contents"
                        ),
                    }
                ]
            }
        except Exception as e:
            logger.error(f"Error deleting collection: {e}")
            return {
                "isError": True,
                "content": [
                    {"type": "text", "text": f"Failed to delete collection: {str(e)}"}
                ],
            }

    async def handle_get_collection_stats(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle get_collection_stats tool call."""
        try:
            collection_name = arguments.get("collection_name")

            if not collection_name:
                return {
                    "isError": True,
                    "content": [
                        {"type": "text", "text": "Collection name is required"}
                    ],
                }

            # Use the GenericMemoryService to get collection stats
            stats = await self.memory_manager.generic_service.get_collection_stats(
                collection_name
            )

            result_text = f"**Statistics for Collection '{collection_name}'**\n\n"
            result_text += f"Document Count: {stats['document_count']}\n"
            result_text += f"Total Size: {stats.get('total_size', 'Unknown')}\n"
            result_text += f"Last Updated: {stats.get('last_updated', 'Unknown')}\n"

            if stats.get("metadata"):
                result_text += f"Metadata: {stats['metadata']}\n"

            return {"content": [{"type": "text", "text": result_text}]}
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {
                "isError": True,
                "content": [
                    {
                        "type": "text",
                        "text": f"Failed to get collection stats: {str(e)}",
                    }
                ],
            }