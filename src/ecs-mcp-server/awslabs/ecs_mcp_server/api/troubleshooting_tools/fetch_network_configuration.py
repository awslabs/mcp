# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""
Network-level diagnostics for ECS deployments

This module provides the main entry point for network analysis functionality,
focusing on collecting raw data that can be interpreted by an LLM.
"""

import inspect
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from botocore.exceptions import ClientError

from awslabs.ecs_mcp_server.utils.aws import get_aws_client

logger = logging.getLogger(__name__)


async def handle_aws_api_call(func, error_value=None, *args, **kwargs):
    """Execute AWS API calls with standardized error handling."""
    try:
        result = func(*args, **kwargs)
        if inspect.iscoroutine(result):
            result = await result
        return result
    except ClientError as e:
        func_name = func.__name__ if hasattr(func, "__name__") else "unknown"
        logger.warning(f"API error in {func_name}: {e}")
        if isinstance(error_value, dict) and "error" not in error_value:
            error_value["error"] = str(e)
        return error_value
    except Exception as e:
        func_name = func.__name__ if hasattr(func, "__name__") else "unknown"
        logger.exception(f"Unexpected error in {func_name}: {e}")
        if isinstance(error_value, dict) and "error" not in error_value:
            error_value["error"] = str(e)
        return error_value


async def fetch_network_configuration(
    app_name: str, vpc_id: Optional[str] = None, cluster_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Network-level diagnostics for ECS deployments.
    Collects data from VPCs, subnets, security groups, load balancers, and ECS clusters

    Parameters
    ----------
    app_name : str
        The name of the application to analyze
    vpc_id : str, optional
        Specific VPC ID to analyze
    cluster_name : str, optional
        Specific ECS cluster name

    Returns
    -------
    Dict[str, Any]
        Raw network configuration data for LLM analysis
    """
    try:
        return await get_network_data(app_name, vpc_id, cluster_name)
    except Exception as e:
        logger.exception(f"Error in fetch_network_configuration: {e}")
        return {"status": "error", "error": f"Internal error: {str(e)}"}


async def get_network_data(
    app_name: str, vpc_id: Optional[str] = None, cluster_name: Optional[str] = None
) -> Dict[str, Any]:
    """Collect all relevant networking data with minimal processing."""
    try:
        # Initialize clients
        ec2 = await get_aws_client("ec2")
        ecs = await get_aws_client("ecs")
        elbv2 = await get_aws_client("elbv2")

        # Identify relevant clusters
        clusters = []
        if cluster_name:
            clusters.append(cluster_name)
        else:
            # Find clusters related to the app name
            cluster_response = await handle_aws_api_call(ecs.list_clusters, {"clusterArns": []})
            cluster_response = cluster_response or {}

            for cluster_arn in cluster_response.get("clusterArns", []):
                if app_name.lower() in cluster_arn.lower():
                    cluster_name = cluster_arn.split("/")[-1]
                    clusters.append(cluster_name)

            # Add default cluster as a fallback
            clusters.append("default")

        # Identify relevant VPCs
        vpc_ids = [vpc_id] if vpc_id else []
        if not vpc_ids:
            # VPC discovery from ECS tasks
            discovered_vpcs = await discover_vpcs_from_clusters(clusters)
            vpc_ids.extend(discovered_vpcs)

            # VPC discovery from load balancers
            lb_vpcs = await discover_vpcs_from_loadbalancers(app_name)
            vpc_ids.extend(lb_vpcs)

            # VPC discovery from CloudFormation tags
            cf_vpcs = await discover_vpcs_from_cloudformation(app_name)
            vpc_ids.extend(cf_vpcs)

            # Direct VPC search by tags
            vpc_response = await handle_aws_api_call(ec2.describe_vpcs, {"Vpcs": []})
            vpc_response = vpc_response or {}

            for vpc in vpc_response.get("Vpcs", []):
                if vpc is None:
                    continue
                tags = {tag["Key"]: tag["Value"] for tag in vpc.get("Tags", [])}
                if tags.get("Name", "").lower().startswith(app_name.lower()):
                    vpc_id = vpc.get("VpcId")
                    if vpc_id:
                        vpc_ids.append(vpc_id)

        # Remove duplicates
        vpc_ids = list(set(filter(None, vpc_ids)))

        # Return early if no VPCs found
        if not vpc_ids:
            return {
                "status": "warning",
                "message": f"No VPC found for application '{app_name}'",
                "app_name": app_name,
                "timestamp": datetime.now().isoformat(),
            }

        # Get all network data in a structured way
        data = {
            "timestamp": datetime.now().isoformat(),
            "app_name": app_name,
            "vpc_ids": vpc_ids,
            "clusters": clusters,
            "raw_resources": {
                # EC2 resources
                "vpcs": await get_ec2_resource(ec2, "describe_vpcs", vpc_ids=vpc_ids),
                "subnets": await get_ec2_resource(ec2, "describe_subnets", vpc_ids=vpc_ids),
                "security_groups": await get_ec2_resource(
                    ec2, "describe_security_groups", vpc_ids=vpc_ids
                ),
                "route_tables": await get_ec2_resource(
                    ec2, "describe_route_tables", vpc_ids=vpc_ids
                ),
                "network_interfaces": await get_ec2_resource(
                    ec2, "describe_network_interfaces", vpc_ids=vpc_ids
                ),
                "nat_gateways": await get_ec2_resource(
                    ec2, "describe_nat_gateways", vpc_ids=vpc_ids
                ),
                "internet_gateways": await get_ec2_resource(
                    ec2, "describe_internet_gateways", vpc_ids=vpc_ids
                ),
                # ELB resources
                "load_balancers": await get_elb_resources(
                    elbv2, "describe_load_balancers", vpc_ids
                ),
                "target_groups": await get_associated_target_groups(elbv2, app_name, vpc_ids),
            },
        }

        # Add analysis guidance for the LLM
        data["analysis_guide"] = generate_analysis_guide()

        return {"status": "success", "data": data}

    except Exception as e:
        logger.exception(f"Error getting network data: {e}")
        return {"status": "error", "error": str(e)}


