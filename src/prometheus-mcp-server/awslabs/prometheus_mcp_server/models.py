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

"""Data models for the Prometheus MCP server."""

from pydantic import BaseModel, Field, field_validator
from typing import Any, List, Optional


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

    prometheus_url: str = Field(description='URL of the AWS Managed Prometheus endpoint')
    aws_region: str = Field(description='AWS region where the Prometheus service is located')
    aws_profile: Optional[str] = Field(
        None, description='AWS profile name to use for authentication (optional)'
    )
    service_name: str = Field(
        default='aps', description='AWS service name for SigV4 authentication'
    )
    retry_delay: int = Field(
        default=1, description='Delay between retry attempts in seconds', ge=1
    )
    max_retries: int = Field(
        default=3, description='Maximum number of retry attempts', ge=1, le=10
    )

    @field_validator('prometheus_url')
    def validate_prometheus_url(cls, v):
        """Validate that the Prometheus URL is properly formatted."""
        if not v:
            raise ValueError('Prometheus URL cannot be empty')

        from urllib.parse import urlparse

        parsed = urlparse(v)
        if not all([parsed.scheme, parsed.netloc]):
            raise ValueError('Prometheus URL must include scheme (https://) and hostname')

        return v


class QueryResponse(BaseModel):
    """Response from a Prometheus query.

    This model defines the structure of responses from Prometheus API queries,
    including status information and result data.

    Attributes:
        status: Status of the query ('success' or 'error').
        data: The query result data.
        error: Error message if status is 'error'.
    """

    status: str = Field(description="Status of the query ('success' or 'error')")
    data: Any = Field(description='The query result data')
    error: Optional[str] = Field(None, description="Error message if status is 'error'")


class MetricsList(BaseModel):
    """List of available metrics in Prometheus.

    Attributes:
        metrics: List of metric names available in the Prometheus server.
    """

    metrics: List[str] = Field(
        description='List of metric names available in the Prometheus server'
    )


class ServerInfo(BaseModel):
    """Information about the Prometheus server configuration.

    Attributes:
        prometheus_url: URL of the AWS Managed Prometheus endpoint.
        aws_region: AWS region where the Prometheus service is located.
        aws_profile: AWS profile name used for authentication.
        service_name: AWS service name for SigV4 authentication.
    """

    prometheus_url: str = Field(description='URL of the AWS Managed Prometheus endpoint')
    aws_region: str = Field(description='AWS region where the Prometheus service is located')
    aws_profile: str = Field(description='AWS profile name used for authentication')
    service_name: str = Field(description='AWS service name for SigV4 authentication')
