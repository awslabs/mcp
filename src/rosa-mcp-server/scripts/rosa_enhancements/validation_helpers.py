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

"""Validation helpers for ROSA MCP Server based on e-book insights."""

from typing import Dict, List, Optional, Tuple


def validate_cluster_configuration(
    cluster_name: str,
    version: str,
    multi_az: bool,
    replicas: int,
    machine_type: str
) -> Tuple[bool, Optional[str]]:
    """
    Validate cluster configuration based on ROSA best practices.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Validate cluster name
    if not cluster_name or len(cluster_name) > 54:
        return False, "Cluster name must be between 1 and 54 characters"
    
    if not cluster_name.replace("-", "").isalnum():
        return False, "Cluster name must contain only alphanumeric characters and hyphens"
    
    # Validate version format
    if not version or not version.count(".") == 2:
        return False, "Version must be in format X.Y.Z"
    
    # Validate replicas for multi-AZ
    if multi_az and replicas % 3 != 0:
        return False, "Multi-AZ clusters require replicas to be a multiple of 3"
    
    # Validate minimum replicas
    if replicas < 2:
        return False, "Minimum 2 replicas required for production clusters"
    
    return True, None


def recommend_instance_type(
    workload_type: str,
    memory_requirements: int,
    cpu_requirements: int
) -> str:
    """
    Recommend instance type based on workload requirements.
    
    Args:
        workload_type: Type of workload (general, memory, compute, gpu)
        memory_requirements: Memory in GB
        cpu_requirements: Number of vCPUs
    
    Returns:
        Recommended instance type
    """
    recommendations = {
        "general": {
            (4, 2): "m5.large",
            (8, 2): "m5.xlarge",
            (16, 4): "m5.xlarge",
            (32, 8): "m5.2xlarge",
            (64, 16): "m5.4xlarge",
        },
        "memory": {
            (16, 2): "r5.large",
            (32, 4): "r5.xlarge",
            (64, 8): "r5.2xlarge",
            (128, 16): "r5.4xlarge",
        },
        "compute": {
            (4, 2): "c5.large",
            (8, 4): "c5.xlarge",
            (16, 8): "c5.2xlarge",
            (32, 16): "c5.4xlarge",
        },
        "gpu": {
            (61, 8): "p3.2xlarge",
            (244, 32): "p3.8xlarge",
            (488, 64): "p3.16xlarge",
        }
    }
    
    # Find best match
    workload_recs = recommendations.get(workload_type, recommendations["general"])
    
    for (mem, cpu), instance in sorted(workload_recs.items()):
        if mem >= memory_requirements and cpu >= cpu_requirements:
            return instance
    
    # Default to largest if requirements exceed all options
    return list(workload_recs.values())[-1]


def validate_networking_config(
    private_link: bool,
    http_proxy: Optional[str],
    https_proxy: Optional[str],
    no_proxy: Optional[List[str]]
) -> Tuple[bool, Optional[str]]:
    """
    Validate networking configuration.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Validate proxy configuration
    if http_proxy and not https_proxy:
        return False, "HTTPS proxy must be configured when HTTP proxy is set"
    
    # Validate no_proxy for private link
    if private_link and no_proxy:
        required_no_proxy = [
            "169.254.169.254",  # Instance metadata
            ".s3.amazonaws.com",  # S3 access
            ".ec2.amazonaws.com",  # EC2 API
        ]
        for required in required_no_proxy:
            if required not in no_proxy:
                return False, f"no_proxy must include {required} for private link clusters"
    
    return True, None


def calculate_cluster_cost_estimate(
    region: str,
    instance_type: str,
    replicas: int,
    multi_az: bool,
    hours_per_month: int = 730
) -> Dict[str, float]:
    """
    Calculate estimated monthly cost for ROSA cluster.
    
    Returns:
        Dictionary with cost breakdown
    """
    # Simplified cost estimates (actual costs vary by region)
    instance_costs = {
        "m5.large": 0.096,
        "m5.xlarge": 0.192,
        "m5.2xlarge": 0.384,
        "m5.4xlarge": 0.768,
        "r5.large": 0.126,
        "r5.xlarge": 0.252,
        "c5.large": 0.085,
        "c5.xlarge": 0.17,
    }
    
    # Base costs
    rosa_service_fee = 0.03  # Per vCPU hour
    control_plane_cost = 0.10 * hours_per_month  # Fixed cost
    
    # Calculate instance costs
    hourly_rate = instance_costs.get(instance_type, 0.192)
    instance_cost = hourly_rate * replicas * hours_per_month
    
    # Multi-AZ adds overhead
    if multi_az:
        instance_cost *= 1.1  # 10% overhead for cross-AZ traffic
    
    # Calculate ROSA service fee (estimate vCPUs)
    vcpus_per_instance = int(instance_type.split(".")[-1].replace("xlarge", "")) * 2
    rosa_fee = rosa_service_fee * vcpus_per_instance * replicas * hours_per_month
    
    return {
        "control_plane": control_plane_cost,
        "worker_instances": instance_cost,
        "rosa_service_fee": rosa_fee,
        "total_monthly": control_plane_cost + instance_cost + rosa_fee,
        "total_hourly": (control_plane_cost + instance_cost + rosa_fee) / hours_per_month
    }


def generate_troubleshooting_steps(error_type: str) -> List[str]:
    """
    Generate troubleshooting steps based on common ROSA errors.
    
    Args:
        error_type: Type of error encountered
    
    Returns:
        List of troubleshooting steps
    """
    troubleshooting_guides = {
        "installation_timeout": [
            "Check CloudFormation stack status in AWS Console",
            "Verify IAM roles have correct permissions",
            "Check VPC and subnet configurations",
            "Review installation logs: rosa logs install -c <cluster-name>",
            "Verify service quotas are not exceeded",
            "Check if the region supports all required AWS services"
        ],
        "authentication_failed": [
            "Verify Red Hat account has ROSA access",
            "Check AWS credentials are valid",
            "Ensure IAM user has required permissions",
            "Try refreshing ROSA token: rosa login --token=<token>",
            "Verify OIDC provider is correctly configured"
        ],
        "node_not_ready": [
            "Check node events: oc describe node <node-name>",
            "Verify security group rules allow required traffic",
            "Check if the instance has network connectivity",
            "Review kubelet logs on the affected node",
            "Verify disk space is available",
            "Check if container runtime is functioning"
        ],
        "pod_pending": [
            "Check pod events: oc describe pod <pod-name>",
            "Verify resource requests can be satisfied",
            "Check node selectors and affinity rules",
            "Verify persistent volume claims are bound",
            "Check if required images can be pulled",
            "Review taints and tolerations"
        ],
        "ingress_not_working": [
            "Verify ingress controller is running",
            "Check load balancer status in AWS Console",
            "Verify DNS records point to load balancer",
            "Check ingress resource configuration",
            "Verify backend services are running",
            "Review security group rules for load balancer"
        ]
    }
    
    return troubleshooting_guides.get(
        error_type,
        ["Check cluster status", "Review logs", "Contact support"]
    )
