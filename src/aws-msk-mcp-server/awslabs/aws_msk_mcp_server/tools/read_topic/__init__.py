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

"""Topic Information API Module

Provides topic-related tools for the MSK MCP server.
"""

import boto3
from botocore.config import Config
from awslabs.aws_msk_mcp_server import __version__
try:
    from mcp.server.fastmcp import FastMCP
except Exception:  # pragma: no cover - allow imports in lightweight test envs
    FastMCP = None
from pydantic import Field

from .list_topics import list_topics
from .describe_topic import describe_topic
from .describe_topic_partitions import describe_topic_partitions


def register_module(mcp: FastMCP) -> None:
    @mcp.tool(name='get_topic_info', description='Gets topic information for a cluster')
    def get_topic_info(
        region: str = Field(..., description='AWS region'),
        cluster_arn: str = Field(..., description='The ARN of the cluster'),
        action: str = Field('list', description="Action: 'list' | 'describe' | 'partitions'"),
        topic_name: str = Field(None, description='Topic name (required for describe/partitions)'),
        kwargs: dict = Field({}, description='Additional args for pagination'),
    ):
        client = boto3.client(
            'kafka',
            region_name=region,
            config=Config(user_agent_extra=f'awslabs/mcp/aws-msk-mcp-server/{__version__}'),
        )

        if action == 'list':
            max_results = kwargs.get('max_results', 10)
            next_token = kwargs.get('next_token', None)
            return list_topics(cluster_arn, client, max_results, next_token)
        if action == 'describe':
            if not topic_name:
                raise ValueError('topic_name is required for describe action')
            return describe_topic(cluster_arn, topic_name, client)
        if action == 'partitions':
            if not topic_name:
                raise ValueError('topic_name is required for partitions action')
            max_results = kwargs.get('max_results', 10)
            next_token = kwargs.get('next_token', None)
            return describe_topic_partitions(cluster_arn, topic_name, client, max_results, next_token)
