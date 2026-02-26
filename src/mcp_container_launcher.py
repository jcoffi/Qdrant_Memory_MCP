"""uvx entrypoint for MCP startup with single Qdrant container management."""

from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from src.mcp_server import run_mcp_server


README_QDRANT_RUN_COMMAND = (
    "docker run --pull-always -p 6333:6333 "
    "-v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant:1.16"
)


@dataclass(frozen=True)
class LaunchConfig:
    qdrant_image: str
    qdrant_container: str
    qdrant_port: str
    qdrant_storage_dir: str
    skip_qdrant_start: bool
    server_mode: str


class CommandError(RuntimeError):
    """Raised when a docker command fails."""


def run_command(
    command: list[str], check: bool = True
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise CommandError(
            f"Command failed: {' '.join(command)}\n"
            f"stdout: {result.stdout.strip()}\n"
            f"stderr: {result.stderr.strip()}"
        )
    return result


def command_succeeds(command: list[str]) -> bool:
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


def _run_qdrant_container(config: LaunchConfig, pull_always_style: str) -> None:
    storage_dir = Path(config.qdrant_storage_dir).resolve()
    storage_dir.mkdir(parents=True, exist_ok=True)

    command = [
        "docker",
        "run",
        "-d",
        "--name",
        config.qdrant_container,
        "-p",
        f"{config.qdrant_port}:6333",
        "-v",
        f"{storage_dir}:/qdrant/storage",
    ]

    if pull_always_style == "pull-always":
        command.append("--pull-always")
    else:
        command.extend(["--pull", "always"])

    command.append(config.qdrant_image)
    run_command(command)


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

    print(
        f"Creating and starting container '{config.qdrant_container}'...",
        file=sys.stderr,
    )
    print(f"Base command: {README_QDRANT_RUN_COMMAND}", file=sys.stderr)

    try:
        _run_qdrant_container(config, pull_always_style="pull-always")
    except CommandError as exc:
        error_text = str(exc)
        if "unknown flag: --pull-always" in error_text:
            _run_qdrant_container(config, pull_always_style="pull")
            return
        if "is already in use by container" in error_text:
            run_command(["docker", "start", config.qdrant_container], check=False)
            return
        raise


def resolve_server_mode() -> str:
    prompts_only = os.environ.get("PROMPTS_ONLY", "").lower() in {"1", "true", "yes"}
    tools_only = os.environ.get("TOOLS_ONLY", "").lower() in {"1", "true", "yes"}
    if prompts_only:
        return "prompts-only"
    if tools_only:
        return "tools-only"
    return "full"


def parse_args() -> LaunchConfig:
    parser = argparse.ArgumentParser(
        description="Start MCP server via uvx and ensure a single Qdrant container."
    )
    parser.add_argument(
        "--qdrant-image",
        default=os.environ.get("QDRANT_IMAGE", "qdrant/qdrant:1.16"),
        help="Qdrant image to use when creating the local Qdrant container",
    )
    parser.add_argument(
        "--qdrant-container",
        default=os.environ.get("QDRANT_CONTAINER", "mcp-qdrant"),
        help="Container name for Qdrant",
    )
    parser.add_argument(
        "--qdrant-port",
        default=os.environ.get("QDRANT_PORT", "6333"),
        help="Host port to expose Qdrant API",
    )
    parser.add_argument(
        "--qdrant-storage-dir",
        default=os.environ.get(
            "QDRANT_STORAGE_DIR", str(Path.cwd() / "qdrant_storage")
        ),
        help="Host path used for Qdrant storage bind mount",
    )
    parser.add_argument(
        "--skip-qdrant-start",
        action="store_true",
        default=os.environ.get("SKIP_QDRANT_START", "").lower() in {"1", "true", "yes"},
        help="Skip starting local Qdrant container and use external Qdrant",
    )
    parser.add_argument(
        "--mode",
        choices=["full", "prompts-only", "tools-only"],
        default=resolve_server_mode(),
        help="Server mode for MCP capabilities",
    )
    args = parser.parse_args()

    return LaunchConfig(
        qdrant_image=args.qdrant_image,
        qdrant_container=args.qdrant_container,
        qdrant_port=str(args.qdrant_port),
        qdrant_storage_dir=args.qdrant_storage_dir,
        skip_qdrant_start=bool(args.skip_qdrant_start),
        server_mode=args.mode,
    )


def main() -> int:
    try:
        config = parse_args()
        ensure_docker_available()
        ensure_qdrant_container(config)
        os.environ.setdefault("QDRANT_HOST", "localhost")
        os.environ.setdefault("QDRANT_PORT", config.qdrant_port)
        asyncio.run(run_mcp_server(config.server_mode))
        return 0
    except CommandError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
