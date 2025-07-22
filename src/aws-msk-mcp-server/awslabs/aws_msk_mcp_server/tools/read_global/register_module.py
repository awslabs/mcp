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

"""Global Information API Module.

This module provides functions to retrieve global information about MSK resources.
"""

import boto3
from .list_clusters import list_clusters
from .list_configurations import list_configurations
from .list_kafka_versions import list_kafka_versions
from .list_vpc_connections import list_vpc_connections
from awslabs.aws_msk_mcp_server import __version__
from botocore.config import Config
from mcp.server.fastmcp import FastMCP
from pydantic import Field


def register_module(mcp: FastMCP) -> None:
    """Registers this tool with the mcp."""

    @mcp.tool(name='get_global_info')
    def get_global_info(
        region: str = Field(..., description='AWS region'),
        info_type: str = Field(
            'all',
            description='Type of information to retrieve (clusters, configurations, vpc_connections, kafka_versions, all)',
        ),
        kwargs: dict = Field({}, description='Additional arguments specific to each info type'),
    ):
        """Unified API to retrieve various types of global information about MSK resources.

        This operation provides a comprehensive view of MSK resources across your AWS account in a specified region.

        === ACTION MODES ===

        1. info_type = "clusters"
        - Retrieves information about all MSK clusters in the region.

        Required parameters:
        - region (str): AWS region. Ask for this if not yet in context

        Optional parameters:
        - cluster_name_filter (str): Filter clusters by name
        - cluster_type_filter (str): Filter clusters by type (PROVISIONED or SERVERLESS)
        - max_results (int): Maximum number of clusters to return (default: 10)
        - next_token (str): Token for pagination

        Output (JSON):
        {
            "ClusterInfoList": [
                {
                    "ClusterArn": "arn:aws:kafka:us-west-2:123456789012:cluster/cluster-name/abcd1234",
                    "ClusterName": "cluster-name",
                    "ClusterType": "PROVISIONED",
                    "State": "ACTIVE",
                    "CreationTime": "2023-01-01T12:00:00.000Z"
                }
            ],
            "NextToken": "AAAABBBCCC"
        }

        2. info_type = "configurations"
        - Retrieves information about all MSK configurations in the region.

        Required parameters:
        - region (str): AWS region

        Optional parameters:
        - max_results (int): Maximum number of configurations to return (default: 10)
        - next_token (str): Token for pagination

        Output (JSON):
        {
            "ConfigurationInfoList": [
                {
                    "Arn": "arn:aws:kafka:us-west-2:123456789012:configuration/configuration-name/abcd1234",
                    "Name": "configuration-name",
                    "CreationTime": "2023-01-01T12:00:00.000Z"
                }
            ],
            "NextToken": "AAAABBBCCC"
        }

        3. info_type = "vpc_connections"
        - Retrieves information about all VPC connections in the region.

        Required parameters:
        - region (str): AWS region

        Optional parameters:
        - max_results (int): Maximum number of VPC connections to return (default: 10)
        - next_token (str): Token for pagination

        Output (JSON):
        {
            "VpcConnectionInfoList": [
                {
                    "VpcConnectionArn": "arn:aws:kafka:us-west-2:123456789012:vpc-connection/connection-id",
                    "VpcConnectionState": "ACTIVE",
                    "CreationTime": "2023-01-01T12:00:00.000Z"
                }
            ],
            "NextToken": "AAAABBBCCC"
        }

        4. info_type = "kafka_versions"
        - Retrieves information about all available Kafka versions.

        Required parameters:
        - region (str): AWS region

        Output (JSON):
        {
            "KafkaVersions": [
                "2.8.1",
                "3.3.1"
            ]
        }

        5. info_type = "all"
        - Retrieves all of the above information in a single call.

        Required parameters:
        - region (str): AWS region

        Optional parameters:
        - cluster_name_filter (str): Filter clusters by name
        - cluster_type_filter (str): Filter clusters by type
        - max_results (int): Maximum number of items to return per category (default: 10)
        - next_token (str): Token for pagination

        Output (JSON):
        {
            "clusters": { /* clusters response */ },
            "configurations": { /* configurations response */ },
            "vpc_connections": { /* vpc_connections response */ },
            "kafka_versions": { /* kafka_versions response */ }
        }

        === NOTES ===

        - This tool provides a convenient way to get a comprehensive view of MSK resources in a region.
        - For accounts with many resources, use pagination parameters to retrieve all results.
        - The cluster_type_filter parameter can be used to filter for PROVISIONED or SERVERLESS clusters.
        - The response structure varies based on the info_type requested.
        """
        # Create a single boto3 client to be shared across all function calls
        client = boto3.client(
            'kafka',
            region_name=region,
            config=Config(user_agent_extra=f'awslabs/mcp/aws-msk-mcp-server/{__version__}'),
        )

        if info_type == 'all':
            # Retrieve all types of information
            result = {
                'clusters': list_clusters(
                    client,
                    cluster_name_filter=kwargs.get('cluster_name_filter'),
                    cluster_type_filter=kwargs.get('cluster_type_filter'),
                    max_results=kwargs.get('max_results', 10),
                    next_token=kwargs.get('next_token'),
                ),
                'configurations': list_configurations(
                    client,
                    max_results=kwargs.get('max_results', 10),
                    next_token=kwargs.get('next_token'),
                ),
                'vpc_connections': list_vpc_connections(
                    client,
                    max_results=kwargs.get('max_results', 10),
                    next_token=kwargs.get('next_token'),
                ),
                'kafka_versions': list_kafka_versions(client),
            }
            return result
        elif info_type == 'clusters':
            cluster_name_filter = kwargs.get('cluster_name_filter')
            cluster_type_filter = kwargs.get('cluster_type_filter')
            max_results = kwargs.get('max_results', 10)
            next_token = kwargs.get('next_token')

            return list_clusters(
                client,
                cluster_name_filter=cluster_name_filter,
                cluster_type_filter=cluster_type_filter,
                max_results=max_results,
                next_token=next_token,
            )
        elif info_type == 'configurations':
            max_results = kwargs.get('max_results', 10)
            next_token = kwargs.get('next_token')

            return list_configurations(client, max_results=max_results, next_token=next_token)
        elif info_type == 'vpc_connections':
            max_results = kwargs.get('max_results', 10)
            next_token = kwargs.get('next_token')

            return list_vpc_connections(client, max_results=max_results, next_token=next_token)
        elif info_type == 'kafka_versions':
            return list_kafka_versions(client)
        else:
            raise ValueError(f'Unsupported info_type: {info_type}')
