# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Data models for AWS Documentation MCP Server."""

from pydantic import BaseModel, ConfigDict, Field
from typing import Dict, List, Optional


class DiscoveredService(BaseModel):
    """AWS service inferred from the query that may be relevant beyond the top results."""

    name: str
    description: Optional[str] = None


class RelatedTaskUrl(BaseModel):
    """Doc URL associated with a related task."""

    url_name: str
    url_description: Optional[str] = None


class RelatedTask(BaseModel):
    """Related operation or workflow with its own doc URLs."""

    name: str
    description: Optional[str] = None
    urls: Optional[List[RelatedTaskUrl]] = None


class Relationship(BaseModel):
    """Named connection between concepts surfaced alongside search results."""

    relation: Optional[str] = None
    to: Optional[str] = None
    to_description: Optional[str] = None
    from_: Optional[str] = Field(default=None, alias='from')

    model_config = ConfigDict(populate_by_name=True)


class ResponseMetadata(BaseModel):
    """Optional response-level metadata surfaced alongside search results."""

    discovered_services: Optional[List[DiscoveredService]] = None
    related_tasks: Optional[List[RelatedTask]] = None
    relationships: Optional[List[Relationship]] = None


class AdditionalUrl(BaseModel):
    """Doc URL related to a search result, with section anchors for citation."""

    url: str
    section_title: Optional[str] = None
    section_anchor: Optional[str] = None


class SearchResultMetadata(BaseModel):
    """Optional per-result metadata surfaced alongside an individual search result."""

    additional_urls: Optional[List[AdditionalUrl]] = None


class SearchResult(BaseModel):
    """Search result from AWS documentation search."""

    rank_order: int
    url: str
    title: str
    context: Optional[str] = None
    recommended_sections: Optional[List[str]] = None
    sections: Optional[List[str]] = None
    metadata: Optional[SearchResultMetadata] = None


class SearchResponse(BaseModel):
    """Complete search response including results and facets."""

    search_results: List[SearchResult]
    facets: Optional[Dict[str, List[str]]] = None
    query_id: str
    metadata: Optional[ResponseMetadata] = None


class RecommendationResult(BaseModel):
    """Recommendation result from AWS documentation."""

    url: str
    title: str
    context: Optional[str] = None
