"""
Server configuration and constants for MCP Memory Server.
Enhanced with YAML configuration support and validation.
"""

import logging
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum


class LogLevel(Enum):
    """Supported logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class QdrantMode(Enum):
    """Qdrant connection modes."""
    LOCAL = "local"
    REMOTE = "remote"
    CLOUD = "cloud"


@dataclass
class QdrantConfig:
    """Qdrant configuration settings."""
    mode: QdrantMode = QdrantMode.LOCAL
    host: str = "localhost"
    port: int = 6333
    api_key: Optional[str] = None
    timeout: int = 60

    # Docker settings (for local mode)
    docker_image: str = "qdrant/qdrant:1.16"
    container_name: str = "qdrant"
    docker_ports: list = field(default_factory=lambda: ["6333:6333", "6334:6334"])

    # Timeouts
    startup_timeout: int = 15
    health_check_timeout: int = 5


@dataclass
class EmbeddingConfig:
    """Embedding model configuration."""
    model_name: str = "all-MiniLM-L6-v2"
    dimension: int = 384
    cache_folder: Optional[str] = None
    device: str = "cpu"  # or "cuda" for GPU


@dataclass
class MarkdownConfig:
    """Markdown processing configuration."""
    chunk_size: int = 900
    chunk_overlap: int = 200
    recursive_processing: bool = True

    # AI enhancement settings
    ai_enhancement_enabled: bool = True
    ai_analysis_depth: str = "standard"  # basic, standard, deep
    ai_content_optimization: bool = True


@dataclass
class PolicyConfig:
    """Policy management configuration."""
    directory: str = "./policy"
    rule_id_pattern: str = r"^[A-Z]+-\d+$"
    validation_strict: bool = True
    hash_algorithm: str = "sha256"


@dataclass
class MemoryConfig:
    """Memory type analysis configuration."""
    type_confidence_threshold: float = 0.6
    suggestion_enabled: bool = True


@dataclass
class DeduplicationConfig:
    """Deduplication settings."""
    similarity_threshold: float = 0.85
    near_miss_threshold: float = 0.80
    logging_enabled: bool = True
    diagnostics_enabled: bool = True


@dataclass
class ErrorHandlingConfig:
    """Error handling configuration."""
    retry_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter_enabled: bool = True


@dataclass
class ServerConfig:
    """Complete server configuration."""
    # Basic server info
    name: str = "memory-server"
    version: str = "1.0.0"
    description: str = "Memory management server for AI agents using Qdrant vector database"

    # Logging
    log_level: LogLevel = LogLevel.INFO
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_file: Optional[str] = None

    # Component configurations
    qdrant: QdrantConfig = field(default_factory=QdrantConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    markdown: MarkdownConfig = field(default_factory=MarkdownConfig)
    policy: PolicyConfig = field(default_factory=PolicyConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    deduplication: DeduplicationConfig = field(default_factory=DeduplicationConfig)
    error_handling: ErrorHandlingConfig = field(default_factory=ErrorHandlingConfig)

    # MCP Protocol settings
    protocol_version: str = "2024-11-05"


class ConfigManager:
    """Enhanced configuration manager with YAML support and validation."""

    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        self.config_path = Path(config_path) if config_path else None
        self.config = ServerConfig()
        self._load_config()
        self._validate_config()

    def _load_config(self):
        """Load configuration from various sources with precedence."""
        # 1. Load default values (already set in ServerConfig)

        # 2. Load from YAML file if specified
        if self.config_path and self.config_path.exists():
            self._load_yaml_config()

        # 3. Override with environment variables
        self._load_env_config()

    def _load_yaml_config(self):
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f)

            if not yaml_data:
                return

            # Update configuration with YAML data
            self._update_config_from_dict(yaml_data)
            logging.getLogger(__name__).info(f"Loaded config from {self.config_path}")

        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to load config from {self.config_path}: {e}")
            raise

    def _update_config_from_dict(self, data: Dict[str, Any]):
        """Update configuration from dictionary data."""
        # Update basic server settings
        if 'server' in data:
            server_data = data['server']
            if 'name' in server_data:
                self.config.name = server_data['name']
            if 'version' in server_data:
                self.config.version = server_data['version']
            if 'description' in server_data:
                self.config.description = server_data['description']

        # Update logging settings
        if 'logging' in data:
            log_data = data['logging']
            if 'level' in log_data:
                self.config.log_level = LogLevel(log_data['level'].upper())
            if 'format' in log_data:
                self.config.log_format = log_data['format']
            if 'file' in log_data:
                self.config.log_file = log_data['file']

        # Update Qdrant settings
        if 'qdrant' in data:
            qdrant_data = data['qdrant']
            if 'mode' in qdrant_data:
                self.config.qdrant.mode = QdrantMode(qdrant_data['mode'])
            if 'host' in qdrant_data:
                self.config.qdrant.host = qdrant_data['host']
            if 'port' in qdrant_data:
                self.config.qdrant.port = qdrant_data['port']
            if 'api_key' in qdrant_data:
                self.config.qdrant.api_key = qdrant_data['api_key']
            if 'timeout' in qdrant_data:
                self.config.qdrant.timeout = qdrant_data['timeout']

        # Update embedding settings
        if 'embedding' in data:
            emb_data = data['embedding']
            if 'model_name' in emb_data:
                self.config.embedding.model_name = emb_data['model_name']
            if 'device' in emb_data:
                self.config.embedding.device = emb_data['device']

        # Update other component settings similarly...
        # (Additional sections can be added as needed)

    def _load_env_config(self):
        """Load configuration from environment variables."""
        # Server settings
        if os.getenv('MCP_SERVER_NAME'):
            self.config.name = os.getenv('MCP_SERVER_NAME')

        # Logging settings
        if os.getenv('LOG_LEVEL'):
            try:
                self.config.log_level = LogLevel(os.getenv('LOG_LEVEL').upper())
            except ValueError:
                pass

        if os.getenv('LOG_FILE'):
            self.config.log_file = os.getenv('LOG_FILE')

        # Qdrant settings
        if os.getenv('QDRANT_HOST'):
            self.config.qdrant.host = os.getenv('QDRANT_HOST')

        if os.getenv('QDRANT_PORT'):
            try:
                self.config.qdrant.port = int(os.getenv('QDRANT_PORT'))
            except ValueError:
                pass

        if os.getenv('QDRANT_API_KEY'):
            self.config.qdrant.api_key = os.getenv('QDRANT_API_KEY')

        # Embedding settings
        if os.getenv('EMBEDDING_MODEL'):
            self.config.embedding.model_name = os.getenv('EMBEDDING_MODEL')

        if os.getenv('EMBEDDING_DEVICE'):
            self.config.embedding.device = os.getenv('EMBEDDING_DEVICE')

    def _validate_config(self):
        """Validate configuration values."""
        errors = []

        # Validate Qdrant settings
        if self.config.qdrant.port < 1 or self.config.qdrant.port > 65535:
            errors.append(f"Invalid Qdrant port: {self.config.qdrant.port}")

        if self.config.qdrant.timeout < 1:
            errors.append(f"Invalid Qdrant timeout: {self.config.qdrant.timeout}")

        # Validate embedding settings
        if not self.config.embedding.model_name:
            errors.append("Embedding model name cannot be empty")

        # Validate thresholds
        if not (0.0 <= self.config.deduplication.similarity_threshold <= 1.0):
            errors.append(f"Invalid similarity threshold: {self.config.deduplication.similarity_threshold}")

        if not (0.0 <= self.config.memory.type_confidence_threshold <= 1.0):
            errors.append(f"Invalid confidence threshold: {self.config.memory.type_confidence_threshold}")

        # Validate chunk sizes
        if self.config.markdown.chunk_size < 100:
            errors.append(f"Chunk size too small: {self.config.markdown.chunk_size}")

        if self.config.markdown.chunk_overlap >= self.config.markdown.chunk_size:
            errors.append("Chunk overlap must be smaller than chunk size")

        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
            raise ValueError(error_msg)

    def get_config(self) -> ServerConfig:
        """Get the current configuration."""
        return self.config

    def save_config(self, path: Optional[Union[str, Path]] = None):
        """Save current configuration to YAML file."""
        save_path = Path(path) if path else self.config_path

        if not save_path:
            raise ValueError("No save path specified")

        config_dict = self._config_to_dict()

        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=True)

        logging.getLogger(__name__).info(f"Configuration saved to {save_path}")

    def _config_to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for YAML export."""
        return {
            'server': {
                'name': self.config.name,
                'version': self.config.version,
                'description': self.config.description
            },
            'logging': {
                'level': self.config.log_level.value,
                'format': self.config.log_format,
                'file': self.config.log_file
            },
            'qdrant': {
                'mode': self.config.qdrant.mode.value,
                'host': self.config.qdrant.host,
                'port': self.config.qdrant.port,
                'timeout': self.config.qdrant.timeout,
                'docker_image': self.config.qdrant.docker_image,
                'container_name': self.config.qdrant.container_name
            },
            'embedding': {
                'model_name': self.config.embedding.model_name,
                'dimension': self.config.embedding.dimension,
                'device': self.config.embedding.device
            },
            'markdown': {
                'chunk_size': self.config.markdown.chunk_size,
                'chunk_overlap': self.config.markdown.chunk_overlap,
                'recursive_processing': self.config.markdown.recursive_processing,
                'ai_enhancement_enabled': self.config.markdown.ai_enhancement_enabled
            },
            'deduplication': {
                'similarity_threshold': self.config.deduplication.similarity_threshold,
                'near_miss_threshold': self.config.deduplication.near_miss_threshold,
                'logging_enabled': self.config.deduplication.logging_enabled
            },
            'error_handling': {
                'retry_attempts': self.config.error_handling.retry_attempts,
                'base_delay': self.config.error_handling.base_delay,
                'max_delay': self.config.error_handling.max_delay
            }
        }


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def initialize_config(config_path: Optional[Union[str, Path]] = None) -> ConfigManager:
    """Initialize the global configuration manager."""
    global _config_manager
    _config_manager = ConfigManager(config_path)
    return _config_manager


