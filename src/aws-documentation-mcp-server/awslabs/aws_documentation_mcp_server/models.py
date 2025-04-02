"""Data models for AWS Documentation MCP Server."""

import re
from pydantic import AnyUrl, BaseModel, Field, field_validator
from typing import Annotated, Any, Optional, Union


class ReadDocumentationParams(BaseModel):
    """Parameters for reading AWS documentation."""

    url: Annotated[
        Union[AnyUrl, str], Field(description='URL of the AWS documentation page to read')
    ]
    max_length: Annotated[
        int,
        Field(
            default=5000,
            description='Maximum number of characters to return.',
            gt=0,
            lt=1000000,
        ),
    ]
    start_index: Annotated[
        int,
        Field(
            default=0,
            description='On return output starting at this character index, useful if a previous fetch was truncated and more content is required.',
            ge=0,
        ),
    ]

    @field_validator('url')
    @classmethod
    def validate_aws_docs_url(cls, v: Any) -> Any:
        """Validate that URL is from docs.aws.amazon.com and ends with .html."""
        url_str = str(v)
        if not re.match(r'^https?://docs\.aws\.amazon\.com/', url_str):
            raise ValueError('URL must be from the docs.aws.amazon.com domain')
        if not url_str.endswith('.html'):
            raise ValueError('URL must end with .html')
        return v


class SearchDocumentationParams(BaseModel):
    """Parameters for searching AWS documentation."""

    search_phrase: Annotated[str, Field(description='Search phrase to use')]
    limit: Annotated[
        int,
        Field(
            default=10,
            description='Maximum number of results to return',
            ge=1,
            le=50,
        ),
    ]


class RecommendParams(BaseModel):
    """Parameters for getting content recommendations."""

    url: Annotated[
        Union[AnyUrl, str],
        Field(description='URL of the AWS documentation page to get recommendations for'),
    ]


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
