"""Operational helpers for ROSA cluster management."""

from typing import Dict, List
import json


def create_autoscaling_config(
    min_replicas: int = 3,
    max_replicas: int = 10,
    target_cpu: int = 70
) -> Dict[str, any]:
    """
    Create cluster autoscaling configuration.
    """
    return {
        "apiVersion": "autoscaling.openshift.io/v1",
        "kind": "ClusterAutoscaler",
        "metadata": {
            "name": "default"
        },
        "spec": {
            "scaleDown": {
                "enabled": True,
                "delayAfterAdd": "10m",
                "delayAfterDelete": "10s",
                "delayAfterFailure": "3m"
            },
            "resourceLimits": {
                "maxNodesTotal": max_replicas,
                "cores": {
                    "min": 4 * min_replicas,
                    "max": 4 * max_replicas
                },
                "memory": {
                    "min": 16 * min_replicas,
                    "max": 16 * max_replicas
                }
            }
        }
    }


def generate_monitoring_config(cluster_name: str) -> Dict[str, any]:
    """
    Generate CloudWatch monitoring configuration for ROSA.
    """
    return {
        "cloudwatch": {
            "region": "us-east-1",
            "namespace": f"ROSA/{cluster_name}",
            "metrics": {
                "cluster_metrics": [
                    "node_cpu_utilization",
                    "node_memory_utilization",
                    "pod_cpu_utilization",
                    "pod_memory_utilization"
                ],
                "api_metrics": [
                    "apiserver_request_duration_seconds",
                    "apiserver_request_total",
                    "etcd_request_duration_seconds"
                ]
            },
            "logs": {
                "groups": [
                    f"/aws/containerinsights/{cluster_name}/application",
                    f"/aws/containerinsights/{cluster_name}/dataplane",
                    f"/aws/containerinsights/{cluster_name}/host"
                ]
            }
        },
        "alerts": [
            {
                "name": "HighNodeCPU",
                "metric": "node_cpu_utilization",
                "threshold": 80,
                "evaluationPeriods": 2
            },
            {
                "name": "HighNodeMemory",
                "metric": "node_memory_utilization",
                "threshold": 85,
                "evaluationPeriods": 2
            },
            {
                "name": "PodRestarts",
                "metric": "pod_restart_rate",
                "threshold": 5,
                "evaluationPeriods": 1
            }
        ]
    }


def calculate_rosa_costs(
    instance_type: str,
    node_count: int,
    multi_az: bool = False,
    hours_per_month: int = 730
) -> Dict[str, float]:
    """
    Calculate estimated ROSA cluster costs.
    """
    # Simplified pricing (actual prices vary by region)
    instance_prices = {
        "m5.large": 0.096,
        "m5.xlarge": 0.192,
        "m5.2xlarge": 0.384,
        "m5.4xlarge": 0.768,
        "m5a.large": 0.086,
        "m5a.xlarge": 0.172
    }
    
    rosa_hourly_fee = 0.03  # Per vCPU-hour
    control_plane_fee = 0.10  # Per hour
    
    # Get instance price
    instance_hourly = instance_prices.get(instance_type, 0.192)
    
    # Calculate vCPUs (rough estimate)
    vcpus = 2 if "large" in instance_type else 4
    if "2xlarge" in instance_type:
        vcpus = 8
    elif "4xlarge" in instance_type:
        vcpus = 16
    
    # Calculate costs
    compute_cost = instance_hourly * node_count * hours_per_month
    rosa_fee = rosa_hourly_fee * vcpus * node_count * hours_per_month
    control_plane_cost = control_plane_fee * hours_per_month
    
    # Add multi-AZ overhead
    if multi_az:
        compute_cost *= 1.1  # 10% overhead for cross-AZ traffic
    
    total = compute_cost + rosa_fee + control_plane_cost
    
    return {
        "compute": round(compute_cost, 2),
        "rosa_service": round(rosa_fee, 2),
        "control_plane": round(control_plane_cost, 2),
        "total_monthly": round(total, 2),
        "total_hourly": round(total / hours_per_month, 3)
    }
