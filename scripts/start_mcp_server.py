#!/usr/bin/env python3
"""MCP startup script for containerized memory server.

This is the script intended to be used as the MCP command target.
It delegates to start_mcp_container.py, which ensures required
containers are running and then launches MCP stdio inside runtime.
"""

from __future__ import annotations

from pathlib import Path
import runpy
import sys


if __name__ == "__main__":
    target = Path(__file__).with_name("start_mcp_container.py")
    sys.argv[0] = str(target)
    runpy.run_path(str(target), run_name="__main__")
