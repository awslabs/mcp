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


from mcp.types import CallToolResult
from pydantic import Field
from typing import Any, Dict, List, Optional


class CreateCrawlerResponse(CallToolResult):
    """Response model for create crawler operation."""

    crawler_name: str = Field(..., description='Name of the created crawler')
    operation: str = Field(default='create', description='Operation performed')


class DeleteCrawlerResponse(CallToolResult):
    """Response model for delete crawler operation."""

    crawler_name: str = Field(..., description='Name of the deleted crawler')
    operation: str = Field(default='delete', description='Operation performed')


class GetCrawlerResponse(CallToolResult):
    """Response model for get crawler operation."""

    crawler_name: str = Field(..., description='Name of the crawler')
    crawler_details: Dict[str, Any] = Field(..., description='Complete crawler definition')
    operation: str = Field(default='get', description='Operation performed')


class GetCrawlersResponse(CallToolResult):
    """Response model for get crawlers operation."""

    crawlers: List[Dict[str, Any]] = Field(..., description='List of crawlers')
    count: int = Field(..., description='Number of crawlers found')
    next_token: Optional[str] = Field(None, description='Token for pagination')
    operation: str = Field(default='list', description='Operation performed')


class StartCrawlerResponse(CallToolResult):
    """Response model for start crawler operation."""

    crawler_name: str = Field(..., description='Name of the crawler')
    operation: str = Field(default='start', description='Operation performed')


class StopCrawlerResponse(CallToolResult):
    """Response model for stop crawler operation."""

    crawler_name: str = Field(..., description='Name of the crawler')
    operation: str = Field(default='stop', description='Operation performed')


class GetCrawlerMetricsResponse(CallToolResult):
    """Response model for get crawler metrics operation."""

    crawler_metrics: List[Dict[str, Any]] = Field(..., description='List of crawler metrics')
    count: int = Field(..., description='Number of crawler metrics found')
    next_token: Optional[str] = Field(None, description='Token for pagination')
    operation: str = Field(default='get_metrics', description='Operation performed')


class StartCrawlerScheduleResponse(CallToolResult):
    """Response model for start crawler schedule operation."""

    crawler_name: str = Field(..., description='Name of the crawler')
    operation: str = Field(default='start_schedule', description='Operation performed')


class StopCrawlerScheduleResponse(CallToolResult):
    """Response model for stop crawler schedule operation."""

    crawler_name: str = Field(..., description='Name of the crawler')
    operation: str = Field(default='stop_schedule', description='Operation performed')


class BatchGetCrawlersResponse(CallToolResult):
    """Response model for batch get crawlers operation."""

    crawlers: List[Any] = Field(..., description='List of crawlers')
    crawlers_not_found: List[str] = Field(..., description='List of crawler names not found')
    operation: str = Field(default='batch_get', description='Operation performed')


class ListCrawlersResponse(CallToolResult):
    """Response model for list crawlers operation."""

    crawlers: List[Any] = Field(..., description='List of crawlers')
    count: int = Field(..., description='Number of crawlers found')
    next_token: Optional[str] = Field(None, description='Token for pagination')
    operation: str = Field(default='list', description='Operation performed')


class UpdateCrawlerResponse(CallToolResult):
    """Response model for update crawler operation."""

    crawler_name: str = Field(..., description='Name of the updated crawler')
    operation: str = Field(default='update', description='Operation performed')


class UpdateCrawlerScheduleResponse(CallToolResult):
    """Response model for update crawler schedule operation."""

    crawler_name: str = Field(..., description='Name of the crawler')
    operation: str = Field(default='update_schedule', description='Operation performed')


# Response models for Classifiers
class CreateClassifierResponse(CallToolResult):
    """Response model for create classifier operation."""

    classifier_name: str = Field(..., description='Name of the created classifier')
    operation: str = Field(default='create', description='Operation performed')


class DeleteClassifierResponse(CallToolResult):
    """Response model for delete classifier operation."""

    classifier_name: str = Field(..., description='Name of the deleted classifier')
    operation: str = Field(default='delete', description='Operation performed')


class GetClassifierResponse(CallToolResult):
    """Response model for get classifier operation."""

    classifier_name: str = Field(..., description='Name of the classifier')
    classifier_details: Dict[str, Any] = Field(..., description='Complete classifier definition')
    operation: str = Field(default='get', description='Operation performed')


class GetClassifiersResponse(CallToolResult):
    """Response model for get classifiers operation."""

    classifiers: List[Dict[str, Any]] = Field(..., description='List of classifiers')
    count: int = Field(..., description='Number of classifiers found')
    next_token: Optional[str] = Field(None, description='Token for pagination')
    operation: str = Field(default='list', description='Operation performed')


class UpdateClassifierResponse(CallToolResult):
    """Response model for update classifier operation."""

    classifier_name: str = Field(..., description='Name of the updated classifier')
    operation: str = Field(default='update', description='Operation performed')
