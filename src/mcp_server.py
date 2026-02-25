"""
MCP (Model Context Protocol) server implementation for memory management.
Handles the MCP protocol communication and tool orchestration.
Enhanced with production-grade error handling and monitoring.
"""

import json
from typing import Dict, Any, List, Optional

from .server_config import get_logger
from .qdrant_manager import ensure_qdrant_running
from .tool_handlers import ToolHandlers
from .resource_handlers import ResourceHandlers
from .prompt_handlers import PromptHandlers
from .tool_definitions import MemoryToolDefinitions
from .mcp_protocol_handler import MCPProtocolHandler
from .system_health_monitor import SystemHealthMonitor

logger = get_logger("mcp-server")

# Import our memory manager
try:
    from .memory_manager import QdrantMemoryManager

    MEMORY_AVAILABLE = True
    logger.info("Memory manager available")
except ImportError as e:
    MEMORY_AVAILABLE = False
    logger.error(f"Memory manager not available: {e}")


class MemoryMCPServer:
    """MCP Server focused solely on memory management using Qdrant."""

    def __init__(self, server_mode="full"):
        self.server_mode = server_mode
        logger.info(f"Starting Memory MCP Server in {server_mode.upper()} mode...")

        # Ensure Qdrant is running before initializing memory manager
        if not ensure_qdrant_running():
            logger.error(
                "❌ Failed to start Qdrant. Memory server will not function properly."
            )

        if MEMORY_AVAILABLE:
            try:
                self.memory_manager = QdrantMemoryManager()
                logger.info("Memory manager initialized")
            except Exception as e:
                logger.error(f"Failed to initialize memory manager: {e}")
                self.memory_manager = None
        else:
            self.memory_manager = None

        # Initialize handlers and monitors
        self.tool_handlers = ToolHandlers(self.memory_manager)
        self.resource_handlers = ResourceHandlers(self.memory_manager)
        self.health_monitor = SystemHealthMonitor(self.memory_manager)

        # Conditionally initialize prompt handlers based on server mode
        if server_mode in ["full", "prompts-only"]:
            self.prompt_handlers = PromptHandlers(self.memory_manager)
            logger.info("Prompt handlers initialized")
        else:
            self.prompt_handlers = None
            logger.info("Prompt handlers disabled (tools-only mode)")

        logger.info("Memory MCP Server initialized")

    def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health information."""
        return self.health_monitor.get_system_health()

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available memory management tools."""
        if not self.memory_manager:
            return []
        return MemoryToolDefinitions.get_all_tools()

    async def handle_tool_call(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle a tool call and return the result."""
        return await self.tool_handlers.handle_tool_call(tool_name, arguments)

    def get_available_resources(self) -> List[Dict[str, Any]]:
        """Get list of available resources."""
        if not self.memory_manager:
            return []
        return self.resource_handlers.list_resources()

    async def handle_resource_read(
        self, uri: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle a resource read request."""
        try:
            # Read the resource with all parameters
            result = await self.resource_handlers.read_resource(uri, **params)

            if result.get("status") == "error":
                return {
                    "error": {
                        "code": -32603,
                        "message": result.get("message", "Resource read failed"),
                    }
                }

            # Format successful response - MCP requires 'contents' array
            resource_data = result.get("data", {})

            # Convert the data to a properly formatted JSON string
            json_text = json.dumps(resource_data, indent=2, ensure_ascii=False)

            return {
                "contents": [
                    {"uri": uri, "mimeType": "application/json", "text": json_text}
                ]
            }

        except Exception as e:
            logger.error(f"Error reading resource {uri}: {e}")
            return {
                "error": {
                    "code": -32603,
                    "message": f"Failed to read resource: {str(e)}",
                }
            }

    def get_available_prompts(self) -> List[Dict[str, Any]]:
        """Get list of available prompts."""
        # Return empty list in tools-only mode or if components not available
        if (
            self.server_mode == "tools-only"
            or not self.memory_manager
            or not self.prompt_handlers
        ):
            return []
        return self.prompt_handlers.list_prompts()

    async def handle_prompt_get(
        self, name: str, arguments: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """Handle a prompt get request."""
        # Return error in tools-only mode
        if self.server_mode == "tools-only" or not self.prompt_handlers:
            return {
                "error": {
                    "code": -32601,
                    "message": "Prompts not available in tools-only mode",
                }
            }

        try:
            # Get the prompt with arguments
            result = await self.prompt_handlers.get_prompt(name, arguments)

            if result.get("status") == "error":
                return {
                    "error": {
                        "code": -32603,
                        "message": result.get("message", "Prompt get failed"),
                    }
                }

            # Support both legacy shape (result['prompt']) and current
            # shape (result['content'] + result['metadata']).
            prompt_data = (
                result.get("prompt", {})
                if isinstance(result.get("prompt"), dict)
                else {}
            )
            description = (
                result.get("description")
                or prompt_data.get("name")
                or result.get("metadata", {}).get("prompt_type")
                or name
            )

            guidance_text = ""
            if prompt_data:
                guidance_text = str(prompt_data.get("content", "")).strip()
            else:
                content_blocks = result.get("content", [])
                if isinstance(content_blocks, str):
                    guidance_text = content_blocks.strip()
                elif isinstance(content_blocks, list):
                    text_parts = []
                    for block in content_blocks:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text_value = str(block.get("text", "")).strip()
                            if text_value:
                                text_parts.append(text_value)
                    guidance_text = "\n\n".join(text_parts)

            if not guidance_text:
                guidance_text = "No reference content available for this prompt."

            # Format as reference guide content
            return {
                "description": description,
                "messages": [
                    {
                        "role": "assistant",
                        "content": {
                            "type": "text",
                            "text": f"Here is the {name} reference guide:\n\n{guidance_text}\n\n---\nThis is reference information only.",
                        },
                    }
                ],
            }

        except Exception as e:
            logger.error(f"Error getting prompt {name}: {e}")
            return {
                "error": {"code": -32603, "message": f"Failed to get prompt: {str(e)}"}
            }


async def run_mcp_server(server_mode="full"):
    """Main server loop for MCP protocol handling."""
    # Create server instance with specified mode
    server = MemoryMCPServer(server_mode)

    # Create protocol handler
    protocol_handler = MCPProtocolHandler(server)

    # Run the protocol loop
    await protocol_handler.run_protocol_loop()


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_mcp_server())
