"""Data models for AWS Documentation MCP Server."""

from pydantic import BaseModel
from typing import Optional


class SearchResult(BaseModel):
    """Search result from AWS documentation search."""

    rank_order: int
    url: str
    title: str
    context: Optional[str] = None


class RecommendationResult(BaseModel):
    """Recommendation result from AWS documentation."""

    url: str
    title: str
    context: Optional[str] = None
