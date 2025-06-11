"""
Logs and Telemetry API Module

This module provides functions to retrieve metrics and telemetry data for MSK clusters,
as well as a separate tool for IAM access information.
"""

from mcp.server.fastmcp import FastMCP

from ..common_functions.client_manager import AWSClientManager
from .cluster_metrics_tools import get_cluster_metrics, list_available_metrics
from .list_customer_iam_access import list_customer_iam_access


def register_module(mcp: FastMCP) -> None:
    @mcp.tool(name="get_cluster_telemetry")
    def get_cluster_telemetry(region, action, cluster_arn=None, kwargs={}):
        """
        Unified API to retrieve telemetry data for MSK clusters.

        Args:
            action (str): The operation to perform (metrics, available_metrics)
            cluster_arn (str): The ARN of the cluster (required for cluster operations)
            region (str): AWS region
            kwargs (dict, optional): Additional arguments specific to each action:
                For "metrics" action:
                    start_time (datetime): Start time for metric data retrieval
                    end_time (datetime): End time for metric data retrieval
                    period (int): The granularity, in seconds, of the returned data points
                    metrics (list or dict): Either:
                        - List of metric names (e.g., ['BytesInPerSec', 'BytesOutPerSec'])
                        - Dictionary mapping metric names to optional statistics
                          (e.g., {'BytesInPerSec': 'Sum', 'BytesOutPerSec': 'Average'})
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
                - For "available_metrics" action:
                    - Metrics (list): List of available metrics based on the monitoring level
                    - MonitoringLevel (str): The monitoring level used to filter metrics
        """
        if action == "metrics" and cluster_arn:
            # Create a client manager instance
            client_manager = AWSClientManager()

            # Extract required parameters from kwargs
            start_time = kwargs.get("start_time")
            end_time = kwargs.get("end_time")
            period = kwargs.get("period")
            metrics = kwargs.get("metrics")

            # Check if required parameters exist
            if start_time is None:
                raise ValueError("start_time is required for metrics action")
            if end_time is None:
                raise ValueError("end_time is required for metrics action")
            if period is None:
                raise ValueError("period is required for metrics action")
            if metrics is None:
                raise ValueError("metrics is required for metrics action")

            # Extract optional parameters from kwargs
            scan_by = kwargs.get("scan_by")
            label_options = kwargs.get("label_options")
            pagination_config = kwargs.get("pagination_config")

            # Pass the extracted parameters to the get_cluster_metrics function
            return get_cluster_metrics(
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
        elif action == "available_metrics":
            if cluster_arn:
                # Create a client manager instance
                client_manager = AWSClientManager()

                # Configure the client manager with the region
                kafka_client = client_manager.get_client("kafka", region)

                # Get cluster's monitoring level
                cluster_info = kafka_client.describe_cluster(ClusterArn=cluster_arn)["ClusterInfo"]
                cluster_monitoring = cluster_info.get("EnhancedMonitoring", "DEFAULT")

                # Return metrics filtered by the cluster's monitoring level
                return list_available_metrics(monitoring_level=cluster_monitoring)
            else:
                # If no cluster ARN is provided, raise an error as monitoring level is required
                raise ValueError("Cluster ARN must be provided to determine monitoring level")
        else:
            raise ValueError(f"Unsupported action or missing required arguments for {action}")

    @mcp.tool(name="list_customer_iam_access")
    def list_customer_iam_access_tool(region, cluster_arn):
        """
        List IAM access information for an MSK cluster.

        Args:
            cluster_arn: The ARN of the MSK cluster
            region: AWS region name

        Returns:
            Dictionary containing:
            - cluster_info: Basic cluster information including IAM auth status
            - resource_policies: Resource-based policies attached to the cluster
            - matching_policies: IAM policies that grant access to this cluster
        """
        # Create a client manager instance
        client_manager = AWSClientManager()

        # No need to create individual clients, the list_customer_iam_access function will handle it

        # Pass the client manager to the list_customer_iam_access function
        return list_customer_iam_access(cluster_arn=cluster_arn, client_manager=client_manager)
