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

from pydantic import BaseModel, Field
from typing import List, Optional


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

    prometheus_url: Optional[str] = Field(
        None, description='URL of the AWS Managed Prometheus endpoint'
    )
    aws_region: str = Field(description='AWS region where the Prometheus service is located')
    aws_profile: Optional[str] = Field(
        None, description='AWS profile name used for authentication'
    )
    service_name: str = Field(description='AWS service name for SigV4 authentication')
