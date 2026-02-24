# MCP Memory Server with Qdrant Vector Database

🎉 **STATUS: PRODUCTION READY** ✅ | **All 9 Implementation Steps Complete**

A Model Context Protocol (MCP) server that provides intelligent memory management capabilities using Qdrant vector database for semantic search and storage. Built specifically for Cursor IDE integration with comprehensive policy governance.

## 🌟 Complete Feature Set

🧠 **Multiple Memory Types**
- **Global Memory**: Shared across all agents for common knowledge
- **Learned Memory**: Lessons learned and mistakes to avoid  
- **Agent-Specific Memory**: Individual agent contexts and specialized knowledge

🔍 **Advanced Search & Processing**
- Vector-based similarity search using sentence transformers
- Duplicate detection to prevent redundant content
- Configurable similarity thresholds
- Markdown processing with intelligent content cleaning
- YAML front matter extraction and section organization

🏛️ **Policy Governance System** *(NEW)*
- **75 Enforceable Rules** across 4 categories (Principles, Forbidden Actions, Requirements, Style Guide)
- **Semantic Policy Search** with vector embeddings for contextual rule discovery
- **Compliance Tracking** with violation logging and agent accountability
- **Version Management** with SHA-256 integrity verification
- **Schema Validation** enforcing required sections and data consistency

📋 **Prompt Management System** *(NEW)*
- **Dynamic Template Engine** with variable substitution and conditional logic
- **Agent-Specific Prompts** with custom configurations and role definitions
- **Validation Framework** ensuring prompt consistency and formatting standards
- **Context Integration** with memory and policy systems for enhanced prompts

🔧 **Complete MCP Integration**
- **9 MCP Tools**: Memory management, markdown processing, policy compliance, prompt generation
- **4 MCP Resources**: Read-only access to memory, policies, prompts, and system status
- Standard MCP protocol compliance for Cursor IDE
- stdin/stdout communication with comprehensive error handling

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│                 │    │                  │    │                 │
│   Cursor IDE    │◄──►│  MCP Server      │◄──►│  Qdrant Vector  │
│                 │    │  (stdin/stdout)  │    │  Database       │
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │ Sentence         │
                       │ Transformers     │
                       │ (Embeddings)     │
                       └──────────────────┘
```

## Installation

### Prerequisites

1. **Python 3.10+** with pip
2. **Qdrant Database** (can run locally with Docker)
3. **Cursor IDE** for MCP integration

### Setup Qdrant Database

Using Docker (recommended):

```bash
docker run -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant
```

Or install Qdrant locally following their [installation guide](https://qdrant.tech/documentation/quick-start/).

### Install Dependencies

Using Poetry (recommended):

```bash
# Install dependencies using Poetry
poetry install
```

Or using pip:

```bash
# Install Python dependencies
pip install -r requirements.txt
```

### Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` with your settings:
```env
# Qdrant Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_API_KEY=

# Embedding Model Configuration  
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384

# Memory Configuration
SIMILARITY_THRESHOLD=0.8
MAX_RESULTS=10

# Agent Configuration
DEFAULT_AGENT_ID=default

# Server Configuration
LOG_LEVEL=INFO
```

## Usage

### Starting the Server

```bash
python server.py
```

The server will:
1. Connect to Qdrant database
2. Initialize vector collections
3. Load the embedding model
4. Start listening for MCP commands via stdin/stdout

### Cursor IDE Integration

Add the server to your Cursor MCP configuration:

