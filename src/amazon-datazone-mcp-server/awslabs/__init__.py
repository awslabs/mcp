"""AWS DataZone MCP Server."""

import os
from pathlib import Path

# Read version from VERSION file
_version_file = Path(__file__).parent.parent.parent / "VERSION"
if _version_file.exists():
    __version__ = _version_file.read_text().strip()
else:
    __version__ = "unknown"

__all__ = ["__version__"]
