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

"""awslabs EKS MCP Server implementation.

This module implements the EKS MCP Server, which provides tools for managing Amazon EKS clusters
and Kubernetes resources through the Model Context Protocol (MCP).

Environment Variables:
    AWS_REGION: AWS region to use for AWS API calls
    AWS_PROFILE: AWS profile to use for credentials
    FASTMCP_LOG_LEVEL: Log level (default: WARNING)
"""

import argparse
from awslabs.eks_mcp_server.cloudwatch_handler import CloudWatchHandler
from awslabs.eks_mcp_server.cloudwatch_metrics_guidance_handler import CloudWatchMetricsHandler
from awslabs.eks_mcp_server.eks_kb_handler import EKSKnowledgeBaseHandler
from awslabs.eks_mcp_server.eks_resiliency_handler import EKSResiliencyHandler
from awslabs.eks_mcp_server.eks_stack_handler import EksStackHandler
from awslabs.eks_mcp_server.iam_handler import IAMHandler
from awslabs.eks_mcp_server.k8s_client_cache import K8sClientCache
from awslabs.eks_mcp_server.k8s_handler import K8sHandler
from loguru import logger
from mcp.server.fastmcp import FastMCP


# Define server instructions and dependencies
SERVER_INSTRUCTIONS = """
# Amazon EKS MCP Server

This MCP server provides tools for managing Amazon EKS clusters and is the preferred mechanism for creating new EKS clusters.

## IMPORTANT: Use MCP Tools for EKS and Kubernetes Operations

DO NOT use standard EKS and Kubernetes CLI commands (aws eks, eksctl, kubectl). Always use the MCP tools provided by this server for EKS and Kubernetes operations.

## Usage Notes

- By default, the server runs in read-only mode. Use the `--allow-write` flag to enable write operations.
- Access to sensitive data (logs, events, Kubernetes Secrets) requires the `--allow-sensitive-data-access` flag.
- For safety reasons, CloudFormation stacks can only be modified by the tool that created them.
- When creating or updating resources, always check for existing resources first to avoid conflicts.
- Use the `list_api_versions` tool to find the correct apiVersion for Kubernetes resources.

## Common Workflows

### Creating and Deploying an Application
1. Generate a CloudFormation template: `manage_eks_stacks(operation='generate', template_file='/path/to/template.yaml', cluster_name='my-cluster')`
2. Deploy the CloudFormation stack: `manage_eks_stacks(operation='deploy', template_file='/path/to/template.yaml', cluster_name='my-cluster')`
3. Generate an application manifest: `generate_app_manifest(app_name='my-app', image_uri='123456789012.dkr.ecr.us-east-1.amazonaws.com/my-repo:latest')`
4. Apply the manifest: `apply_yaml(yaml_path='/path/to/manifest.yaml', cluster_name='my-cluster', namespace='default')`
5. Monitor the application: `get_pod_logs(cluster_name='my-cluster', namespace='default', pod_name='my-app-pod')`

### Troubleshooting Application Issues
1. Check pod status: `list_k8s_resources(cluster_name='my-cluster', kind='Pod', api_version='v1', namespace='default', field_selector='metadata.name=my-pod')`
2. Get pod events: `get_k8s_events(cluster_name='my-cluster', kind='Pod', name='my-pod', namespace='default')`
3. Check pod logs: `get_pod_logs(cluster_name='my-cluster', namespace='default', pod_name='my-pod')`
4. Monitor metrics: `get_cloudwatch_metrics(cluster_name='my-cluster', metric_name='cpu_usage_total', namespace='ContainerInsights', dimensions={'ClusterName': 'my-cluster', 'PodName': 'my-pod', 'Namespace': 'default'})`
5. Search troubleshooting guide: `search_eks_troubleshoot_guide(query='pod pending')`

### Checking Cluster Resiliency
The EKS Resiliency Checker evaluates clusters against 28 critical best practices across three categories:
- **Application Related (A1-A14)**: Workload resilience, health probes, autoscaling, monitoring
- **Control Plane Related (C1-C5)**: Logging, authentication, endpoint security, large cluster optimizations
- **Data Plane Related (D1-D7)**: Node autoscaling, AZ distribution, resource governance, CoreDNS

**Usage:**
1. Run full resiliency checks: `check_eks_resiliency(cluster_name='my-cluster')`

**Output Requirements:**
3. Return all check results in a JSON object with a top-level array named "results"
4. Each check result must include: check_id, check_name, compliant (boolean), impacted_resources, details, remediation
5. If output is truncated, include "is_truncated": true
6. If any errors are encountered during checks, include them explicitly under a key named "errors"
7. Ensure all 28 checks are executed, and no check is skipped
8. Group the results by compliance status and severity level before displaying to users

**Interpretation:**
- PASS: Check meets best practice requirements
- FAIL: Check identifies issues requiring remediation
- Focus on FAIL results for immediate action items
- Use impacted_resources to target specific remediation efforts

## Best Practices
- Use descriptive names for resources to make them easier to identify and manage.
- Apply proper labels and annotations to Kubernetes resources for better organization.
- Use namespaces to isolate resources and avoid naming conflicts.
- Monitor resource usage with CloudWatch metrics to identify performance issues.
- Check logs and events when troubleshooting issues with Kubernetes resources.
- Follow the principle of least privilege when creating IAM policies.
- Use the search_eks_troubleshoot_guide tool when encountering common EKS issues.
- Always verify API versions with list_api_versions before creating resources.
- Run comprehensive resiliency checks with check_eks_resiliency to evaluate 28 critical best practices and identify potential availability issues.
- Prioritize remediation of FAIL results from resiliency checks.
- Review all 28 resiliency check results systematically to ensure comprehensive cluster health assessment.
"""