async def discover_vpcs_from_clusters(clusters: List[str]) -> List[str]:
    """Discover VPC IDs associated with ECS clusters."""
    vpc_ids = []

    try:
        ecs = await get_aws_client("ecs")
        ec2 = await get_aws_client("ec2")

        for cluster in clusters:
            # List tasks in the cluster
            tasks_response = await handle_aws_api_call(
                ecs.list_tasks, {"taskArns": []}, cluster=cluster
            )
            tasks_response = tasks_response or {}

            if not tasks_response.get("taskArns"):
                continue

            # Describe tasks to get network configuration
            task_arns = tasks_response.get("taskArns", [])[:100]  # Limit to 100 tasks
            tasks = await handle_aws_api_call(
                ecs.describe_tasks,
                {"tasks": []},
                cluster=cluster,
                tasks=task_arns,
            )
            tasks = tasks or {}

            # Extract network interface IDs from tasks
            eni_ids = []
            for task in tasks.get("tasks", []):
                if task is None:
                    continue
                for attachment in task.get("attachments", []):
                    if attachment is None:
                        continue
                    if attachment.get("type") == "ElasticNetworkInterface":
                        for detail in attachment.get("details", []):
                            if detail is None:
                                continue
                            if detail.get("name") == "networkInterfaceId":
                                value = detail.get("value")
                                if value:
                                    eni_ids.append(value)

            # Get VPC IDs from network interfaces
            if eni_ids:
                eni_response = await handle_aws_api_call(
                    ec2.describe_network_interfaces,
                    {"NetworkInterfaces": []},
                    NetworkInterfaceIds=eni_ids,
                )
                eni_response = eni_response or {}

                for eni in eni_response.get("NetworkInterfaces", []):
                    if eni is None:
                        continue
                    vpc_id = eni.get("VpcId")
                    if vpc_id:
                        vpc_ids.append(vpc_id)

    except Exception as e:
        logger.warning(f"Error discovering VPCs from clusters: {e}")

    return vpc_ids


async def discover_vpcs_from_loadbalancers(app_name: str) -> List[str]:
    """Discover VPC IDs associated with load balancers related to the application."""
    vpc_ids = []

    try:
        elbv2 = await get_aws_client("elbv2")

        # Describe load balancers
        lb_response = await handle_aws_api_call(
            elbv2.describe_load_balancers, {"LoadBalancers": []}
        )
        lb_response = lb_response or {}

        for lb in lb_response.get("LoadBalancers", []):
            if lb is None:
                continue
            # Check if load balancer name contains app name
            if app_name.lower() in lb.get("LoadBalancerName", "").lower():
                vpc_id = lb.get("VpcId")
                if vpc_id:
                    vpc_ids.append(vpc_id)

            # Also check tags if name doesn't match
            else:
                lb_arn = lb.get("LoadBalancerArn")
                if not lb_arn:
                    continue

                tags_response = await handle_aws_api_call(
                    elbv2.describe_tags,
                    {"TagDescriptions": []},
                    ResourceArns=[lb_arn],
                )
                tags_response = tags_response or {}

                for tag_desc in tags_response.get("TagDescriptions", []):
                    if tag_desc is None:
                        continue
                    for tag in tag_desc.get("Tags", []):
                        if tag is None:
                            continue
                        if (
                            tag.get("Key") == "Name"
                            and app_name.lower() in tag.get("Value", "").lower()
                        ):
                            vpc_id = lb.get("VpcId")
                            if vpc_id:
                                vpc_ids.append(vpc_id)
                            break

    except Exception as e:
        logger.warning(f"Error discovering VPCs from load balancers: {e}")

    return vpc_ids


