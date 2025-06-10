"""
Cluster Best Practices Module

This module provides tools for retrieving best practices and quotas for AWS MSK clusters.
"""

# Global best-practice thresholds and guidelines
RECOMMENDED_CPU_UTILIZATION_PERCENT = 60  # Keep CPU (user+sys) under 60% for headroom
MAX_CPU_UTILIZATION_PERCENT = 70  # Avoid exceeding 70% (risk of instability during reassignments)
STORAGE_UTILIZATION_WARNING_PERCENT = 85  # Alert threshold for disk usage
STORAGE_UTILIZATION_CRITICAL_PERCENT = (
    90  # Critical threshold for disk usage (take immediate action)
)
RECOMMENDED_REPLICATION_FACTOR = 3  # Typical replication factor for production clusters
RECOMMENDED_MIN_INSYNC_REPLICAS = 2  # minISR for RF=3 to tolerate one broker failure
UNDER_REPLICATED_PARTITIONS_TOLERANCE = (
    0  # Under-replicated partitions should ideally be zero in steady state
)
LEADER_IMBALANCE_TOLERANCE_PERCENT = 10  # Leader imbalance threshold across brokers

# Resource specifications for supported broker instance types
INSTANCE_SPECS = {
    "kafka.t3.small": {
        "vCPU": 2,
        "Memory (GB)": 2,
        "Network Bandwidth (Gbps)": 5.0,
        "Ingress Recommended (MBps)": 4.8,
        "Ingress Max (MBps)": 7.2,
        "Egress Recommended (MBps)": 9.6,
        "Egress Max (MBps)": 18.0,
        "Partitions per Broker Recommended": 300,
        "Partitions per Broker Max": 300,
    },
    "kafka.m5.large": {
        "vCPU": 2,
        "Memory (GB)": 8,
        "Network Bandwidth (Gbps)": 10.0,
        "Ingress Recommended (MBps)": 4.8,
        "Ingress Max (MBps)": 7.2,
        "Egress Recommended (MBps)": 9.6,
        "Egress Max (MBps)": 18.0,
        "Partitions per Broker Recommended": 1000,
        "Partitions per Broker Max": 1500,
    },
    "kafka.m5.xlarge": {
        "vCPU": 4,
        "Memory (GB)": 16,
        "Network Bandwidth (Gbps)": 10.0,
        "Ingress Recommended (MBps)": 9.6,
        "Ingress Max (MBps)": 14.4,
        "Egress Recommended (MBps)": 19.2,
        "Egress Max (MBps)": 36.0,
        "Partitions per Broker Recommended": 1000,
        "Partitions per Broker Max": 1500,
    },
    "kafka.m5.2xlarge": {
        "vCPU": 8,
        "Memory (GB)": 32,
        "Network Bandwidth (Gbps)": 10.0,
        "Ingress Recommended (MBps)": 19.2,
        "Ingress Max (MBps)": 28.8,
        "Egress Recommended (MBps)": 38.4,
        "Egress Max (MBps)": 72.0,
        "Partitions per Broker Recommended": 2000,
        "Partitions per Broker Max": 3000,
    },
    "kafka.m5.4xlarge": {
        "vCPU": 16,
        "Memory (GB)": 64,
        "Network Bandwidth (Gbps)": 10.0,
        "Ingress Recommended (MBps)": 38.4,
        "Ingress Max (MBps)": 57.6,
        "Egress Recommended (MBps)": 76.8,
        "Egress Max (MBps)": 144.0,
        "Partitions per Broker Recommended": 4000,
        "Partitions per Broker Max": 6000,
    },
    "kafka.m5.8xlarge": {
        "vCPU": 32,
        "Memory (GB)": 128,
        "Network Bandwidth (Gbps)": 10.0,
        "Ingress Recommended (MBps)": 76.9,
        "Ingress Max (MBps)": 115.4,
        "Egress Recommended (MBps)": 153.8,
        "Egress Max (MBps)": 288.5,
        "Partitions per Broker Recommended": 4000,
        "Partitions per Broker Max": 6000,
    },
    "kafka.m5.12xlarge": {
        "vCPU": 48,
        "Memory (GB)": 192,
        "Network Bandwidth (Gbps)": 12.0,
        "Ingress Recommended (MBps)": 115.4,
        "Ingress Max (MBps)": 173.1,
        "Egress Recommended (MBps)": 230.8,
        "Egress Max (MBps)": 432.7,
        "Partitions per Broker Recommended": 4000,
        "Partitions per Broker Max": 6000,
    },
    "kafka.m5.16xlarge": {
        "vCPU": 64,
        "Memory (GB)": 256,
        "Network Bandwidth (Gbps)": 20.0,
        "Ingress Recommended (MBps)": 153.8,
        "Ingress Max (MBps)": 230.7,
        "Egress Recommended (MBps)": 307.7,
        "Egress Max (MBps)": 576.9,
        "Partitions per Broker Recommended": 4000,
        "Partitions per Broker Max": 6000,
    },
    "kafka.m5.24xlarge": {
        "vCPU": 96,
        "Memory (GB)": 384,
        "Network Bandwidth (Gbps)": 25.0,
        "Ingress Recommended (MBps)": 153.8,
        "Ingress Max (MBps)": 230.7,
        "Egress Recommended (MBps)": 307.7,
        "Egress Max (MBps)": 576.9,
        "Partitions per Broker Recommended": 4000,
        "Partitions per Broker Max": 6000,
    },
    "kafka.m7g.large": {
        "vCPU": 2,
        "Memory (GB)": 8,
        "Network Bandwidth (Gbps)": 12.5,
        "Ingress Recommended (MBps)": 4.8,
        "Ingress Max (MBps)": 7.2,
        "Egress Recommended (MBps)": 9.6,
        "Egress Max (MBps)": 18.0,
        "Partitions per Broker Recommended": 1000,
        "Partitions per Broker Max": 1500,
    },
    "kafka.m7g.xlarge": {
        "vCPU": 4,
        "Memory (GB)": 16,
        "Network Bandwidth (Gbps)": 15.0,
        "Ingress Recommended (MBps)": 9.6,
        "Ingress Max (MBps)": 14.4,
        "Egress Recommended (MBps)": 19.2,
        "Egress Max (MBps)": 36.0,
        "Partitions per Broker Recommended": 1000,
        "Partitions per Broker Max": 1500,
    },
    "kafka.m7g.2xlarge": {
        "vCPU": 8,
        "Memory (GB)": 32,
        "Network Bandwidth (Gbps)": 15.0,
        "Ingress Recommended (MBps)": 19.2,
        "Ingress Max (MBps)": 28.8,
        "Egress Recommended (MBps)": 38.4,
        "Egress Max (MBps)": 72.0,
        "Partitions per Broker Recommended": 2000,
        "Partitions per Broker Max": 3000,
    },
    "kafka.m7g.4xlarge": {
        "vCPU": 16,
        "Memory (GB)": 64,
        "Network Bandwidth (Gbps)": 15.0,
        "Ingress Recommended (MBps)": 38.4,
        "Ingress Max (MBps)": 57.6,
        "Egress Recommended (MBps)": 76.8,
        "Egress Max (MBps)": 144.0,
        "Partitions per Broker Recommended": 4000,
        "Partitions per Broker Max": 6000,
    },
    "kafka.m7g.8xlarge": {
        "vCPU": 32,
        "Memory (GB)": 128,
        "Network Bandwidth (Gbps)": 15.0,
        "Ingress Recommended (MBps)": 76.9,
        "Ingress Max (MBps)": 115.4,
        "Egress Recommended (MBps)": 153.8,
        "Egress Max (MBps)": 288.5,
        "Partitions per Broker Recommended": 4000,
        "Partitions per Broker Max": 6000,
    },
    "kafka.m7g.12xlarge": {
        "vCPU": 48,
        "Memory (GB)": 192,
        "Network Bandwidth (Gbps)": 22.5,
        "Ingress Recommended (MBps)": 115.4,
        "Ingress Max (MBps)": 173.1,
        "Egress Recommended (MBps)": 230.8,
        "Egress Max (MBps)": 432.7,
        "Partitions per Broker Recommended": 4000,
        "Partitions per Broker Max": 6000,
    },
    "kafka.m7g.16xlarge": {
        "vCPU": 64,
        "Memory (GB)": 256,
        "Network Bandwidth (Gbps)": 30.0,
        "Ingress Recommended (MBps)": 153.8,
        "Ingress Max (MBps)": 230.7,
        "Egress Recommended (MBps)": 307.7,
        "Egress Max (MBps)": 576.9,
        "Partitions per Broker Recommended": 4000,
        "Partitions per Broker Max": 6000,
    },
    "express.m7g.large": {
        "vCPU": 2,
        "Memory (GB)": 8,
        "Network Bandwidth (Gbps)": 12.5,
        "Ingress Recommended (MBps)": 15.6,
        "Ingress Max (MBps)": 23.4,
        "Egress Recommended (MBps)": 31.2,
        "Egress Max (MBps)": 58.5,
        "Partitions per Broker Recommended": 1000,
        "Partitions per Broker Max": 1500,
    },
    "express.m7g.xlarge": {
        "vCPU": 4,
        "Memory (GB)": 16,
        "Network Bandwidth (Gbps)": 15.0,
        "Ingress Recommended (MBps)": 31.2,
        "Ingress Max (MBps)": 46.8,
        "Egress Recommended (MBps)": 62.5,
        "Egress Max (MBps)": 117.0,
        "Partitions per Broker Recommended": 1000,
        "Partitions per Broker Max": 1500,
    },
    "express.m7g.2xlarge": {
        "vCPU": 8,
        "Memory (GB)": 32,
        "Network Bandwidth (Gbps)": 15.0,
        "Ingress Recommended (MBps)": 62.5,
        "Ingress Max (MBps)": 93.7,
        "Egress Recommended (MBps)": 125.0,
        "Egress Max (MBps)": 234.2,
        "Partitions per Broker Recommended": 2000,
        "Partitions per Broker Max": 3000,
    },
    "express.m7g.4xlarge": {
        "vCPU": 16,
        "Memory (GB)": 64,
        "Network Bandwidth (Gbps)": 15.0,
        "Ingress Recommended (MBps)": 124.9,
        "Ingress Max (MBps)": 187.5,
        "Egress Recommended (MBps)": 249.8,
        "Egress Max (MBps)": 468.7,
        "Partitions per Broker Recommended": 4000,
        "Partitions per Broker Max": 6000,
    },
    "express.m7g.8xlarge": {
        "vCPU": 32,
        "Memory (GB)": 128,
        "Network Bandwidth (Gbps)": 15.0,
        "Ingress Recommended (MBps)": 250.0,
        "Ingress Max (MBps)": 375.0,
        "Egress Recommended (MBps)": 500.0,
        "Egress Max (MBps)": 937.5,
        "Partitions per Broker Recommended": 4000,
        "Partitions per Broker Max": 6000,
    },
    "express.m7g.12xlarge": {
        "vCPU": 48,
        "Memory (GB)": 192,
        "Network Bandwidth (Gbps)": 22.5,
        "Ingress Recommended (MBps)": 375.0,
        "Ingress Max (MBps)": 562.5,
        "Egress Recommended (MBps)": 750.0,
        "Egress Max (MBps)": 1406.2,
        "Partitions per Broker Recommended": 4000,
        "Partitions per Broker Max": 6000,
    },
    "express.m7g.16xlarge": {
        "vCPU": 64,
        "Memory (GB)": 256,
        "Network Bandwidth (Gbps)": 30.0,
        "Ingress Recommended (MBps)": 500.0,
        "Ingress Max (MBps)": 750.0,
        "Egress Recommended (MBps)": 1000.0,
        "Egress Max (MBps)": 1875.0,
        "Partitions per Broker Recommended": 4000,
        "Partitions per Broker Max": 6000,
    },
}


