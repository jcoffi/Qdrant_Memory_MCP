# MCP Container Quickstart

Use this guide to run the memory server through Docker with a Python startup script that safely reuses existing containers.

## What this does

`scripts/start_mcp_container.py` will:
- Check Docker availability
- Create the Docker network if needed
- Start (or create) the `mcp-qdrant` container only when not already running
- Start (or create) the `mcp-memory-runtime` container only when not already running
- Launch `python memory_server.py` inside the runtime container over stdio using `docker exec -i`

That means repeated launches are idempotent and do not create duplicate containers.

## Requirements

- Docker installed and available on your PATH
- Runtime image published at `ghcr.io/jcoffi/qdrant-memory-mcp:latest` (or set `MCP_IMAGE`)

## MCP Configuration

Set your MCP config to call the Python startup script directly:

```json
{
  "mcpServers": {
    "memory-server": {
      "command": "python3",
      "args": [
        "/absolute/path/to/Qdrant_Memory_MCP/scripts/start_mcp_container.py"
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

- `MCP_IMAGE`: runtime image (default: `ghcr.io/jcoffi/qdrant-memory-mcp:latest`)
- `QDRANT_IMAGE`: Qdrant image (default: `qdrant/qdrant:latest`)
- `MCP_RUNTIME_CONTAINER`: runtime container name (default: `mcp-memory-runtime`)
- `QDRANT_CONTAINER`: qdrant container name (default: `mcp-qdrant`)
- `MCP_DOCKER_NETWORK`: network name (default: `mcp-memory-net`)
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