async def discover_vpcs_from_cloudformation(app_name: str) -> List[str]:
    """Discover VPC IDs from CloudFormation stacks related to the application."""
    vpc_ids = []

    try:
        cfn = await get_aws_client("cloudformation")

        # List CloudFormation stacks
        stacks = []
        next_token = None

        # Add pagination limit to avoid potential infinite loops
        max_iterations = 10  # Reasonable limit for pagination
        iterations = 0

        while True and iterations < max_iterations:
            iterations += 1

            if next_token:
                response = await handle_aws_api_call(
                    cfn.list_stacks, {"StackSummaries": []}, NextToken=next_token
                )
            else:
                response = await handle_aws_api_call(cfn.list_stacks, {"StackSummaries": []})

            response = response or {}
            stacks.extend(response.get("StackSummaries", []))

            next_token = response.get("NextToken")
            if not next_token:
                break

        # Filter stacks by app name
        app_stacks = []
        for stack in stacks:
            if stack is None:
                continue
            if app_name.lower() in stack.get("StackName", "").lower() and stack.get(
                "StackStatus"
            ) not in ["DELETE_COMPLETE", "DELETE_IN_PROGRESS"]:
                stack_name = stack.get("StackName")
                if stack_name:
                    app_stacks.append(stack_name)

        # Describe resources in each stack
        for stack_name in app_stacks:
            resources = await handle_aws_api_call(
                cfn.list_stack_resources, {"StackResourceSummaries": []}, StackName=stack_name
            )
            resources = resources or {}

            for resource in resources.get("StackResourceSummaries", []):
                if resource is None:
                    continue
                if resource.get("ResourceType") == "AWS::EC2::VPC":
                    vpc_id = resource.get("PhysicalResourceId")
                    if vpc_id:
                        vpc_ids.append(vpc_id)

    except Exception as e:
        logger.warning(f"Error discovering VPCs from CloudFormation: {e}")

    return vpc_ids


async def get_ec2_resource(
    client, method: str, vpc_ids: Optional[List[str]] = None, **kwargs
) -> Dict[str, Any]:
    """Generic function to call EC2 API methods with VPC filtering when applicable."""
    try:
        filters = []
        if vpc_ids:
            if method in [
                "describe_subnets",
                "describe_security_groups",
                "describe_route_tables",
                "describe_nat_gateways",
            ]:
                filters.append({"Name": "vpc-id", "Values": vpc_ids})

        if filters:
            kwargs["Filters"] = filters

        if method == "describe_vpcs" and vpc_ids:
            kwargs["VpcIds"] = vpc_ids

        func = getattr(client, method)
        error_value = {"error": "API Error"}

        result = await handle_aws_api_call(func, error_value, **kwargs)
        return result if result is not None else {"error": "No response"}
    except Exception as e:
        logger.warning(f"Error in get_ec2_resource for {method}: {e}")
        return {"error": "API Error"}


async def get_elb_resources(client, method: str, vpc_ids: List[str]) -> Dict[str, Any]:
    """Generic function to call ELB API methods."""
    try:
        func = getattr(client, method)
        error_value = {"error": f"Error in {method}"}

        response = await handle_aws_api_call(func, error_value)
        response = response or {}

        # For load balancers, filter by VPC afterward
        if vpc_ids and method == "describe_load_balancers" and "LoadBalancers" in response:
            response["LoadBalancers"] = [
                lb for lb in response["LoadBalancers"] if lb and lb.get("VpcId") in vpc_ids
            ]

        return response if response is not None else {"error": "No response"}
    except Exception as e:
        logger.warning(f"Error in get_elb_resources for {method}: {e}")
        return {"error": str(e)}


