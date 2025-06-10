"""
Static Tools API Module

This module provides static tools that do not require AWS API calls.
"""

from mcp.server.fastmcp import FastMCP

from .cluster_best_practices import get_cluster_best_practices


def register_module(mcp: FastMCP) -> None:
    @mcp.tool(name="get_cluster_best_practices")
    def get_cluster_best_practices_tool(instance_type: str, number_of_brokers: int):
        """
        Provides detailed best practices and quotas for AWS MSK clusters to guide in evaluating cluster health and identifying deviations.

        Args:
            instance_type (str): The AWS MSK broker instance type (e.g., kafka.m5.large, kafka.m5.xlarge, express.m7g.large).
            number_of_brokers (int): The total number of brokers in the MSK cluster.

        Returns:
            dict: Detailed best practice guidelines and recommended quotas, including:
                - Instance specifications (vCPU, memory, network bandwidth)
                - Throughput recommendations (ingress and egress)
                - Partition guidelines (per broker and per cluster)
                - Resource utilization thresholds (CPU and disk)
                - Reliability configuration (replication factor, in-sync replicas)

        How to interpret results:
            - CPU Utilization: Maintain CPU usage below 60% for regular operations and never exceed 70%.
            - Disk Utilization: Act if storage surpasses 85%, urgently address at 90%.
            - Partition Count: Keep partition counts within recommended broker limits.
            - Replication Factor: Follow replication factor 3 and minimum ISR of 2 for optimal resilience.
            - Under-Replicated Partitions: Any deviation from zero indicates potential replication health issues.
            - Leader Imbalance: Maintain leader distribution within 10% balance to avoid performance bottlenecks.

        Additional Considerations:
            - Express broker types (express.*) offer better performance and stability.
            - Always consider recommended throughput values for ingress/egress planning, not the maximum values.
            - CloudWatch metrics may be in bytes; ensure proper conversion between bytes and megabytes.
        """
        return get_cluster_best_practices(instance_type, number_of_brokers)