def get_config_manager() -> ConfigManager:
    """Get the global configuration manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config() -> ServerConfig:
    """Get the current server configuration."""
    return get_config_manager().get_config()


# Backwards compatibility - expose configuration values as constants
config = get_config()

# Server Metadata
SERVER_NAME = config.name
SERVER_VERSION = config.version
SERVER_DESCRIPTION = config.description

# MCP Protocol Version
MCP_PROTOCOL_VERSION = config.protocol_version

# Logging Configuration
LOGGING_LEVEL = getattr(logging, config.log_level.value)
LOGGING_FORMAT = config.log_format

# Qdrant Configuration
QDRANT_DEFAULT_HOST = config.qdrant.host
QDRANT_DEFAULT_PORT = config.qdrant.port
QDRANT_HEALTH_ENDPOINT = f"http://{config.qdrant.host}:{config.qdrant.port}/"
QDRANT_COLLECTIONS_ENDPOINT = f"http://{config.qdrant.host}:{config.qdrant.port}/collections"

# Docker Configuration
QDRANT_DOCKER_IMAGE = config.qdrant.docker_image
QDRANT_CONTAINER_NAME = config.qdrant.container_name
QDRANT_DOCKER_PORTS = config.qdrant.docker_ports

# Timeouts
DOCKER_COMMAND_TIMEOUT = 30
QDRANT_STARTUP_TIMEOUT = config.qdrant.startup_timeout
HEALTH_CHECK_TIMEOUT = config.qdrant.health_check_timeout

# Processing Configuration
MARKDOWN_CHUNK_SIZE = config.markdown.chunk_size
MARKDOWN_CHUNK_OVERLAP = config.markdown.chunk_overlap
MARKDOWN_PROCESSING_RECURSIVE = config.markdown.recursive_processing

# AI Enhancement Configuration
AI_ENHANCEMENT_ENABLED = config.markdown.ai_enhancement_enabled
AI_ANALYSIS_DEPTH = config.markdown.ai_analysis_depth
AI_CONTENT_OPTIMIZATION = config.markdown.ai_content_optimization

# Policy Configuration
POLICY_DIRECTORY_DEFAULT = config.policy.directory
POLICY_RULE_ID_PATTERN = config.policy.rule_id_pattern
POLICY_VALIDATION_STRICT = config.policy.validation_strict
POLICY_HASH_ALGORITHM = config.policy.hash_algorithm

# Memory Configuration
MEMORY_TYPE_CONFIDENCE_THRESHOLD = config.memory.type_confidence_threshold
MEMORY_TYPE_SUGGESTION_ENABLED = config.memory.suggestion_enabled

# Deduplication Configuration
DEDUPLICATION_SIMILARITY_THRESHOLD = config.deduplication.similarity_threshold
DEDUPLICATION_NEAR_MISS_THRESHOLD = config.deduplication.near_miss_threshold
DEDUPLICATION_LOGGING_ENABLED = config.deduplication.logging_enabled
DEDUPLICATION_DIAGNOSTICS_ENABLED = config.deduplication.diagnostics_enabled

# MCP Capabilities
MCP_CAPABILITIES = {
    "tools": {
        "listChanged": False
    }
}

# MCP Server Info
MCP_SERVER_INFO = {
    "name": SERVER_NAME,
    "version": SERVER_VERSION,
    "description": SERVER_DESCRIPTION
}

# MCP Initialization Response
MCP_INIT_RESPONSE = {
    "protocolVersion": MCP_PROTOCOL_VERSION,
    "capabilities": MCP_CAPABILITIES,
    "serverInfo": MCP_SERVER_INFO
}


def setup_logging() -> logging.Logger:
    """Configure logging for the server."""
    logging.basicConfig(level=LOGGING_LEVEL, format=LOGGING_FORMAT)
    return logging.getLogger("memory-mcp-server")


def get_logger(name: str = "memory-mcp-server") -> logging.Logger:
    """Get a logger instance with the specified name."""
    return logging.getLogger(name)
