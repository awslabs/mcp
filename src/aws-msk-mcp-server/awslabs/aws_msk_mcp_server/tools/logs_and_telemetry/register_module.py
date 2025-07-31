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

"""Logs and Telemetry API Module.

This module provides functions to retrieve metrics and telemetry data for MSK clusters,
as well as a separate tool for IAM access information.
"""

from ..common_functions.client_manager import AWSClientManager
from .cluster_metrics_tools import get_cluster_metrics, list_available_metrics
from .list_customer_iam_access import list_customer_iam_access
from mcp.server.fastmcp import FastMCP
from pydantic import Field


def register_module(mcp: FastMCP) -> None:
    """Registers this tool with the mcp."""

    @mcp.tool(
        name='get_cluster_telemetry',
        description="""Access metrics and telemetry data for MSK clusters via CloudWatch

Capabilities:
- Supports cluster-level and broker-level metrics
- Compatible with both PROVISIONED and SERVERLESS clusters
- Allows querying available metrics or retrieving time-series data
- Parses metric formats including list and dict inputs with validation

=== ACTION MODES ===

1. action = "metrics"
- Retrieves time-series telemetry data for specified metrics.

Required kwargs:
    - start_time (datetime): Start timestamp for metric retrieval
    - end_time (datetime): End timestamp for metric retrieval
    - period (int): Data granularity in seconds
    - metrics (list or dict):
        Either:
        - List of metric names: ['BytesInPerSec', 'MessagesInPerSec']
        - Dict of metric name -> statistic: {'BytesInPerSec': 'Sum'}

        A list of dicts is NOT supported and will cause an "unhashable type: 'dict'" error.

Optional kwargs:
    - scan_by (str): 'TimestampAscending' | 'TimestampDescending'
    - label_options (dict): e.g., {'timezone': 'UTC'}
    - pagination_config (dict): e.g., {'PageSize': 500}

Output (JSON):
{
    "MetricDataResults": [
    {
        "Id": "string",
        "Label": "string",
        "Timestamps": ["2024-01-01T00:00:00Z"],
        "Values": [1.2],
        "StatusCode": "Complete"
    }
    ]
}

2. action = "available_metrics"
- Returns the set of available metrics based on the cluster's Enhanced Monitoring level.

No kwargs.

Output (JSON):
{
    "Metrics": ["BytesInPerSec", "MessagesInPerSec", ...],
    "MonitoringLevel": "DEFAULT" | "PER_BROKER" | "PER_TOPIC_PER_BROKER"
}

Input Schema:
region: str (required) — AWS region (e.g., 'us-west-2')
action: str (required) — 'metrics' | 'available_metrics'
cluster_arn: str (required) — ARN of the MSK cluster
kwargs: dict (optional) — See action-specific parameters above

Notes on Recommended Metrics:

PROVISIONED clusters (recommended):
- GlobalTopicCount: Indicates cluster-wide topic count.
- GlobalPartitionCount: Important for understanding broker resource usage.
- OfflinePartitionsCount: Should always be 0; >0 indicates data loss risk.
- UnderReplicatedPartitions: Alert-worthy when >0.
- ConnectionCount: Watch for large or sudden spikes.
- ActiveControllerCount: Should always be exactly 1.

BROKER-level metrics (if enabled):
- BytesInPerSec, BytesOutPerSec
- UnderReplicatedPartitions (per broker)
- LeaderCount
- ProduceTotalTimeMsMean
- FetchConsumerTotalTimeMsMean

SERVERLESS clusters:
- BytesInPerSec, BytesOutPerSec (per topic)
- FetchMessageConversionsPerSec
- MessagesInPerSec
- ProduceMessageConversionsPerSec

Related Resources:
- resource://msk-best-practices - Access comprehensive best practices and recommended thresholds
  for interpreting the metrics returned by this tool""",
    )
    def get_cluster_telemetry(
        region: str = Field(..., description='AWS region'),
        action: str = Field(
            ..., description='The operation to perform (metrics, available_metrics)'
        ),
        cluster_arn: str = Field(
            ..., description='The ARN of the cluster (required for cluster operations)'
        ),
        kwargs: dict = Field({}, description='Additional arguments based on the action type'),
    ):
        if action == 'metrics' and cluster_arn:
            # Create a client manager instance
            client_manager = AWSClientManager()

            # Extract required parameters from kwargs
            start_time = kwargs.get('start_time')
            end_time = kwargs.get('end_time')
            period = kwargs.get('period')
            metrics = kwargs.get('metrics')

            # Check if required parameters exist
            if start_time is None:
                raise ValueError('start_time is required for metrics action')
            if end_time is None:
                raise ValueError('end_time is required for metrics action')
            if period is None:
                raise ValueError('period is required for metrics action')
            if metrics is None:
                raise ValueError('metrics is required for metrics action')

            # Extract optional parameters from kwargs
            scan_by = kwargs.get('scan_by')
            label_options = kwargs.get('label_options')
            pagination_config = kwargs.get('pagination_config')

            # Pass the extracted parameters to the get_cluster_metrics function
            return get_cluster_metrics(
                region=region,
                cluster_arn=cluster_arn,
                client_manager=client_manager,
                start_time=start_time,
                end_time=end_time,
                period=period,
                metrics=metrics,
                scan_by=scan_by,
                label_options=label_options,
                pagination_config=pagination_config,
            )
        elif action == 'available_metrics':
            if cluster_arn:
                # Create a client manager instance
                client_manager = AWSClientManager()

                # Configure the client manager with the region
                kafka_client = client_manager.get_client(region, 'kafka')

                # Get cluster's monitoring level
                cluster_info = kafka_client.describe_cluster_v2(ClusterArn=cluster_arn)[
                    'ClusterInfo'
                ]
                cluster_monitoring = cluster_info.get('EnhancedMonitoring', 'DEFAULT')

                # Return metrics filtered by the cluster's monitoring level
                return list_available_metrics(monitoring_level=cluster_monitoring)
            else:
                # If no cluster ARN is provided, raise an error as monitoring level is required
                raise ValueError('Cluster ARN must be provided to determine monitoring level')
        else:
            raise ValueError(f'Unsupported action or missing required arguments for {action}')

    @mcp.tool(
        name='list_customer_iam_access',
        description="""Audit IAM access configuration and policies for an MSK cluster

This tool audits both resource-based and identity-based (IAM) policies associated with the specified MSK cluster. It helps determine whether IAM authentication is enabled and which principals have access.

=== INPUT PARAMETERS ===

- cluster_arn (str): The ARN of the target MSK cluster.
- region (str): The AWS region where the cluster is deployed.

=== OUTPUT (JSON) ===

{
"cluster_info": {
    "ClusterArn": "arn:aws:kafka:us-west-2:123456789012:cluster/my-cluster/abcd1234",
    "ClusterName": "my-cluster",
    "IamAuthEnabled": true
},
"resource_policies": [
    {
    "Version": "2012-10-17",
    "Statement": [
        {
        "Effect": "Allow",
        "Action": ["kafka:DescribeCluster"],
        "Resource": "*"
        }
    ]
    }
],
"matching_policies": [
    {
    "PolicyName": "KafkaAccessPolicy",
    "PolicyArn": "arn:aws:iam::123456789012:policy/KafkaAccessPolicy",
    "Actions": ["kafka:DescribeCluster", "kafka:Connect"]
    }
]
}

=== NOTES ===

- `resource_policies` represent policies directly attached to the cluster.
- `matching_policies` are IAM identity policies (users, roles, or groups) granting access to the cluster.
- Useful for compliance, security audits, and debugging IAM access issues.""",
    )
    def list_customer_iam_access_tool(
        region: str = Field(..., description='AWS region'),
        cluster_arn: str = Field(..., description='The ARN of the MSK cluster'),
    ):
        # Create a client manager instance
        client_manager = AWSClientManager()

        # No need to create individual clients, the list_customer_iam_access function will handle it

        # Pass the client manager to the list_customer_iam_access function
        return list_customer_iam_access(cluster_arn=cluster_arn, client_manager=client_manager)
