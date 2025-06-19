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
Logs and Telemetry API Module

This module provides functions to retrieve metrics and telemetry data for MSK clusters,
as well as a separate tool for IAM access information.
"""

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ..common_functions.client_manager import AWSClientManager
from .cluster_metrics_tools import get_cluster_metrics, list_available_metrics
from .list_customer_iam_access import list_customer_iam_access


def register_module(mcp: FastMCP) -> None:
    @mcp.tool(name='get_cluster_telemetry')
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
        """
        Unified API to retrieve telemetry data for MSK clusters. Current implementation of metrics uses a static table of available metrics.
        Would be better to have a resource to pull this data from and force read it first.

        Args:
            action (str): The operation to perform (metrics, available_metrics)
            cluster_arn (str): The ARN of the cluster (required for cluster operations)
            region (str): AWS region
            kwargs (dict): Additional arguments based on the action type:
                For "metrics" action (ALL of these parameters are REQUIRED):
                    start_time (datetime): Start time for metric data retrieval
                    end_time (datetime): End time for metric data retrieval
                    period (int): The granularity, in seconds, of the returned data points
                    metrics (list or dict): REQUIRED. Must be one of:
                        - List of metric names (e.g., ['BytesInPerSec', 'BytesOutPerSec'])
                        - Dictionary mapping metric names to optional statistics
                          (e.g., {'BytesInPerSec': 'Sum', 'BytesOutPerSec': 'Average'})

                        The function will validate that metrics is provided and raise an error if missing.
                        If you're unsure which metrics to include, consider using these recommended cluster-level metrics:

                          **Why these metrics are important:**
                          - **Total Topics (GlobalTopicCount):** Number of topics in the cluster. A rapidly growing topic count can increase metadata overhead and memory usage on brokers. It's useful for capacity planning; extremely large numbers of topics (hundreds or thousands) may impact controller performance.
                          - **Total Partitions (GlobalPartitionCount):** Total count of partitions across all topics. This correlates with broker load (each partition uses memory and file handles). Very high partition counts can strain the cluster (e.g., controller has to manage more metadata, more replication tasks).
                          - **Offline Partitions Count:** Number of partitions without an active leader. This should be 0 in a healthy cluster. A non-zero value means some data is unavailable (likely due to broker failure or insufficient replication). Immediate investigation is needed if >0.
                          - **Under-Replicated Partitions:** Partitions where the replication factor is not currently met (one or more replicas are out of sync). Normally 0. If >0, the cluster is vulnerable to data loss until replicas catch up. Persistent under-replicated partitions indicate a broker down or slow, or network issues hindering replication.
                          - **Connection Count:** Total active connections to brokers (client + inter-broker). Indicates client load. A very high connection count (e.g., thousands of clients) can stress broker networking and memory (each connection uses file descriptors/threads). Monitoring this helps detect surges or leaks in client connections.
                          - **Active Controller Count:** Number of active controllers in the cluster (should be 1). Kafka's controller broker handles admin tasks; there must be exactly one. A value other than 1 indicates an issue (0 means no controller - cluster not operational; >1 is unexpected under normal conditions and could imply a split-brain or ongoing controller election).

                          And these broker-level metrics if per-broker monitoring is enabled:
                          - **BytesInPerSec & BytesOutPerSec:** These measure the incoming and outgoing traffic handled by each broker. They indicate load distribution — if one broker is handling significantly more bytes, it may be doing more work (perhaps hosting more partition leaders or a heavy-topic). High throughput values approach the network or disk I/O limits of the broker's instance.
                          - **UnderReplicatedPartitions:** Per-broker count of partitions for which this broker (as leader) has followers that are not fully caught up. If non-zero on a broker, the partitions it leads are not meeting the replication factor (some follower brokers lagging or down). Ideally 0 for all brokers; a non-zero on any broker is a sign that replication is falling behind for partitions on that broker.
                          - **LeaderCount:** Number of partition leaders on this broker. This shows how partition leadership is distributed. In a balanced cluster, each broker has a similar leader count. If one broker's leader count is much higher, that broker carries more responsibility (all client reads/writes for those partitions go through it). Imbalances can lead to hotspots.
                          - **ProduceTotalTimeMsMean:** The mean time in ms to handle produce (write) requests on this broker. This is an average end-to-end latency for producers interacting with the broker. Higher values mean clients are experiencing slower acknowledgments. It can increase if the broker is overloaded (CPU, I/O) or if there are disk flush bottlenecks.
                          - **FetchConsumerTotalTimeMsMean:** The mean time in ms for consumer fetch requests on this broker. Similarly, it reflects how responsive the broker is to consumer reads. If this climbs, consumers may see increased lag or slower deliveries. Causes include high load, I/O bottlenecks, or network saturation affecting that broker.
                    scan_by (str, optional): Scan order for data points ('TimestampDescending' or 'TimestampAscending')
                    label_options (dict, optional): Dictionary containing label options:
                        - timezone: Timezone for labels (e.g., 'UTC', 'US/Pacific')
                    pagination_config (dict, optional): Dictionary containing pagination settings:
                        - MaxItems: Maximum number of items to return
                        - PageSize: Number of items per page
                        - StartingToken: Token for starting position

        Returns:
            dict: Result of the requested operation:
                - For "metrics" action:
                    - MetricDataResults (list): List of metric data results, each containing:
                        - Id (str): The ID of the metric
                        - Label (str): The label of the metric
                        - Timestamps (list): List of timestamps for the data points
                        - Values (list): List of values for the data points
                        - StatusCode (str): The status code of the metric data

                    **How to interpret and use the data:** The tool returns a dictionary of metrics with time-series data (timestamps and values). Key interpretations:
                    - **Topics/Partitions:** Gradual increases are normal as you add topics. However, if you notice an unplanned spike, ensure it's expected (maybe a deployment created many topics). Extremely high counts (relative to broker number) might degrade performance; consider adding brokers if partitions per broker count is very high.
                    - **Offline Partitions:** If this is >0 at any time, the cluster has lost leadership for some partitions (likely a broker went down without replica to take over). If partitions remain offline, data for those partitions is unavailable. Investigate broker failures or replication-factor settings (ensure critical topics have replication factor >= 2 or 3).
                    - **Under-Replicated Partitions:** Spikes may occur during broker restarts or network blips, but they should return to 0 quickly. If under-replicated count persists >0 for extended periods, it suggests one or more brokers are not caught up. Identify which broker is lagging or down and resolve (could involve restarting a stuck broker or adding a replacement).
                    - **Connection Count:** This shows total client load. A steadily increasing connection count might indicate new clients or that clients aren't disconnecting properly. If the number is very high, check broker logs or OS limits (each broker has a max connection capacity). Compare with historical norms; sudden large jumps might cause broker strain or require tuning (e.g., increased connection backlog or thread pools).
                    - **Active Controller Count:** Should always be 1. If you see it drop to 0 or spike to 2, it usually means a controller election took place (possibly due to the controller broker failing or restarting). Brief fluctuations from 1 to 0 back to 1 may correspond to a normal failover. Repeated elections (count flipping often) could indicate an unstable controller broker.

                    **Trends and thresholds for cluster-level metrics:**
                    - A growing number of topics/partitions without corresponding increase in resources could eventually saturate broker memory or network. Keep partitions per broker to a reasonable level (there's no hard limit, but thousands of partitions per broker can be problematic).
                    - **Offline Partitions = 0** is the only acceptable steady-state. Alert immediately on any >0.
                    - **Under-Replicated Partitions** should trend back to 0 quickly after any transient issues. Continuous non-zero values (especially increasing) is critical to address (could lead to data loss if another failure occurs).
                    - **Connection Count:** No fixed "max", but track your typical range. If it approaches known limits (for example, if each broker can handle X thousand connections based on instance type), consider scaling or load balancing clients. Spikes might correlate with deploys or client bugs.
                    - **Controller Elections:** If ActiveControllerCount deviates from 1 even briefly, note the time and correlate with broker logs (there will be logs for controller election). Frequent elections (e.g., multiple times a day) are a concern - possibly due to a flapping broker or network issues between brokers.

                    **Trends and thresholds for broker-level metrics:**
                    - **Throughput:** If cluster traffic is increasing, ensure no single broker approaches network saturation (for instance, if an instance type can handle X MB/s, keep an eye if BytesOut on any broker gets close). Sudden throughput imbalance might warrant data redistribution.
                    - **UnderReplicated:** Should normally be 0. Even a small non-zero for extended periods is an alert condition. If under-replication persists on one broker, it may eventually lead to ISR shrink (replica being kicked out) or risk data loss if another failure happens.
                    - **LeaderCount:** Imbalance isn't immediately critical but can cause indirect issues (hotter broker). Aim for leader count to be within a small range across brokers. Large discrepancies might need manual rebalancing.
                    - **Latency metrics:** While exact acceptable values depend on workload, sustained mean latencies above, say, 100-200ms is usually problematic for Kafka (typical operations are faster). If any broker's mean latency jumps significantly relative to its baseline, investigate that broker's health (CPU, memory, garbage collection in logs, etc.). Use these metrics to detect if client-facing performance is degrading at the broker level.

                - For "available_metrics" action:
                    - Metrics (list): List of available metrics based on the monitoring level
                    - MonitoringLevel (str): The monitoring level used to filter metrics
        """
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
                cluster_info = kafka_client.describe_cluster(ClusterArn=cluster_arn)['ClusterInfo']
                cluster_monitoring = cluster_info.get('EnhancedMonitoring', 'DEFAULT')

                # Return metrics filtered by the cluster's monitoring level
                return list_available_metrics(monitoring_level=cluster_monitoring)
            else:
                # If no cluster ARN is provided, raise an error as monitoring level is required
                raise ValueError('Cluster ARN must be provided to determine monitoring level')
        else:
            raise ValueError(f'Unsupported action or missing required arguments for {action}')

    @mcp.tool(name='list_customer_iam_access')
    def list_customer_iam_access_tool(
        region: str = Field(description='AWS region'),
        cluster_arn: str = Field(description='The ARN of the MSK cluster'),
    ):
        """
        List IAM access information for an MSK cluster.

        Args:
            cluster_arn: The ARN of the MSK cluster
            region: AWS region name

        Returns:
            dict: Dictionary containing:
                - cluster_info (dict): Basic cluster information including:
                    - ClusterArn (str): The ARN of the cluster
                    - ClusterName (str): The name of the cluster
                    - IamAuthEnabled (bool): Whether IAM authentication is enabled
                - resource_policies (list): Resource-based policies attached to the cluster, each containing:
                    - Version (str): The policy version
                    - Statement (list): List of policy statements
                - matching_policies (list): IAM policies that grant access to this cluster, each containing:
                    - PolicyName (str): The name of the policy
                    - PolicyArn (str): The ARN of the policy
                    - Actions (list): List of allowed Kafka actions
        """
        # Create a client manager instance
        client_manager = AWSClientManager()

        # No need to create individual clients, the list_customer_iam_access function will handle it

        # Pass the client manager to the list_customer_iam_access function
        return list_customer_iam_access(cluster_arn=cluster_arn, client_manager=client_manager)
