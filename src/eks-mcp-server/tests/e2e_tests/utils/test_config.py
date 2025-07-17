"""Configuration for end-to-end tests."""

# EKS cluster configuration
EKS_CLUSTER_CONFIG = {
    "cluster_name": "test-eks-hybrid",  # Replace with your cluster's name
    "region": "us-west-2",                     # Replace with your cluster's region
    "vpc_id": "vpc-0ba023159808954e7",         # Optional, will be detected if not provided
}

# Hybrid node configuration
HYBRID_NODE_CONFIG = {
    "node_names": ["mi-0bfcba958b91f5e0a", "mi-0fec8c110483fd66f"],  # Node names to validate
    "expected_remote_cidr": "10.80.146.0/24",  # Replace with your actual CIDR
}

# Test parameters
TEST_CONFIG = {
    "timeout_seconds": 30,                     # Timeout for API calls
    "additional_hostnames": ["amazon.com", "aws.amazon.com"],  # Additional hostnames to test DNS resolution
}

# AWS credentials configuration
AWS_CONFIG = {
    "profile": 'admin-role',  # Set to your AWS profile name or None to use default credentials
}
