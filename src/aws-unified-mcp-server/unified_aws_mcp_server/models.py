from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class UnifiedMcpErrorResponse(BaseModel):
    error: bool = True
    detail: str


ToolPayload = dict[str, Any] | UnifiedMcpErrorResponse