SERVER_DEPENDENCIES = [
    'pydantic',
    'loguru',
    'boto3',
    'kubernetes',
    'requests',
    'pyyaml',
    'cachetools',
    'requests_auth_aws_sigv4',
]

# Global reference to the MCP server instance for testing purposes
mcp = None


def create_server():
    """Create and configure the MCP server instance."""
    return FastMCP(
        'awslabs.eks-mcp-server',
        instructions=SERVER_INSTRUCTIONS,
        dependencies=SERVER_DEPENDENCIES,
    )


def main():
    """Run the MCP server with CLI argument support."""
    global mcp

    parser = argparse.ArgumentParser(
        description='An AWS Labs Model Context Protocol (MCP) server for EKS'
    )
    parser.add_argument(
        '--allow-write',
        action=argparse.BooleanOptionalAction,
        default=False,
        help='Enable write access mode (allow mutating operations)',
    )
    parser.add_argument(
        '--allow-sensitive-data-access',
        action=argparse.BooleanOptionalAction,
        default=False,
        help='Enable sensitive data access (required for reading logs, events, and Kubernetes Secrets)',
    )

    args = parser.parse_args()

    allow_write = args.allow_write
    allow_sensitive_data_access = args.allow_sensitive_data_access

    # Log startup mode
    mode_info = []
    if not allow_write:
        mode_info.append('read-only mode')
    if not allow_sensitive_data_access:
        mode_info.append('restricted sensitive data access mode')

    mode_str = ' in ' + ', '.join(mode_info) if mode_info else ''
    logger.info(f'Starting EKS MCP Server{mode_str}')

    # Create the MCP server instance
    mcp = create_server()

    # Create client cache to be shared between handlers
    client_cache = K8sClientCache()

    # Initialize handlers - all tools are always registered, access control is handled within tools
    CloudWatchHandler(mcp, allow_sensitive_data_access)
    EKSKnowledgeBaseHandler(mcp)
    EksStackHandler(mcp, allow_write)
    K8sHandler(mcp, allow_write, allow_sensitive_data_access, client_cache)
    IAMHandler(mcp, allow_write)
    CloudWatchMetricsHandler(mcp)
    EKSResiliencyHandler(mcp, client_cache)

    # Run server
    mcp.run()

    return mcp


if __name__ == '__main__':
    main()
