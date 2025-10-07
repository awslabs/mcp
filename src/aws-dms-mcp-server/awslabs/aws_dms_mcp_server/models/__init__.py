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

"""
Data models for AWS DMS MCP Server.

Pydantic models for type-safe data validation and serialization.
"""

from .config_models import (
    ReplicationInstanceConfig,
    EndpointConfig,
    TaskConfig,
)
from .dms_models import (
    ReplicationInstanceResponse,
    EndpointResponse,
    TaskResponse,
    TableStatistics,
    PaginationConfig,
    FilterConfig,
    OperationResponse,
    ErrorResponse,
)

__all__ = [
    # Configuration Models
    'ReplicationInstanceConfig',
    'EndpointConfig',
    'TaskConfig',
    # Response Models
    'ReplicationInstanceResponse',
    'EndpointResponse',
    'TaskResponse',
    'TableStatistics',
    # Common Models
    'PaginationConfig',
    'FilterConfig',
    'OperationResponse',
    'ErrorResponse',
]
