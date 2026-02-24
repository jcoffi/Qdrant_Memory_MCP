#!/usr/bin/env python3
"""Start or reuse Docker containers, then start the MCP server process.

This script is designed to be used as the MCP startup script. It ensures
required containers are running before launching the stdio server process
inside the runtime container.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


PASSTHROUGH_ENV_VARS = [
    "QDRANT_API_KEY",
    "EMBEDDING_MODEL",
    "EMBEDDING_DIMENSION",
    "SIMILARITY_THRESHOLD",
    "MAX_RESULTS",
    "DEFAULT_AGENT_ID",
    "LOG_LEVEL",
    "PROMPTS_ONLY",
    "TOOLS_ONLY",
    "UI",
    "UI_ONLY",
]

README_QDRANT_RUN_COMMAND = (
    "docker run --pull-always -p 6333:6333 "
    "-v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant"
)


@dataclass(frozen=True)
class LaunchConfig:
    image: str
    qdrant_image: str
    runtime_container: str
    qdrant_container: str
    network: str
    qdrant_port: str
    skip_qdrant_start: bool


class CommandError(RuntimeError):
    """Raised when a docker command fails."""


def run_command(
    command: List[str], check: bool = True
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise CommandError(
            f"Command failed: {' '.join(command)}\n"
            f"stdout: {result.stdout.strip()}\n"
            f"stderr: {result.stderr.strip()}"
        )
    return result


def command_succeeds(command: List[str]) -> bool:
    return subprocess.run(command, capture_output=True, text=True).returncode == 0


def ensure_docker_available() -> None:
    if shutil.which("docker") is None:
        raise CommandError("Docker is not installed or not available in PATH.")


def container_exists(name: str) -> bool:
    return command_succeeds(["docker", "inspect", name])


def container_running(name: str) -> bool:
    result = run_command(
        ["docker", "inspect", "--format", "{{.State.Running}}", name], check=False
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def network_exists(name: str) -> bool:
    return command_succeeds(["docker", "network", "inspect", name])


def image_exists(name: str) -> bool:
    return command_succeeds(["docker", "image", "inspect", name])


def ensure_network(network_name: str) -> None:
    if network_exists(network_name):
        return
    print(f"Creating Docker network '{network_name}'...", file=sys.stderr)
    run_command(["docker", "network", "create", network_name])


def ensure_image(image_name: str) -> None:
    if image_exists(image_name):
        return
    print(f"Pulling Docker image '{image_name}'...", file=sys.stderr)
    run_command(["docker", "pull", image_name])


def ensure_qdrant_container(config: LaunchConfig) -> None:
    if config.skip_qdrant_start:
        return

    if container_running(config.qdrant_container):
        return

    if container_exists(config.qdrant_container):
        print(
            f"Starting existing container '{config.qdrant_container}'...",
            file=sys.stderr,
        )
        run_command(["docker", "start", config.qdrant_container])
        return

    storage_dir = Path.cwd() / "qdrant_storage"
    storage_dir.mkdir(parents=True, exist_ok=True)

    print(
        f"Creating and starting container '{config.qdrant_container}'...",
        file=sys.stderr,
    )
    print(f"Base command: {README_QDRANT_RUN_COMMAND}", file=sys.stderr)

    run_command_with_pull_always = [
        "docker",
        "run",
        "-d",
        "--pull-always",
        "--name",
        config.qdrant_container,
        "--network",
        config.network,
        "--restart",
        "unless-stopped",
        "-p",
        f"{config.qdrant_port}:6333",
        "-p",
        "6334:6334",
        "-v",
        f"{storage_dir}:/qdrant/storage",
        config.qdrant_image,
    ]

    try:
        run_command(run_command_with_pull_always)
    except CommandError as exc:
        if "unknown flag: --pull-always" not in str(exc):
            raise

        run_command_with_pull_flag = [
            "docker",
            "run",
            "-d",
            "--pull",
            "always",
            "--name",
            config.qdrant_container,
            "--network",
            config.network,
            "--restart",
            "unless-stopped",
            "-p",
            f"{config.qdrant_port}:6333",
            "-p",
            "6334:6334",
            "-v",
            f"{storage_dir}:/qdrant/storage",
            config.qdrant_image,
        ]
        run_command(run_command_with_pull_flag)


def ensure_runtime_container(config: LaunchConfig) -> None:
    if container_running(config.runtime_container):
        return

    if container_exists(config.runtime_container):
        print(
            f"Starting existing container '{config.runtime_container}'...",
            file=sys.stderr,
        )
        run_command(["docker", "start", config.runtime_container])
        return

    ensure_image(config.image)
    print(
        f"Creating and starting container '{config.runtime_container}'...",
        file=sys.stderr,
    )
    run_command(
        [
            "docker",
            "run",
            "-d",
            "--name",
            config.runtime_container,
            "--network",
            config.network,
            "--restart",
            "unless-stopped",
            config.image,
            "sleep",
            "infinity",
        ]
    )


def build_exec_environment(config: LaunchConfig) -> Dict[str, str]:
    env: Dict[str, str] = {
        "QDRANT_HOST": os.environ.get("QDRANT_HOST", config.qdrant_container),
        "QDRANT_PORT": os.environ.get("QDRANT_PORT", "6333"),
    }

    for key in PASSTHROUGH_ENV_VARS:
        value = os.environ.get(key)
        if value:
            env[key] = value

    return env


def exec_server_process(config: LaunchConfig) -> None:
    command = ["docker", "exec", "-i"]

    for key, value in build_exec_environment(config).items():
        command.extend(["-e", f"{key}={value}"])

    command.extend([config.runtime_container, "python", "memory_server.py"])
    os.execvp("docker", command)


def parse_args() -> LaunchConfig:
    parser = argparse.ArgumentParser(
        description="Start MCP memory server in Docker with idempotent container checks."
    )
    parser.add_argument(
        "--image",
        default=os.environ.get("MCP_IMAGE", "ghcr.io/jcoffi/qdrant-memory-mcp:latest"),
        help="Runtime image that contains memory_server.py",
    )
    parser.add_argument(
        "--qdrant-image",
        default=os.environ.get("QDRANT_IMAGE", "qdrant/qdrant:latest"),
        help="Qdrant image to use when creating a local Qdrant container",
    )
    parser.add_argument(
        "--runtime-container",
        default=os.environ.get("MCP_RUNTIME_CONTAINER", "mcp-memory-runtime"),
        help="Container name for the MCP runtime",
    )
    parser.add_argument(
        "--qdrant-container",
        default=os.environ.get("QDRANT_CONTAINER", "mcp-qdrant"),
        help="Container name for Qdrant",
    )
    parser.add_argument(
        "--network",
        default=os.environ.get("MCP_DOCKER_NETWORK", "mcp-memory-net"),
        help="Docker network used by runtime and Qdrant containers",
    )
    parser.add_argument(
        "--qdrant-port",
        default=os.environ.get("QDRANT_PORT", "6333"),
        help="Host port to expose Qdrant API",
    )
    parser.add_argument(
        "--skip-qdrant-start",
        action="store_true",
        default=os.environ.get("SKIP_QDRANT_START", "").lower() in {"1", "true", "yes"},
        help="Skip starting local Qdrant container (use external Qdrant)",
    )

    args = parser.parse_args()

    return LaunchConfig(
        image=args.image,
        qdrant_image=args.qdrant_image,
        runtime_container=args.runtime_container,
        qdrant_container=args.qdrant_container,
        network=args.network,
        qdrant_port=str(args.qdrant_port),
        skip_qdrant_start=bool(args.skip_qdrant_start),
    )


def main() -> int:
    try:
        config = parse_args()
        ensure_docker_available()
        ensure_network(config.network)
        ensure_qdrant_container(config)
        ensure_runtime_container(config)
        exec_server_process(config)
        return 0
    except CommandError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
