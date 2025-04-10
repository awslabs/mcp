# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
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
