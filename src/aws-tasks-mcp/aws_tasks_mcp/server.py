from __future__ import annotations

import logging
import os
import re
import shlex
import sys
from logging.handlers import RotatingFileHandler
from typing import Dict, Iterable, List

from fastmcp import FastMCP

from .config import FASTMCP_LOG_LEVEL, LOG_FILE
from .loader import MCPLoader, McpServerSpec

logger = logging.getLogger("aws_tasks_mcp")
log_level = getattr(logging, FASTMCP_LOG_LEVEL, logging.INFO)
logger.setLevel(log_level)
logger.propagate = False
if not logger.handlers:
    stream_handler = logging.StreamHandler(stream=sys.stderr)
    stream_handler.setLevel(log_level)

    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=7)
    file_handler.setLevel(log_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    stream_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)

# Ensure proxy support exists
if not hasattr(FastMCP, "as_proxy"):
    raise RuntimeError(
        "The installed fastmcp package does not expose FastMCP.as_proxy. "
        "Upgrade fastmcp to a build that supports proxy registration."
    )

FORWARDED_PREFIXES: tuple[str, ...] = ("AWS_",)
EXPLICIT_ENV_KEYS: set[str] = {"AWS_REGION"}

def _normalise_args(raw: Iterable[str] | str | None) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return shlex.split(raw)
    return [str(item) for item in raw]

def _build_env(overrides: Dict[str, str]) -> Dict[str, str]:
    env: Dict[str, str] = {}
    for key, value in os.environ.items():
        if key in EXPLICIT_ENV_KEYS or key.startswith(FORWARDED_PREFIXES):
            env[key] = value
    env.setdefault("AWS_REGION", "us-east-1")
    env.update({str(k): str(v) for k, v in overrides.items()})
    return env

_SAFE_RE = re.compile(r"[^a-zA-Z0-9_-]")
def _safe_id(name: str) -> str:
    """Make a safe mount id matching ^[a-zA-Z0-9_-]{1,64}$."""
    safe = _SAFE_RE.sub("_", name or "proxy")
    return safe[:64] or "proxy"

def _to_config_entry(spec: McpServerSpec) -> Dict[str, object]:
    """Convert one loader spec into an MCP config entry for FastMCP.as_proxy()."""
    transport = (spec.transport or "").lower()

    if transport == "stdio":
        cmd = spec.args.get("command")
        if not cmd:
            raise ValueError(f"'{spec.name}' stdio config requires a 'command' entry")
        cmd_args = _normalise_args(spec.args.get("args"))
        extra_env = spec.args.get("env", {}) or {}
        if not isinstance(extra_env, dict):
            raise ValueError(f"'{spec.name}' stdio config 'env' must be an object")

        return {
            "transport": "stdio",
            "command": cmd,
            "args": cmd_args,
            "env": _build_env({str(k): str(v) for k, v in extra_env.items()}),
        }

    if transport in {"streamable-http", "http"}:
        url = spec.args.get("urls") or spec.args.get("url")
        if isinstance(url, list):
            url = url[0] if url else None
        if not url or not isinstance(url, str):
            raise ValueError(f"'{spec.name}' streamable-http config requires a 'urls' or 'url' entry")
        return {"transport": "http", "url": url}

    raise ValueError(f"Unsupported transport '{spec.transport}' for '{spec.name}'")

def main() -> None:
    logger.info("AWS Tasks MCP starting up")

    loader = MCPLoader()
    try:
        specs = loader.load()
    except Exception as exc:
        logger.error("Failed to load MCP configuration: %s", exc)
        raise

    if not specs:
        logger.warning("No MCP servers configured; nothing will be proxied")

    mcp_servers: Dict[str, Dict[str, object]] = {}
    for spec in specs:
        alias = _safe_id(spec.name)
        if alias != spec.name:
            logger.info("Mount '%s' -> '%s' (sanitized for tool name rules)", spec.name, alias)
        entry = _to_config_entry(spec)
        mcp_servers[alias] = entry
        logger.info("Prepared proxy entry for %s (%s)", alias, entry.get("transport"))

    config = {"mcpServers": mcp_servers}

    proxy_server = FastMCP.as_proxy(config, name="aws-tasks-mcp")
    proxy_server.run()

if __name__ == "__main__":
    main()