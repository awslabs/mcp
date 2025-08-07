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

"""Pydantic models for Data Processing MCP Server."""

from mcp.types import CallToolResult
from pydantic import Field
from typing import Any, Dict, List, Optional


class ListPermissionsResponse(CallToolResult):
    """Response model for listing Lake Formation permissions."""

    permissions: List[Dict[str, Any]] = Field(..., description='A list of permissions.')
    operation: str = Field(..., description='The operation performed.')
    next_token: Optional[str] = Field(None, description='Token for pagination.')


class GetDataLakeSettingsResponse(CallToolResult):
    """Response model for getting Lake Formation data lake settings."""

    data_lake_settings: Dict[str, Any] = Field(..., description='The data lake settings.')
    operation: str = Field(..., description='The operation performed.')


class ListResourcesResponse(CallToolResult):
    """Response model for listing Lake Formation resources."""

    resources: List[Dict[str, Any]] = Field(..., description='A list of resources.')
    operation: str = Field(..., description='The operation performed.')
    next_token: Optional[str] = Field(None, description='Token for pagination.')


class DescribeResourceResponse(CallToolResult):
    """Response model for describing a Lake Formation resource."""

    resource_info: Dict[str, Any] = Field(..., description='Information about the resource.')
    operation: str = Field(..., description='The operation performed.')


class BatchGetEffectivePermissionsForPathResponse(CallToolResult):
    """Response model for batch getting effective permissions for a path."""

    permissions: List[Dict[str, Any]] = Field(..., description='A list of effective permissions.')
    operation: str = Field(..., description='The operation performed.')
