# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the \"License\"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""Data models for the Prometheus MCP server."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PrometheusConfig(BaseModel):
    """Configuration for the Prometheus MCP server.
    
    This model defines the parameters that control the connection to AWS Managed Prometheus,
    including authentication and retry settings.
    
    Attributes:
        prometheus_url: URL of the AWS Managed Prometheus endpoint.
        aws_region: AWS region where the Prometheus service is located.
        aws_profile: AWS profile name to use for authentication (optional).
        service_name: AWS service name for SigV4 authentication (default: 'aps').
        retry_delay: Delay between retry attempts in seconds (default: 1).
        max_retries: Maximum number of retry attempts (default: 3).
    """
    
    prometheus_url: str
    aws_region: str
    aws_profile: Optional[str] = None
    service_name: str = Field(default='aps')
    retry_delay: int = Field(default=1)
    max_retries: int = Field(default=3)


class QueryResponse(BaseModel):
    """Response from a Prometheus query.
    
    Attributes:
        status: Status of the query ('success' or 'error').
        data: The query result data.
        error: Error message if status is 'error'.
    """
    
    status: str
    data: Any
    error: Optional[str] = None