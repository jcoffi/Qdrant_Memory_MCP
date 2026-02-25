#!/usr/bin/env python3
"""Local wrapper that runs the uvx MCP launcher module from source checkout."""

from __future__ import annotations

from pathlib import Path
import sys


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))
    from src.mcp_container_launcher import main

    raise SystemExit(main())