def get_cluster_best_practices(instance_type: str, number_of_brokers: int) -> dict:
    """
    Provides detailed best practices and quotas for AWS MSK clusters to guide AI agents in evaluating cluster health and identifying deviations.

    Args:
        instance_type (str): The AWS MSK broker instance type (e.g., kafka.m5.large).
        number_of_brokers (int): The total number of brokers in the MSK cluster.

    Returns:
        dict: Detailed best practice guidelines and recommended quotas, structured in natural language for easy interpretation by AI.

    How to interpret results:
        - **CPU Utilization**: Maintain CPU usage below 60% for regular operations and never exceed 70%.
        - **Disk Utilization**: Act if storage surpasses 85%, urgently address at 90%.
        - **Partition Count**: Keep partition counts within recommended broker limits.
        - **Replication Factor**: Follow replication factor 3 and minimum ISR of 2 for optimal resilience.
        - **Under-Replicated Partitions**: Any deviation from zero indicates potential replication health issues.
        - **Leader Imbalance**: Maintain leader distribution within 10% balance to avoid performance bottlenecks.

    Additional Considerations:
        - Never recommond moving out of express broker, as they are more stable and better performing.
        - Always consider recommonded throughput for ingress, egress objective, no the max

    Example usage:
        advisory = get_cluster_best_practices('kafka.m5.large', 3)
        # Evaluate actual metrics against advisory data provided.
    """
    if instance_type not in INSTANCE_SPECS:
        return {"Error": f"Instance type '{instance_type}' is not supported or recognized."}

    specs = INSTANCE_SPECS[instance_type]
    recommended_cluster_partitions = specs["Partitions per Broker Recommended"] * number_of_brokers
    max_cluster_partitions = specs["Partitions per Broker Max"] * number_of_brokers

    replication_factor = (
        RECOMMENDED_REPLICATION_FACTOR
        if number_of_brokers >= RECOMMENDED_REPLICATION_FACTOR
        else number_of_brokers
    )
    min_insync_replicas = (
        RECOMMENDED_MIN_INSYNC_REPLICAS
        if number_of_brokers >= RECOMMENDED_REPLICATION_FACTOR
        else number_of_brokers
    )

    # Determine if this is an express cluster type
    is_express_cluster = instance_type.startswith("express.")

    # For express clusters, always use replication factor of 3
    if is_express_cluster:
        replication_factor = 3

    return {
        "Instance Type": f"{instance_type} (provided as input)",
        "Number of Brokers": f"{number_of_brokers} (provided as input)",
        "vCPU per Broker": specs["vCPU"],
        "Memory (GB) per Broker": f"{specs['Memory (GB)']} (available on the host)",
        "Network Bandwidth (Gbps) per Broker": f"{specs['Network Bandwidth (Gbps)']} (available on the host)",
        "Ingress Throughput Recommended (MBps)": f"{specs['Ingress Recommended (MBps)']} (Note: CloudWatch metrics may be in bytes; ensure proper conversion between bytes and megabytes)",
        "Ingress Throughput Max (MBps)": f"{specs['Ingress Max (MBps)']} (Note: CloudWatch metrics may be in bytes; ensure proper conversion between bytes and megabytes)",
        "Egress Throughput Recommended (MBps)": f"{specs['Egress Recommended (MBps)']} (Note: CloudWatch metrics may be in bytes; ensure proper conversion between bytes and megabytes)",
        "Egress Throughput Max (MBps)": f"{specs['Egress Max (MBps)']} (Note: CloudWatch metrics may be in bytes; ensure proper conversion between bytes and megabytes)",
        "Recommended Partitions per Broker": specs["Partitions per Broker Recommended"],
        "Max Partitions per Broker": f"{specs['Partitions per Broker Max']} (Note: Each partition should be 3-way replicated. For example, 1000 total partitions with three brokers will mean each broker has 1000 partitions.)",
        "Recommended Max Partitions per Cluster": recommended_cluster_partitions,
        "Max Partitions per Cluster": max_cluster_partitions,
        "CPU Utilization Guidelines": f"Keep below {RECOMMENDED_CPU_UTILIZATION_PERCENT}% regularly; never exceed {MAX_CPU_UTILIZATION_PERCENT}%.",
        "Disk Utilization Guidelines": f"Warning at {STORAGE_UTILIZATION_WARNING_PERCENT}%, critical at {STORAGE_UTILIZATION_CRITICAL_PERCENT}%.",
        "Replication Factor": f"{replication_factor}"
        + (
            " (Note: For express clusters, replication factor should always be 3)"
            if is_express_cluster
            else " (recommended)"
        ),
        "Minimum In-Sync Replicas": min_insync_replicas,
        "Under-Replicated Partitions Tolerance": UNDER_REPLICATED_PARTITIONS_TOLERANCE,
        "Leader Imbalance Tolerance (%)": LEADER_IMBALANCE_TOLERANCE_PERCENT,
    }
