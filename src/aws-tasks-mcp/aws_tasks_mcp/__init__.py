"""Unified AWS MCP server package."""

from typing import TYPE_CHECKING

__all__ = ["server"]

# For type checkers only (no runtime import)
if TYPE_CHECKING:
    from .server import server  # noqa: F401


def __getattr__(name: str):
    if name == "server":
        from .server import server as _server
        return _server
    raise AttributeError(name)
