from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import CONFIG_INLINE_ENV, CONFIG_PATH_ENV, default_config_path


@dataclass
class McpServerSpec:
    name: str
    transport: str
    tools: List[str]
    args: Dict[str, Any] = field(default_factory=dict)
    description: Optional[str] = None
    rename_tools: Dict[str, str] = field(default_factory=dict)


class MCPLoader:
    """Loads proxy configuration for downstream MCP servers."""

    def __init__(self, path: Optional[Path] = None, inline: Optional[str] = None) -> None:
        self.inline = inline if inline is not None else os.getenv(CONFIG_INLINE_ENV)
        if path is not None:
            self.path = path.expanduser()
        else:
            env_path = os.getenv(CONFIG_PATH_ENV)
            self.path = Path(env_path).expanduser() if env_path else default_config_path()

    def load(self) -> List[McpServerSpec]:
        raw = self._load_raw_config()
        servers = raw.get("mcp_servers") or raw.get("cameos")
        if servers is None:
            return []
        if not isinstance(servers, list):
            raise ValueError("Expected 'mcp_servers' to be a list")

        specs: List[McpServerSpec] = []
        for index, entry in enumerate(servers):
            if not isinstance(entry, dict):
                raise ValueError(f"Entry {index} in 'mcp_servers' must be an object")

            name = entry.get("name")
            transport = entry.get("type") or entry.get("transport")
            tools = entry.get("tools", [])
            args = entry.get("args", {})
            rename = entry.get("rename_tools", {})

            if not name or not isinstance(name, str):
                raise ValueError(f"Entry {index} missing 'name'")
            if not transport or not isinstance(transport, str):
                raise ValueError(f"Entry {name} missing 'type'/'transport'")
            if not isinstance(tools, list) or not all(isinstance(t, str) for t in tools):
                raise ValueError(f"Entry {name} has invalid 'tools' list")
            if not isinstance(args, dict):
                raise ValueError(f"Entry {name} has invalid 'args' section")
            if not isinstance(rename, dict):
                raise ValueError(f"Entry {name} has invalid 'rename_tools' section")

            specs.append(
                McpServerSpec(
                    name=name,
                    transport=transport,
                    tools=[tool.strip() for tool in tools if tool.strip()],
                    args=args,
                    description=entry.get("description"),
                    rename_tools={k: v for k, v in rename.items() if isinstance(k, str) and isinstance(v, str)},
                )
            )
        return specs

    def _load_raw_config(self) -> Dict[str, Any]:
        if self.inline:
            return json.loads(self.inline)
        path = self.path
        if not path.exists():
            if path.name == "config.json":
                return {}
            raise FileNotFoundError(f"Config file not found at {path}")
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
