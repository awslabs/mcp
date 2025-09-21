from __future__ import annotations

import os
import shlex
from pathlib import Path


def _split_command(value: str) -> tuple[str, ...]:
    return tuple(shlex.split(value)) if value else tuple()


API_MCP_COMMAND: str = os.getenv("API_MCP_COMMAND", "python3")
API_MCP_ARGS: tuple[str, ...] = _split_command(
    os.getenv("API_MCP_ARGS", "-m awslabs.aws_api_mcp_server.server")
)


def _knowledge_url() -> str:
    base = os.getenv("KNOWLEDGE_MCP_BASE_URL")
    return os.getenv("KNOWLEDGE_MCP_URL", base or "https://knowledge-mcp.global.api.aws")


KNOWLEDGE_MCP_URL: str = _knowledge_url()

FASTMCP_LOG_LEVEL: str = os.getenv("FASTMCP_LOG_LEVEL", "INFO").upper()


LOG_DIR: Path = Path.home() / ".aws" / "aws-unified-mcp"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE: Path = LOG_DIR / "aws-unified-mcp-server.log"
MODULE_PATH: Path = Path(__file__).resolve().parent
PROJECT_ROOT: Path = MODULE_PATH.parent
SRC_ROOT: Path = PROJECT_ROOT.parent
REPO_ROOT: Path = SRC_ROOT.parent
STUB_PATH: Path = MODULE_PATH / "stubs"


def api_environment() -> dict[str, str]:
    uv_cache = os.getenv("UV_CACHE_DIR") or str(LOG_DIR / "uv-cache")
    Path(uv_cache).mkdir(parents=True, exist_ok=True)
    combined_python_path = [str(STUB_PATH), str(PROJECT_ROOT), str(SRC_ROOT), str(REPO_ROOT)]
    python_path_env = os.getenv("PYTHONPATH")
    if python_path_env:
        combined_python_path.append(python_path_env)

    env: dict[str, str] = {
        "AWS_REGION": os.getenv("AWS_REGION", "us-east-1"),
        "AWS_API_MCP_WORKING_DIR": os.getenv(
            "AWS_API_MCP_WORKING_DIR", str(Path.home() / ".aws" / "aws-api-mcp" / "work")
        ),
        "AWS_API_MCP_READ_ONLY": os.getenv("AWS_API_MCP_READ_ONLY", "true"),
        "AWS_API_MCP_REQUIRE_MUTATION_CONSENT": os.getenv(
            "AWS_API_MCP_REQUIRE_MUTATION_CONSENT", "true"
        ),
        "AWS_API_MCP_DISABLE_KNOWLEDGE_BASE": os.getenv(
            "AWS_API_MCP_DISABLE_KNOWLEDGE_BASE", "true"
        ),
        "UV_CACHE_DIR": uv_cache,
        "UV_NO_SYNC": os.getenv("UV_NO_SYNC", "1"),
        "PYTHONPATH": os.pathsep.join(combined_python_path),
    }
    return env
