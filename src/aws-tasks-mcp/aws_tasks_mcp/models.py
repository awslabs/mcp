from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class McpErrorResponse(BaseModel):
    error: bool = True
    detail: str


ToolPayload = dict[str, Any] | McpErrorResponse

