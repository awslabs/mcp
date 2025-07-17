"""Configuration for EKS MCP Server end-to-end tests."""

# EKS cluster configuration
EKS_CLUSTER_CONFIG = {
    "cluster_name": "test-eks-hybrid",  # Replace with your cluster's name
    "region": "us-west-2",              # Replace with your cluster's region
}

# AWS credentials configuration
AWS_CONFIG = {
    "profile": 'admin-role',  # Set to your AWS profile name or None to use default credentials
}

# Test parameters
TEST_CONFIG = {
    "timeout_seconds": 30,
    "additional_hostnames": ["amazon.com", "aws.amazon.com"],  # Additional hostnames to test DNS resolution
}

# Server configuration
SERVER_CONFIG = {
    "host": "127.0.0.1",  # Using direct IP instead of localhost
    "port": 8888,  # Using a different port in case 8080 is in use
    "allow_write": True,
    "allow_sensitive_data_access": True,
}
