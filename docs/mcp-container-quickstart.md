# MCP Container Quickstart

Use this guide to run the MCP server with `uvx` while starting a single Qdrant Docker container.

## What this does

`qdrant-memory-mcp` (from `uvx`) is the MCP startup command. It will:
- Check Docker availability
- Start (or create) the `mcp-qdrant` container only when not already running
- Run the MCP server process directly in the uvx environment

The Qdrant start path is based on this command from the README flow:
`docker run --pull-always -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant`

That means repeated launches do not create duplicate Qdrant containers.

## Requirements

- Docker installed and available on your PATH
- `uvx` installed (`uv tool install uv` or from your package manager)

## MCP Configuration

Point MCP to `uvx` and the package entrypoint:

```json
{
  "mcpServers": {
    "memory-server": {
      "command": "uvx",
      "args": [
        "--from",
        "/absolute/path/to/Qdrant_Memory_MCP",
        "qdrant-memory-mcp"
      ],
      "env": {
        "LOG_LEVEL": "INFO",
        "SIMILARITY_THRESHOLD": "0.8",
        "MAX_RESULTS": "10"
      }
    }
  }
}
```

## Optional environment variables

- `QDRANT_IMAGE`: Qdrant image (default: `qdrant/qdrant:latest`)
- `QDRANT_CONTAINER`: qdrant container name (default: `mcp-qdrant`)
- `QDRANT_STORAGE_DIR`: host path for storage bind mount (default: `$(pwd)/qdrant_storage`)
- `QDRANT_PORT`: host port for Qdrant (default: `6333`)
- `SKIP_QDRANT_START`: set to `1`/`true` to use external Qdrant instead of local container start

Pass-through runtime env vars include:
- `QDRANT_HOST`
- `QDRANT_PORT`
- `QDRANT_API_KEY`
- `EMBEDDING_MODEL`
- `EMBEDDING_DIMENSION`
- `SIMILARITY_THRESHOLD`
- `MAX_RESULTS`
- `DEFAULT_AGENT_ID`
- `LOG_LEVEL`
- `PROMPTS_ONLY`
- `TOOLS_ONLY`
- `UI`
- `UI_ONLY`

## External Qdrant mode

If you use Qdrant Cloud or another hosted endpoint:
- Set `SKIP_QDRANT_START=true`
- Set `QDRANT_HOST` and `QDRANT_PORT` in MCP `env`