async def get_associated_target_groups(client, app_name: str, vpc_ids: List[str]) -> Dict[str, Any]:
    """Get target groups with their health and targets."""
    try:
        # Get all target groups
        tg_response = await handle_aws_api_call(client.describe_target_groups, {"TargetGroups": []})
        tg_response = tg_response or {}

        target_groups = tg_response.get("TargetGroups", [])

        # Filter by VPC ID
        if vpc_ids:
            target_groups = [tg for tg in target_groups if tg and tg.get("VpcId") in vpc_ids]

        # Filter by name similarity to app name
        name_matched_tgs = []
        for tg in target_groups:
            if tg is None:
                continue
            if app_name.lower() in tg.get("TargetGroupName", "").lower():
                name_matched_tgs.append(tg)

        # If we have name matches, prioritize them
        if name_matched_tgs:
            target_groups = name_matched_tgs

        # Get target health for each group
        result = {"TargetGroups": target_groups, "TargetHealth": {}}

        for tg in target_groups:
            if tg is None:
                continue
            tg_arn = tg.get("TargetGroupArn")
            if tg_arn:
                health_response = await handle_aws_api_call(
                    client.describe_target_health,
                    {"TargetHealthDescriptions": []},
                    TargetGroupArn=tg_arn,
                )
                health_response = health_response or {}
                result["TargetHealth"][tg_arn] = health_response.get("TargetHealthDescriptions", [])

        return result

    except Exception as e:
        logger.warning(f"Error getting associated target groups: {e}")
        return {"error": str(e)}


async def get_clusters_info(client, clusters: List[str]) -> Dict[str, Any]:
    """Get detailed information about ECS clusters."""
    try:
        results = {}

        # Get cluster details
        if clusters:
            clusters_response = await handle_aws_api_call(
                client.describe_clusters, {"clusters": [], "failures": []}, clusters=clusters
            )
            clusters_response = clusters_response or {}
            results["clusters"] = clusters_response.get("clusters", [])
            results["failures"] = clusters_response.get("failures", [])

        return results

    except Exception as e:
        logger.warning(f"Error getting cluster information: {e}")
        return {"error": str(e)}


def generate_analysis_guide() -> Dict[str, Any]:
    """Generate guidance for the LLM to interpret the network data."""
    return {
        "common_issues": [
            {
                "issue": "Missing security group ingress rules",
                "description": "Services may be unreachable if security groups don't allow traffic",
                "checks": [
                    "Check if security groups have ingress rules for required ports",
                    "Verify load balancer security groups can reach targets",
                    "Look for empty security groups attached to resources",
                ],
            },
            {
                "issue": "Subnet IP exhaustion",
                "description": "Tasks may fail to launch if subnets have insufficient IPs",
                "checks": [
                    "Check how many ENIs are in each subnet",
                    "Compare to subnet CIDR range size",
                    "Look for large numbers of resources in small subnets",
                ],
            },
            {
                "issue": "Target health issues",
                "description": "Load balancers may not route traffic if targets are unhealthy",
                "checks": [
                    "Check target health status and reasons for failures",
                    "Verify health check configuration is appropriate",
                    "Ensure targets can receive traffic from load balancers",
                ],
            },
            {
                "issue": "Routing configuration",
                "description": (
                    "Resources in private subnets may need NAT gateways for outbound access"
                ),
                "checks": [
                    "Check route tables for internet access",
                    "Verify NAT gateways or endpoints for private subnets",
                    "Ensure proper routing between components",
                ],
            },
            {
                "issue": "DNS configuration",
                "description": (
                    "Services may have name resolution issues with improper DNS settings"
                ),
                "checks": [
                    "Verify VPC DNS settings are enabled",
                    "Check for any custom DNS settings or endpoints",
                ],
            },
        ],
        "resource_relationships": [
            {
                "from": "Load Balancers",
                "to": "Target Groups",
                "key": "VPC resources are interconnected through security groups and routing",
            },
            {
                "from": "Target Groups",
                "to": "ECS Tasks",
                "key": "Target groups route traffic to specific ports on ECS tasks",
            },
            {
                "from": "ECS Tasks",
                "to": "Network Interfaces",
                "key": "Tasks attach to ENIs in specific subnets",
            },
            {
                "from": "Network Interfaces",
                "to": "Security Groups",
                "key": "ENIs are protected by security group rules",
            },
            {
                "from": "Subnets",
                "to": "Route Tables",
                "key": "Subnets use route tables for network traffic paths",
            },
        ],
    }
