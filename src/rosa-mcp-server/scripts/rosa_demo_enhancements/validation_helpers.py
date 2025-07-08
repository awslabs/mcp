"""Enhanced validation functions based on ROSA e-book best practices."""

from typing import Tuple, Optional


def validate_rosa_cluster_config(
    cluster_name: str,
    instance_type: str,
    replicas: int,
    multi_az: bool,
    environment: str = "production"
) -> Tuple[bool, Optional[str]]:
    """
    Validate ROSA cluster configuration based on e-book recommendations.
    """
    # Cluster name validation
    if not cluster_name or len(cluster_name) > 54:
        return False, "Cluster name must be 1-54 characters"
    
    if not cluster_name.replace("-", "").replace("_", "").isalnum():
        return False, "Cluster name must be alphanumeric with hyphens/underscores"
    
    # Environment-based validation
    if environment == "production":
        if not multi_az:
            return False, "Production clusters must be multi-AZ"
        if replicas < 3:
            return False, "Production requires minimum 3 replicas"
        if instance_type.startswith("t"):
            return False, "T-series instances not recommended for production"
    
    # Multi-AZ validation
    if multi_az and replicas % 3 != 0:
        return False, "Multi-AZ requires replicas to be multiple of 3"
    
    return True, None


def recommend_cluster_size(workload_type: str, expected_pods: int) -> dict:
    """
    Recommend cluster size based on workload requirements.
    """
    # Based on e-book recommendations
    sizing = {
        "small": {
            "max_pods": 100,
            "workers": 3,
            "instance_type": "m5.large",
            "estimated_cost": "$350/month"
        },
        "medium": {
            "max_pods": 500,
            "workers": 6,
            "instance_type": "m5.xlarge",
            "estimated_cost": "$700/month"
        },
        "large": {
            "max_pods": 1000,
            "workers": 9,
            "instance_type": "m5.2xlarge",
            "estimated_cost": "$1400/month"
        }
    }
    
    if expected_pods <= 100:
        return sizing["small"]
    elif expected_pods <= 500:
        return sizing["medium"]
    else:
        return sizing["large"]
