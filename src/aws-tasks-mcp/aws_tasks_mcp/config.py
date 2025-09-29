from __future__ import annotations

import os
from pathlib import Path

CONFIG_PATH_ENV = "AWS_TASKS_MCP_CONFIG_PATH"
CONFIG_INLINE_ENV = "AWS_TASKS_MCP_CONFIG"

FASTMCP_LOG_LEVEL = os.getenv("FASTMCP_LOG_LEVEL", "INFO").upper()

LOG_DIR: Path = Path.home() / ".aws" / "aws-tasks-mcp"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE: Path = LOG_DIR / "aws-tasks-mcp-server.log"


def default_config_path() -> Path:
    configured = os.getenv(CONFIG_PATH_ENV)
    if configured:
        return Path(configured).expanduser()
    return Path(__file__).resolve().parent / "config.json"