```json
{
  "mcpServers": {
    "memory-server": {
      "command": "/media/hannesn/storage/Code/MCP/.venv/bin/python",
      "args": ["/media/hannesn/storage/Code/MCP/server.py"],
      "cwd": "/media/hannesn/storage/Code/MCP",
      "env": {
        "PYTHONPATH": "/media/hannesn/storage/Code/MCP",
        "QDRANT_HOST": "localhost",
        "QDRANT_PORT": "6333",
        "EMBEDDING_MODEL": "all-MiniLM-L6-v2",
        "SIMILARITY_THRESHOLD": "0.8",
        "MAX_RESULTS": "10",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

Alternatively, you can run the server using Poetry:

```bash
poetry run python server.py
```

### Container MCP Startup (uvx)

- Use `uvx` to launch `qdrant-memory-mcp` directly from this repo.
- Startup checks for an existing `mcp-qdrant` container and only creates one when missing.
- Qdrant startup is based on `docker run --pull-always -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant`.

Example Cursor MCP config using uvx:

```json
{
  "mcpServers": {
    "memory-server-container": {
      "command": "uvx",
      "args": ["--from", "/absolute/path/to/Qdrant_Memory_MCP", "qdrant-memory-mcp"],
      "cwd": "./",
      "env": {
        "QDRANT_HOST": "localhost",
        "QDRANT_PORT": "6333",
        "EMBEDDING_MODEL": "all-MiniLM-L6-v2"
      }
    }
  }
}
```

See `docs/mcp-container-quickstart.md` for advanced options and configuration.

## MCP Tools

### 1. `set_agent_context`

Initialize agent context from a markdown file.

**Parameters:**
- `agent_id` (string): Unique identifier for the agent
- `context_file_path` (string): Path to markdown file with agent context
- `description` (string, optional): Description of the context

**Example:**
```json
{
  "tool": "set_agent_context",
  "arguments": {
    "agent_id": "frontend_dev",
    "context_file_path": "./contexts/frontend_agent.md",
    "description": "Frontend development agent context"
  }
}
```

### 2. `add_to_global_memory`

Add content to global memory shared across all agents.

**Parameters:**
- `file_path` (string): Path to markdown file
- `description` (string, optional): Content description

**Example:**
```json
{
  "tool": "add_to_global_memory", 
  "arguments": {
    "file_path": "./docs/coding_standards.md",
    "description": "Company coding standards"
  }
}
```

### 3. `add_to_learned_memory`

Store lessons learned to avoid repeated mistakes.

**Parameters:**
- `file_path` (string): Path to markdown file with lessons
- `lesson_type` (string): Type of lesson (e.g., "deployment", "security")
- `description` (string, optional): Lesson description

**Example:**
```json
{
  "tool": "add_to_learned_memory",
  "arguments": {
    "file_path": "./lessons/deployment_issues.md", 
    "lesson_type": "deployment",
    "description": "Critical deployment lessons"
  }
}
```

### 4. `add_to_agent_memory`

Store lessons learned to avoid repeated mistakes.

**Parameters:**
- `file_path` (string): Path to markdown file with lessons
- `lesson_type` (string): Type of lesson (e.g., "deployment", "security")
- `description` (string, optional): Lesson description

### 5. `query_memory`

Search memory collections for relevant content.

**Parameters:**
- `query` (string): Search query
- `memory_type` (string): "global", "learned", "agent", or "all" 
- `agent_id` (string, optional): Agent ID for agent-specific queries
- `max_results` (integer, optional): Maximum results (default: 10)

**Example:**
```json
{
  "tool": "query_memory",
  "arguments": {
    "query": "authentication best practices",
    "memory_type": "all",
    "max_results": 5
  }
}
```

### 6. `compare_against_learned_memory`

Check proposed actions against past lessons learned.

**Parameters:**
- `action_description` (string): Description of proposed action
- `agent_id` (string, optional): Agent making the request

**Example:**
```json
{
  "tool": "compare_against_learned_memory",
  "arguments": {
    "action_description": "Deploy database migration on Friday afternoon",
    "agent_id": "devops_agent"
  }
}
```

## Memory Types Explained

### Global Memory
- **Purpose**: Store knowledge shared across all agents
- **Content**: Coding standards, documentation, best practices
- **Access**: All agents can query this memory
- **Use Case**: Company-wide policies, architectural decisions

### Learned Memory  
- **Purpose**: Store lessons learned from past mistakes
- **Content**: Incident reports, post-mortems, anti-patterns
- **Access**: Most agents (exclude "human-like" testers)
- **Use Case**: Avoid repeating past mistakes, improve decisions

### Agent-Specific Memory
- **Purpose**: Store knowledge specific to individual agents
- **Content**: Role definitions, specialized knowledge, context
- **Access**: Only the specific agent
- **Use Case**: Agent initialization, specialized expertise

## Testing

### Run Basic Functionality Tests

```bash
python tests/test_basic_functionality.py
```

This will test:
- Qdrant connection and collection setup
- Memory operations (add, query, duplicate detection)
- Markdown processing and content cleaning
- Vector embedding and similarity search

### Manual Testing with Sample Data

1. Start the server:
```bash
python server.py
```

2. Use the provided sample markdown files in `sample_data/`:
   - `frontend_agent_context.md`: Frontend agent context
   - `backend_agent_context.md`: Backend agent context  
   - `deployment_lessons.md`: Learned lessons
   - `global_standards.md`: Global development standards

## Troubleshooting

### Common Issues

**Qdrant Connection Failed**
```
❌ Failed to initialize Qdrant: ConnectionError
```
- Ensure Qdrant is running on configured host/port
- Check firewall settings
- Verify API key if using Qdrant Cloud

**Embedding Model Download Issues**n- **Qdrant Connection Failed**
```
❌ Failed to initialize Qdrant: ConnectionError
```
- Ensure Qdrant is running on configured host/port
- Check firewall settings
- Verify API key if using Qdrant Cloud

**Embedding Model Download Issues**
```
❌ Failed to load embedding model
```
- Ensure internet connection for first download
- Check available disk space (models can be large)
- Try alternative model in configuration

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `QDRANT_HOST` | localhost | Qdrant server host |
| `QDRANT_PORT` | 6333 | Qdrant server port |
| `QDRANT_API_KEY` | | API key for Qdrant Cloud |
| `EMBEDDING_MODEL` | all-MiniLM-L6-v2 | Sentence transformer model |
| `EMBEDDING_DIMENSION` | 384 | Vector dimension size |
| `SIMILARITY_THRESHOLD` | 0.8 | Duplicate detection threshold |
| `MAX_RESULTS` | 10 | Default max query results |
| `DEFAULT_AGENT_ID` | default | Default agent identifier |
| `LOG_LEVEL` | INFO | Logging verbosity |

### Collection Names

- **Global Memory**: `global_memory`
- **Learned Memory**: `learned_memory`  
- **Agent Memory**: `agent_specific_memory_{agent_id}`

## Development

### Project Structure

```
mcp-memory-server/
├── server.py                 # Main MCP server
├── src/
│   ├── __init__.py
│   ├── config.py             # Configuration management
│   ├── memory_manager.py     # Qdrant operations
│   └── markdown_processor.py # Markdown handling
├── tests/
│   └── test_basic_functionality.py
├── sample_data/              # Example markdown files
├── docs/                     # Additional documentation
├── requirements.txt          # Python dependencies
├── pyproject.toml           # Poetry configuration
└── README.md                # This file
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `python -m pytest tests/`
5. Submit a pull request

### Adding New Tools

1. Add tool function to `MCPMemoryServer._register_tools()`
2. Update `_list_tools()` method with tool schema
3. Add tests for the new functionality
4. Update this README

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review Qdrant documentation for database issues
3. Check MCP protocol documentation for integration issues
4. Open an issue with detailed logs and configuration