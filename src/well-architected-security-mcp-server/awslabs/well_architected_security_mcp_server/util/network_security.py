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

"""Utility functions for checking AWS network services for data-in-transit security."""

from typing import Any, Dict, List

import boto3
import botocore.exceptions
from botocore.config import Config
from mcp.server.fastmcp import Context

from awslabs.well_architected_security_mcp_server import __version__

# User agent configuration for AWS API calls
USER_AGENT_CONFIG = Config(
    user_agent_extra=f"awslabs/mcp/well-architected-security-mcp-server/{__version__}"
)

# Acceptable TLS versions for secure data in transit
ACCEPTABLE_TLS_VERSIONS = ["TLSv1.2", "TLSv1.3"]

# Minimum TLS version for secure data in transit
MIN_TLS_VERSION = "TLSv1.2"

# Insecure protocols that should be avoided
INSECURE_PROTOCOLS = ["TLSv1.0", "TLSv1.1", "SSLv3", "SSLv2"]


async def check_network_security(
    region: str,
    services: List[str],
    session: boto3.Session,
    ctx: Context,
    include_non_compliant_only: bool = False,
) -> Dict[str, Any]:
    """Check AWS network resources for data-in-transit security best practices.

    Args:
        region: AWS region to check
        services: List of network services to check
        session: boto3 Session for AWS API calls
        ctx: MCP context for error reporting
        include_non_compliant_only: Whether to include only non-compliant resources in the results

    Returns:
        Dictionary with network security status
    """
    results = {
        "region": region,
        "services_checked": services,
        "resources_checked": 0,
        "compliant_resources": 0,
        "non_compliant_resources": 0,
        "compliance_by_service": {},
        "resource_details": [],
        "recommendations": [],
    }

    # Find all network resources using Resource Explorer
    network_resources = await find_network_resources(region, session, services, ctx)

    # Check each service as requested
    if "elb" in services:
        # Check classic load balancers
        elb_client = session.client("elb", region_name=region, config=USER_AGENT_CONFIG)
        elb_results = await check_classic_load_balancers(
            region, elb_client, ctx, network_resources
        )
        await _update_results(results, elb_results, "elb", include_non_compliant_only)

        # Check application and network load balancers
        elbv2_client = session.client("elbv2", region_name=region, config=USER_AGENT_CONFIG)
        elbv2_results = await check_elbv2_load_balancers(
            region, elbv2_client, ctx, network_resources
        )
        await _update_results(results, elbv2_results, "elbv2", include_non_compliant_only)

    if "vpc" in services:
        vpc_client = session.client("ec2", region_name=region, config=USER_AGENT_CONFIG)
        vpc_results = await check_vpc_endpoints(region, vpc_client, ctx, network_resources)
        await _update_results(results, vpc_results, "vpc", include_non_compliant_only)

        # Check security groups
        sg_results = await check_security_groups(region, vpc_client, ctx, network_resources)
        await _update_results(results, sg_results, "security_groups", include_non_compliant_only)

    if "apigateway" in services:
        apigw_client = session.client("apigateway", region_name=region, config=USER_AGENT_CONFIG)
        apigw_results = await check_api_gateway(region, apigw_client, ctx, network_resources)
        await _update_results(results, apigw_results, "apigateway", include_non_compliant_only)

    if "cloudfront" in services:
        # CloudFront is a global service, but we'll check it if requested
        if region == "us-east-1":
            cf_client = session.client("cloudfront", region_name=region, config=USER_AGENT_CONFIG)
            cf_results = await check_cloudfront_distributions(
                region, cf_client, ctx, network_resources
            )
            await _update_results(results, cf_results, "cloudfront", include_non_compliant_only)

    # Generate overall recommendations based on findings
    results["recommendations"] = await generate_recommendations(results)

    return results


async def _update_results(
    main_results: Dict[str, Any],
    service_results: Dict[str, Any],
    service_name: str,
    include_non_compliant_only: bool,
) -> None:
    """Update the main results dictionary with service-specific results."""
    # Update resource counts
    main_results["resources_checked"] += service_results.get("resources_checked", 0)
    main_results["compliant_resources"] += service_results.get("compliant_resources", 0)
    main_results["non_compliant_resources"] += service_results.get("non_compliant_resources", 0)

    # Add service-specific compliance info
    main_results["compliance_by_service"][service_name] = {
        "resources_checked": service_results.get("resources_checked", 0),
        "compliant_resources": service_results.get("compliant_resources", 0),
        "non_compliant_resources": service_results.get("non_compliant_resources", 0),
    }

    # Add resource details
    for resource in service_results.get("resource_details", []):
        if not include_non_compliant_only or not resource.get("compliant", True):
            main_results["resource_details"].append(resource)


async def generate_recommendations(results: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on the scan results."""
    recommendations = []

    # Check ELB recommendations
    if "elb" in results.get("compliance_by_service", {}) or "elbv2" in results.get(
        "compliance_by_service", {}
    ):
        elb_non_compliant = (
            results.get("compliance_by_service", {})
            .get("elb", {})
            .get("non_compliant_resources", 0)
        )
        elbv2_non_compliant = (
            results.get("compliance_by_service", {})
            .get("elbv2", {})
            .get("non_compliant_resources", 0)
        )

        if elb_non_compliant > 0 or elbv2_non_compliant > 0:
            recommendations.append("Configure all load balancers to use HTTPS/TLS listeners")
            recommendations.append("Update security policies to use TLS 1.2 or later")
            recommendations.append(
                "Use AWS Certificate Manager (ACM) to provision and manage certificates"
            )

    # Check VPC endpoint recommendations
    if (
        "vpc" in results.get("compliance_by_service", {})
        and results.get("compliance_by_service", {})
        .get("vpc", {})
        .get("non_compliant_resources", 0)
        > 0
    ):
        recommendations.append(
            "Configure interface VPC endpoints to use TLS for all communications"
        )
        recommendations.append("Enable private DNS for interface endpoints where applicable")

    # Check security group recommendations
    if (
        "security_groups" in results.get("compliance_by_service", {})
        and results.get("compliance_by_service", {})
        .get("security_groups", {})
        .get("non_compliant_resources", 0)
        > 0
    ):
        recommendations.append("Restrict inbound traffic to necessary ports only")
        recommendations.append("Avoid allowing unrestricted access (0.0.0.0/0) to sensitive ports")
        recommendations.append("Use security groups to enforce encryption in transit")

    # Check API Gateway recommendations
    if (
        "apigateway" in results.get("compliance_by_service", {})
        and results.get("compliance_by_service", {})
        .get("apigateway", {})
        .get("non_compliant_resources", 0)
        > 0
    ):
        recommendations.append("Configure API Gateway to enforce HTTPS endpoints only")
        recommendations.append("Set a minimum TLS version of 1.2 for all API Gateway APIs")

    # Check CloudFront recommendations
    if (
        "cloudfront" in results.get("compliance_by_service", {})
        and results.get("compliance_by_service", {})
        .get("cloudfront", {})
        .get("non_compliant_resources", 0)
        > 0
    ):
        recommendations.append("Configure CloudFront distributions to redirect HTTP to HTTPS")
        recommendations.append("Use TLS 1.2 or later for viewer and origin connections")
        recommendations.append(
            "Use Origin Access Identity (OAI) or Origin Access Control (OAC) for S3 origins"
        )

    # General recommendations
    recommendations.append("Implement a centralized certificate management process")
    recommendations.append("Regularly rotate and audit TLS certificates")
    recommendations.append("Monitor for expiring certificates and insecure protocol usage")

    return recommendations


async def find_network_resources(
    region: str, session: boto3.Session, services: List[str], ctx: Context
) -> Dict[str, Any]:
    """Find network resources using Resource Explorer."""
    try:
        print(
            f"[DEBUG:NetworkSecurity] Finding network resources in {region} using Resource Explorer"
        )

        # Initialize resource explorer client
        resource_explorer = session.client(
            "resource-explorer-2", region_name=region, config=USER_AGENT_CONFIG
        )

        # Try to get the default view for Resource Explorer
        print("[DEBUG:NetworkSecurity] Listing Resource Explorer views...")
        views = resource_explorer.list_views()
        print(f"[DEBUG:NetworkSecurity] Found {len(views.get('Views', []))} views")

        default_view = None
        # Find the default view
        for view in views.get("Views", []):
            print(f"[DEBUG:NetworkSecurity] View: {view.get('ViewArn')}")
            if view.get("Filters", {}).get("FilterString", "") == "":
                default_view = view.get("ViewArn")
                print(f"[DEBUG:NetworkSecurity] Found default view: {default_view}")
                break

        if not default_view:
            print("[DEBUG:NetworkSecurity] No default view found. Cannot use Resource Explorer.")
            await ctx.warning(
                "No default Resource Explorer view found. Will fall back to direct service API calls."
            )
            return {"error": "No default Resource Explorer view found"}

        # Build filter strings for each service
        service_filters = []

        if "elb" in services:
            service_filters.append("service:elasticloadbalancing")
        if "vpc" in services:
            service_filters.append("service:ec2 resourcetype:ec2:vpc")
            service_filters.append("service:ec2 resourcetype:ec2:vpc-endpoint")
            service_filters.append("service:ec2 resourcetype:ec2:security-group")
        if "apigateway" in services:
            service_filters.append("service:apigateway")
        if "cloudfront" in services and region == "us-east-1":
            service_filters.append("service:cloudfront")

        # Combine with OR
        filter_string = " OR ".join(service_filters)
        print(f"[DEBUG:NetworkSecurity] Using filter string: {filter_string}")

        # Get resources
        resources = []
        paginator = resource_explorer.get_paginator("list_resources")
        page_iterator = paginator.paginate(
            Filters={"FilterString": filter_string}, MaxResults=100, ViewArn=default_view
        )

        for page in page_iterator:
            resources.extend(page.get("Resources", []))

        print(f"[DEBUG:NetworkSecurity] Found {len(resources)} total network resources")

        # Organize by service
        resources_by_service = {}

        for resource in resources:
            arn = resource.get("Arn", "")
            if ":" in arn:
                service = arn.split(":")[2]

                # Map elasticloadbalancing to 'elb'
                if service == "elasticloadbalancing":
                    service = "elb"

                # Map ec2 VPC endpoints to 'vpc_endpoints'
                if service == "ec2" and "vpc-endpoint" in arn:
                    service = "vpc_endpoints"

                # Map ec2 security groups to 'security_groups'
                if service == "ec2" and "security-group" in arn:
                    service = "security_groups"

                # Map ec2 VPCs to 'vpc'
                if service == "ec2" and "vpc/" in arn and "vpc-endpoint" not in arn:
                    service = "vpc"

                if service not in resources_by_service:
                    resources_by_service[service] = []

                resources_by_service[service].append(resource)

        # Print summary
        for service, svc_resources in resources_by_service.items():
            print(f"[DEBUG:NetworkSecurity] {service}: {len(svc_resources)} resources")

        return {
            "total_resources": len(resources),
            "resources_by_service": resources_by_service,
            "resources": resources,
        }

    except botocore.exceptions.BotoCoreError as e:
        print(f"[DEBUG:NetworkSecurity] Error finding network resources: {e}")
        await ctx.error(f"Error finding network resources: {e}")
        return {"error": str(e), "resources_by_service": {}}


async def check_classic_load_balancers(
    region: str, elb_client: Any, ctx: Context, network_resources: Dict[str, Any]
) -> Dict[str, Any]:
    """Check Classic Load Balancers for data-in-transit security best practices."""
    print(f"[DEBUG:NetworkSecurity] Checking Classic Load Balancers in {region}")

    results = {
        "service": "elb",
        "resources_checked": 0,
        "compliant_resources": 0,
        "non_compliant_resources": 0,
        "resource_details": [],
    }

    try:
        # Get load balancer list - either from Resource Explorer or directly
        load_balancers = []

        if "error" not in network_resources and "elb" in network_resources.get(
            "resources_by_service", {}
        ):
            # Use Resource Explorer results
            elb_resources = network_resources["resources_by_service"]["elb"]
            for resource in elb_resources:
                arn = resource.get("Arn", "")
                # Filter for classic load balancers
                if ":loadbalancer/app/" not in arn and ":loadbalancer/net/" not in arn:
                    lb_name = arn.split("/")[-1]
                    load_balancers.append(lb_name)
        else:
            # Fall back to direct API call
            response = elb_client.describe_load_balancers()
            for lb in response["LoadBalancerDescriptions"]:
                load_balancers.append(lb["LoadBalancerName"])

        print(
            f"[DEBUG:NetworkSecurity] Found {len(load_balancers)} Classic Load Balancers in region {region}"
        )
        results["resources_checked"] = len(load_balancers)

        # Check each load balancer
        for lb_name in load_balancers:
            lb_result = {
                "name": lb_name,
                "arn": f"arn:aws:elasticloadbalancing:{region}:loadbalancer/{lb_name}",
                "type": "classic_load_balancer",
                "compliant": True,
                "issues": [],
                "checks": {},
            }

            # Get load balancer details
            lb_details = elb_client.describe_load_balancers(LoadBalancerNames=[lb_name])[
                "LoadBalancerDescriptions"
            ][0]

            # Check for HTTPS listeners
            listeners = lb_details.get("ListenerDescriptions", [])
            https_listeners = [
                lst for lst in listeners if lst["Listener"].get("Protocol") in ["HTTPS", "SSL"]
            ]
            http_listeners = [
                lst for lst in listeners if lst["Listener"].get("Protocol") in ["HTTP", "TCP"]
            ]

            lb_result["checks"]["https_listeners"] = {
                "count": len(https_listeners),
                "total_listeners": len(listeners),
            }

            # Check if all listeners are secure
            all_secure = len(http_listeners) == 0 and len(https_listeners) > 0
            lb_result["checks"]["all_listeners_secure"] = all_secure

            if not all_secure:
                lb_result["compliant"] = False
                lb_result["issues"].append(f"Found {len(http_listeners)} non-encrypted listeners")

            # Check SSL policies for each HTTPS listener
            for https_listener in https_listeners:
                ssl_policy = None
                try:
                    policy_response = elb_client.describe_load_balancer_policies(
                        LoadBalancerName=lb_name,
                        PolicyNames=[https_listener["PolicyNames"][0]]
                        if https_listener.get("PolicyNames")
                        else [],
                    )

                    if policy_response.get("PolicyDescriptions"):
                        ssl_policy = policy_response["PolicyDescriptions"][0]

                        # Check for secure protocols
                        protocol_policies = [
                            attr
                            for attr in ssl_policy.get("PolicyAttributeDescriptions", [])
                            if attr["AttributeName"].startswith("Protocol-")
                            and attr["AttributeValue"] == "true"
                        ]

                        insecure_protocols = [
                            p["AttributeName"].replace("Protocol-", "")
                            for p in protocol_policies
                            if p["AttributeName"].replace("Protocol-", "") in INSECURE_PROTOCOLS
                        ]

                        if insecure_protocols:
                            lb_result["compliant"] = False
                            lb_result["issues"].append(
                                f"Using insecure protocols: {', '.join(insecure_protocols)}"
                            )

                            if "ssl_policies" not in lb_result["checks"]:
                                lb_result["checks"]["ssl_policies"] = []

                            lb_result["checks"]["ssl_policies"].append(
                                {
                                    "name": ssl_policy.get("PolicyName"),
                                    "insecure_protocols": insecure_protocols,
                                }
                            )
                except Exception as e:
                    print(f"[DEBUG:NetworkSecurity] Error checking SSL policy for {lb_name}: {e}")
                    lb_result["issues"].append("Error checking SSL policy")

            # Generate remediation steps
            lb_result["remediation"] = []

            if not all_secure:
                lb_result["remediation"].append("Replace HTTP listeners with HTTPS listeners")

            if lb_result["checks"].get("ssl_policies") and any(
                p.get("insecure_protocols") for p in lb_result["checks"].get("ssl_policies", [])
            ):
                lb_result["remediation"].append("Update SSL policy to use only TLSv1.2 or later")

            # Update counts
            if lb_result["compliant"]:
                results["compliant_resources"] += 1
            else:
                results["non_compliant_resources"] += 1

            results["resource_details"].append(lb_result)

        return results

    except botocore.exceptions.BotoCoreError as e:
        print(f"[DEBUG:NetworkSecurity] Error checking Classic Load Balancers: {e}")
        await ctx.error(f"Error checking Classic Load Balancers: {e}")
        return {
            "service": "elb",
            "error": str(e),
            "resources_checked": 0,
            "compliant_resources": 0,
            "non_compliant_resources": 0,
            "resource_details": [],
        }


async def check_elbv2_load_balancers(
    region: str, elbv2_client: Any, ctx: Context, network_resources: Dict[str, Any]
) -> Dict[str, Any]:
    """Check Application and Network Load Balancers for data-in-transit security best practices."""
    print(f"[DEBUG:NetworkSecurity] Checking ALB/NLB Load Balancers in {region}")

    results = {
        "service": "elbv2",
        "resources_checked": 0,
        "compliant_resources": 0,
        "non_compliant_resources": 0,
        "resource_details": [],
    }

    try:
        # Get load balancer list - either from Resource Explorer or directly
        load_balancers = []

        if "error" not in network_resources and "elb" in network_resources.get(
            "resources_by_service", {}
        ):
            # Use Resource Explorer results
            elb_resources = network_resources["resources_by_service"]["elb"]
            for resource in elb_resources:
                arn = resource.get("Arn", "")
                # Filter for ALB/NLB load balancers
                if ":loadbalancer/app/" in arn or ":loadbalancer/net/" in arn:
                    load_balancers.append(arn)
        else:
            # Fall back to direct API call
            response = elbv2_client.describe_load_balancers()
            for lb in response["LoadBalancers"]:
                load_balancers.append(lb["LoadBalancerArn"])

        print(
            f"[DEBUG:NetworkSecurity] Found {len(load_balancers)} ALB/NLB Load Balancers in region {region}"
        )
        results["resources_checked"] = len(load_balancers)

        # Check each load balancer
        for lb_arn in load_balancers:
            lb_name = (
                lb_arn.split("/")[-2]
                if "/app/" in lb_arn or "/net/" in lb_arn
                else lb_arn.split("/")[-1]
            )
            lb_type = (
                "application"
                if "/app/" in lb_arn
                else "network"
                if "/net/" in lb_arn
                else "unknown"
            )

            lb_result = {
                "name": lb_name,
                "arn": lb_arn,
                "type": f"{lb_type}_load_balancer",
                "compliant": True,
                "issues": [],
                "checks": {},
            }

            # Get listeners
            try:
                listeners_response = elbv2_client.describe_listeners(LoadBalancerArn=lb_arn)
                listeners = listeners_response.get("Listeners", [])

                # For ALBs, check for HTTPS listeners
                if lb_type == "application":
                    https_listeners = [lst for lst in listeners if lst.get("Protocol") == "HTTPS"]
                    http_listeners = [lst for lst in listeners if lst.get("Protocol") == "HTTP"]

                    lb_result["checks"]["https_listeners"] = {
                        "count": len(https_listeners),
                        "total_listeners": len(listeners),
                    }

                    # Check if all listeners are secure
                    all_secure = len(http_listeners) == 0 and len(https_listeners) > 0
                    lb_result["checks"]["all_listeners_secure"] = all_secure

                    if not all_secure:
                        lb_result["compliant"] = False
                        lb_result["issues"].append(
                            f"Found {len(http_listeners)} non-encrypted HTTP listeners"
                        )

                    # Check SSL policies for each HTTPS listener
                    for https_listener in https_listeners:
                        ssl_policy = https_listener.get("SslPolicy")

                        # Check if the SSL policy is secure
                        if (
                            ssl_policy
                            and not ssl_policy.startswith("ELBSecurityPolicy-TLS-1-2")
                            and not ssl_policy.startswith("ELBSecurityPolicy-FS-1-2")
                        ):
                            lb_result["compliant"] = False
                            lb_result["issues"].append(
                                f"Using potentially insecure SSL policy: {ssl_policy}"
                            )

                            if "ssl_policies" not in lb_result["checks"]:
                                lb_result["checks"]["ssl_policies"] = []

                            lb_result["checks"]["ssl_policies"].append(
                                {
                                    "name": ssl_policy,
                                    "listener_arn": https_listener.get("ListenerArn"),
                                }
                            )

                # For NLBs, check for TLS listeners
                elif lb_type == "network":
                    tls_listeners = [lst for lst in listeners if lst.get("Protocol") == "TLS"]
                    # tcp_listeners = [lst for lst in listeners if lst.get('Protocol') == 'TCP']

                    lb_result["checks"]["tls_listeners"] = {
                        "count": len(tls_listeners),
                        "total_listeners": len(listeners),
                    }

                    # For NLBs, we don't require all listeners to be TLS
                    # but we check the SSL policies of TLS listeners
                    for tls_listener in tls_listeners:
                        ssl_policy = tls_listener.get("SslPolicy")

                        # Check if the SSL policy is secure
                        if (
                            ssl_policy
                            and not ssl_policy.startswith("ELBSecurityPolicy-TLS-1-2")
                            and not ssl_policy.startswith("ELBSecurityPolicy-FS-1-2")
                        ):
                            lb_result["compliant"] = False
                            lb_result["issues"].append(
                                f"Using potentially insecure SSL policy: {ssl_policy}"
                            )

                            if "ssl_policies" not in lb_result["checks"]:
                                lb_result["checks"]["ssl_policies"] = []

                            lb_result["checks"]["ssl_policies"].append(
                                {
                                    "name": ssl_policy,
                                    "listener_arn": tls_listener.get("ListenerArn"),
                                }
                            )

            except Exception as e:
                print(f"[DEBUG:NetworkSecurity] Error checking listeners for {lb_arn}: {e}")
                lb_result["issues"].append("Error checking listeners")
                lb_result["compliant"] = False

            # Generate remediation steps
            lb_result["remediation"] = []

            if lb_type == "application" and not lb_result["checks"].get(
                "all_listeners_secure", True
            ):
                lb_result["remediation"].append("Replace HTTP listeners with HTTPS listeners")
                lb_result["remediation"].append("Configure HTTP to HTTPS redirection")

            if lb_result["checks"].get("ssl_policies"):
                lb_result["remediation"].append(
                    "Update SSL policy to ELBSecurityPolicy-TLS-1-2-2017-01 or newer"
                )

            # Update counts
            if lb_result["compliant"]:
                results["compliant_resources"] += 1
            else:
                results["non_compliant_resources"] += 1

            results["resource_details"].append(lb_result)

        return results

    except botocore.exceptions.BotoCoreError as e:
        print(f"[DEBUG:NetworkSecurity] Error checking ALB/NLB Load Balancers: {e}")
        await ctx.error(f"Error checking ALB/NLB Load Balancers: {e}")
        return {
            "service": "elbv2",
            "error": str(e),
            "resources_checked": 0,
            "compliant_resources": 0,
            "non_compliant_resources": 0,
            "resource_details": [],
        }


async def check_vpc_endpoints(
    region: str, ec2_client: Any, ctx: Context, network_resources: Dict[str, Any]
) -> Dict[str, Any]:
    """Check VPC endpoints for data-in-transit security best practices."""
    print(f"[DEBUG:NetworkSecurity] Checking VPC endpoints in {region}")

    results = {
        "service": "vpc",
        "resources_checked": 0,
        "compliant_resources": 0,
        "non_compliant_resources": 0,
        "resource_details": [],
    }

    try:
        # Get VPC endpoint list - either from Resource Explorer or directly
        vpc_endpoints = []

        if "error" not in network_resources and "vpc_endpoints" in network_resources.get(
            "resources_by_service", {}
        ):
            # Use Resource Explorer results
            endpoint_resources = network_resources["resources_by_service"]["vpc_endpoints"]
            for resource in endpoint_resources:
                vpc_endpoints.append(resource.get("Arn", ""))
        else:
            # Fall back to direct API call
            response = ec2_client.describe_vpc_endpoints()
            vpc_endpoints = [
                endpoint["VpcEndpointId"] for endpoint in response.get("VpcEndpoints", [])
            ]

        print(
            f"[DEBUG:NetworkSecurity] Found {len(vpc_endpoints)} VPC endpoints in region {region}"
        )
        results["resources_checked"] = len(vpc_endpoints)

        # Check each VPC endpoint
        for endpoint_id in vpc_endpoints:
            # Extract endpoint ID from ARN if necessary
            if endpoint_id.startswith("arn:"):
                endpoint_id = endpoint_id.split("/")[-1]

            # Get endpoint details
            endpoint_response = ec2_client.describe_vpc_endpoints(VpcEndpointIds=[endpoint_id])

            if not endpoint_response.get("VpcEndpoints"):
                continue

            endpoint = endpoint_response["VpcEndpoints"][0]

            endpoint_result = {
                "id": endpoint_id,
                "arn": f"arn:aws:ec2:{region}:{endpoint.get('OwnerId', '')}:vpc-endpoint/{endpoint_id}",
                "type": "vpc_endpoint",
                "service": endpoint.get("ServiceName", "").split(".")[-1],
                "endpoint_type": endpoint.get("VpcEndpointType", ""),
                "compliant": True,
                "issues": [],
                "checks": {},
            }

            # Check endpoint type
            endpoint_type = endpoint.get("VpcEndpointType", "")
            endpoint_result["checks"]["endpoint_type"] = endpoint_type

            # For interface endpoints, check if private DNS is enabled
            if endpoint_type == "Interface":
                private_dns_enabled = endpoint.get("PrivateDnsEnabled", False)
                endpoint_result["checks"]["private_dns_enabled"] = private_dns_enabled

                # For interface endpoints, private DNS should be enabled for secure access
                if not private_dns_enabled:
                    endpoint_result["compliant"] = False
                    endpoint_result["issues"].append(
                        "Private DNS not enabled for interface endpoint"
                    )

            # Check security groups for interface endpoints
            if endpoint_type == "Interface" and "Groups" in endpoint:
                security_groups = endpoint.get("Groups", [])
                endpoint_result["checks"]["security_groups"] = [
                    sg["GroupId"] for sg in security_groups
                ]

                # We don't fail compliance here, but we'll check the security groups separately

            # Generate remediation steps
            endpoint_result["remediation"] = []

            if endpoint_type == "Interface" and not endpoint.get("PrivateDnsEnabled", False):
                endpoint_result["remediation"].append("Enable private DNS for interface endpoint")

            # Update counts
            if endpoint_result["compliant"]:
                results["compliant_resources"] += 1
            else:
                results["non_compliant_resources"] += 1

            results["resource_details"].append(endpoint_result)

        return results

    except botocore.exceptions.BotoCoreError as e:
        print(f"[DEBUG:NetworkSecurity] Error checking VPC endpoints: {e}")
        await ctx.error(f"Error checking VPC endpoints: {e}")
        return {
            "service": "vpc",
            "error": str(e),
            "resources_checked": 0,
            "compliant_resources": 0,
            "non_compliant_resources": 0,
            "resource_details": [],
        }


async def check_security_groups(
    region: str, ec2_client: Any, ctx: Context, network_resources: Dict[str, Any]
) -> Dict[str, Any]:
    """Check security groups for data-in-transit security best practices."""
    print(f"[DEBUG:NetworkSecurity] Checking security groups in {region}")

    results = {
        "service": "security_groups",
        "resources_checked": 0,
        "compliant_resources": 0,
        "non_compliant_resources": 0,
        "resource_details": [],
    }

    try:
        # Get security group list - either from Resource Explorer or directly
        security_groups = []

        if "error" not in network_resources and "security_groups" in network_resources.get(
            "resources_by_service", {}
        ):
            # Use Resource Explorer results
            sg_resources = network_resources["resources_by_service"]["security_groups"]
            for resource in sg_resources:
                sg_id = resource.get("Arn", "").split("/")[-1]
                security_groups.append(sg_id)
        else:
            # Fall back to direct API call
            response = ec2_client.describe_security_groups()
            security_groups = [sg["GroupId"] for sg in response.get("SecurityGroups", [])]

        print(
            f"[DEBUG:NetworkSecurity] Found {len(security_groups)} security groups in region {region}"
        )
        results["resources_checked"] = len(security_groups)

        # Define sensitive ports for data in transit
        sensitive_ports = {
            80: "HTTP",
            23: "Telnet",
            21: "FTP",
            20: "FTP-Data",
            25: "SMTP",
            110: "POP3",
            143: "IMAP",
            69: "TFTP",
        }

        # Check each security group
        for sg_id in security_groups:
            # Get security group details
            sg_response = ec2_client.describe_security_groups(GroupIds=[sg_id])

            if not sg_response.get("SecurityGroups"):
                continue

            sg = sg_response["SecurityGroups"][0]

            sg_result = {
                "id": sg_id,
                "name": sg.get("GroupName", ""),
                "arn": f"arn:aws:ec2:{region}:{sg.get('OwnerId', '')}:security-group/{sg_id}",
                "type": "security_group",
                "vpc_id": sg.get("VpcId", ""),
                "compliant": True,
                "issues": [],
                "checks": {},
            }

            # Check for open sensitive ports
            open_sensitive_ports = []

            for rule in sg.get("IpPermissions", []):
                from_port = rule.get("FromPort")
                to_port = rule.get("ToPort")

                # Skip if ports are not defined
                if from_port is None or to_port is None:
                    continue

                # Check for sensitive ports
                for port in range(from_port, to_port + 1):
                    if port in sensitive_ports:
                        # Check if open to the world (0.0.0.0/0)
                        for ip_range in rule.get("IpRanges", []):
                            if ip_range.get("CidrIp") == "0.0.0.0/0":
                                open_sensitive_ports.append(
                                    {
                                        "port": port,
                                        "service": sensitive_ports[port],
                                        "cidr": "0.0.0.0/0",
                                    }
                                )
                                break

            sg_result["checks"]["open_sensitive_ports"] = open_sensitive_ports

            if open_sensitive_ports:
                sg_result["compliant"] = False
                for port_info in open_sensitive_ports:
                    sg_result["issues"].append(
                        f"Port {port_info['port']} ({port_info['service']}) open to the world"
                    )

            # Generate remediation steps
            sg_result["remediation"] = []

            if open_sensitive_ports:
                sg_result["remediation"].append(
                    "Restrict access to sensitive ports to specific IP ranges"
                )
                sg_result["remediation"].append(
                    "Replace insecure protocols with secure alternatives (e.g., HTTPS instead of HTTP)"
                )
                sg_result["remediation"].append(
                    "Use security group source references instead of CIDR blocks where possible"
                )

            # Update counts
            if sg_result["compliant"]:
                results["compliant_resources"] += 1
            else:
                results["non_compliant_resources"] += 1

            results["resource_details"].append(sg_result)

        return results

    except botocore.exceptions.BotoCoreError as e:
        print(f"[DEBUG:NetworkSecurity] Error checking security groups: {e}")
        await ctx.error(f"Error checking security groups: {e}")
        return {
            "service": "security_groups",
            "error": str(e),
            "resources_checked": 0,
            "compliant_resources": 0,
            "non_compliant_resources": 0,
            "resource_details": [],
        }


async def check_api_gateway(
    region: str, apigw_client: Any, ctx: Context, network_resources: Dict[str, Any]
) -> Dict[str, Any]:
    """Check API Gateway for data-in-transit security best practices."""
    print(f"[DEBUG:NetworkSecurity] Checking API Gateway in {region}")

    results = {
        "service": "apigateway",
        "resources_checked": 0,
        "compliant_resources": 0,
        "non_compliant_resources": 0,
        "resource_details": [],
    }

    try:
        # Get API list - either from Resource Explorer or directly
        apis = []

        if "error" not in network_resources and "apigateway" in network_resources.get(
            "resources_by_service", {}
        ):
            # Use Resource Explorer results
            api_resources = network_resources["resources_by_service"]["apigateway"]
            for resource in api_resources:
                api_id = resource.get("Arn", "").split("/")[-1]
                apis.append(api_id)
        else:
            # Fall back to direct API call
            response = apigw_client.get_rest_apis()
            apis = [api["id"] for api in response.get("items", [])]

        print(f"[DEBUG:NetworkSecurity] Found {len(apis)} APIs in region {region}")
        results["resources_checked"] = len(apis)

        # Check each API
        for api_id in apis:
            # Get API details
            api_response = apigw_client.get_rest_api(restApiId=api_id)

            api_result = {
                "id": api_id,
                "name": api_response.get("name", ""),
                "arn": f"arn:aws:apigateway:{region}::/restapis/{api_id}",
                "type": "api_gateway",
                "compliant": True,
                "issues": [],
                "checks": {},
            }

            # Check for HTTPS enforcement
            try:
                stages_response = apigw_client.get_stages(restApiId=api_id)
                stages = stages_response.get("item", [])

                for stage in stages:
                    stage_name = stage.get("stageName", "")

                    # Check if HTTPS is enforced
                    method_settings = stage.get("methodSettings", {})

                    # Default to not enforced
                    https_enforced = False

                    # Check if there's a '*/*' setting that enforces HTTPS
                    if "*/*" in method_settings:
                        https_enforced = method_settings["*/*"].get("requireHttps", False)

                    if not https_enforced:
                        api_result["compliant"] = False
                        api_result["issues"].append(f"HTTPS not enforced for stage: {stage_name}")

                        if "stages" not in api_result["checks"]:
                            api_result["checks"]["stages"] = []

                        api_result["checks"]["stages"].append(
                            {"name": stage_name, "https_enforced": https_enforced}
                        )
            except Exception as e:
                print(f"[DEBUG:NetworkSecurity] Error checking stages for API {api_id}: {e}")
                api_result["issues"].append("Error checking API stages")

            # Check for custom domain names with secure TLS
            try:
                domains_response = apigw_client.get_domain_names()
                domains = domains_response.get("items", [])

                for domain in domains:
                    domain_name = domain.get("domainName", "")

                    # Check if this domain is mapped to our API
                    mappings_response = apigw_client.get_base_path_mappings(domainName=domain_name)
                    mappings = mappings_response.get("items", [])

                    for mapping in mappings:
                        if mapping.get("restApiId") == api_id:
                            # Check TLS version
                            security_policy = domain.get("securityPolicy", "")

                            if security_policy != "TLS_1_2":
                                api_result["compliant"] = False
                                api_result["issues"].append(
                                    f"Domain {domain_name} using insecure TLS policy: {security_policy}"
                                )

                                if "domains" not in api_result["checks"]:
                                    api_result["checks"]["domains"] = []

                                api_result["checks"]["domains"].append(
                                    {"name": domain_name, "security_policy": security_policy}
                                )
            except Exception as e:
                print(f"[DEBUG:NetworkSecurity] Error checking domains for API {api_id}: {e}")
                # Don't fail compliance just because we couldn't check domains

            # Generate remediation steps
            api_result["remediation"] = []

            if "stages" in api_result["checks"] and any(
                not stage.get("https_enforced", False)
                for stage in api_result["checks"].get("stages", [])
            ):
                api_result["remediation"].append("Enable 'Require HTTPS' in method settings")

            if "domains" in api_result["checks"] and any(
                domain.get("security_policy") != "TLS_1_2"
                for domain in api_result["checks"].get("domains", [])
            ):
                api_result["remediation"].append("Update custom domain security policy to TLS_1_2")

            # Update counts
            if api_result["compliant"]:
                results["compliant_resources"] += 1
            else:
                results["non_compliant_resources"] += 1

            results["resource_details"].append(api_result)

        return results

    except botocore.exceptions.BotoCoreError as e:
        print(f"[DEBUG:NetworkSecurity] Error checking API Gateway: {e}")
        await ctx.error(f"Error checking API Gateway: {e}")
        return {
            "service": "apigateway",
            "error": str(e),
            "resources_checked": 0,
            "compliant_resources": 0,
            "non_compliant_resources": 0,
            "resource_details": [],
        }


async def check_cloudfront_distributions(
    region: str, cf_client: Any, ctx: Context, network_resources: Dict[str, Any]
) -> Dict[str, Any]:
    """Check CloudFront distributions for data-in-transit security best practices."""
    print("[DEBUG:NetworkSecurity] Checking CloudFront distributions")

    results = {
        "service": "cloudfront",
        "resources_checked": 0,
        "compliant_resources": 0,
        "non_compliant_resources": 0,
        "resource_details": [],
    }

    try:
        # Get distribution list - either from Resource Explorer or directly
        distributions = []

        if "error" not in network_resources and "cloudfront" in network_resources.get(
            "resources_by_service", {}
        ):
            # Use Resource Explorer results
            cf_resources = network_resources["resources_by_service"]["cloudfront"]
            for resource in cf_resources:
                dist_id = resource.get("Arn", "").split("/")[-1]
                distributions.append(dist_id)
        else:
            # Fall back to direct API call
            response = cf_client.list_distributions()
            if "DistributionList" in response and "Items" in response["DistributionList"]:
                distributions = [dist["Id"] for dist in response["DistributionList"]["Items"]]

        print(f"[DEBUG:NetworkSecurity] Found {len(distributions)} CloudFront distributions")
        results["resources_checked"] = len(distributions)

        # Check each distribution
        for dist_id in distributions:
            # Get distribution details
            dist_response = cf_client.get_distribution(Id=dist_id)

            if "Distribution" not in dist_response:
                continue

            dist = dist_response["Distribution"]
            config = dist.get("DistributionConfig", {})

            dist_result = {
                "id": dist_id,
                "arn": f"arn:aws:cloudfront::{dist.get('Id', '')}:distribution/{dist_id}",
                "domain_name": dist.get("DomainName", ""),
                "type": "cloudfront_distribution",
                "compliant": True,
                "issues": [],
                "checks": {},
            }

            # Check if HTTPS is required
            viewer_protocol_policy = None
            default_cache_behavior = config.get("DefaultCacheBehavior", {})
            if default_cache_behavior:
                viewer_protocol_policy = default_cache_behavior.get("ViewerProtocolPolicy")

            dist_result["checks"]["viewer_protocol_policy"] = viewer_protocol_policy

            if (
                viewer_protocol_policy != "redirect-to-https"
                and viewer_protocol_policy != "https-only"
            ):
                dist_result["compliant"] = False
                dist_result["issues"].append(
                    f"Viewer protocol policy not enforcing HTTPS: {viewer_protocol_policy}"
                )

            # Check TLS version
            ssl_protocol_version = config.get("ViewerCertificate", {}).get(
                "MinimumProtocolVersion"
            )
            dist_result["checks"]["minimum_tls_version"] = ssl_protocol_version

            if ssl_protocol_version and ssl_protocol_version not in [
                "TLSv1.2_2018",
                "TLSv1.2_2019",
                "TLSv1.2_2021",
            ]:
                dist_result["compliant"] = False
                dist_result["issues"].append(f"Using outdated TLS version: {ssl_protocol_version}")

            # Check origin protocol policy for S3 origins
            origins = config.get("Origins", {}).get("Items", [])
            s3_origins_without_oai = []

            for origin in origins:
                if "s3" in origin.get("DomainName", "").lower():
                    # Check if using OAI or OAC
                    has_oai = (
                        "S3OriginConfig" in origin
                        and "OriginAccessIdentity" in origin["S3OriginConfig"]
                        and origin["S3OriginConfig"]["OriginAccessIdentity"]
                    )
                    has_oac = "OriginAccessControlId" in origin

                    if not has_oai and not has_oac:
                        s3_origins_without_oai.append(origin.get("Id", "unknown"))

            if s3_origins_without_oai:
                dist_result["compliant"] = False
                dist_result["issues"].append(
                    f"S3 origins without OAI/OAC: {', '.join(s3_origins_without_oai)}"
                )
                dist_result["checks"]["s3_origins_without_oai"] = s3_origins_without_oai

            # Generate remediation steps
            dist_result["remediation"] = []

            if (
                viewer_protocol_policy != "redirect-to-https"
                and viewer_protocol_policy != "https-only"
            ):
                dist_result["remediation"].append(
                    "Set ViewerProtocolPolicy to 'redirect-to-https' or 'https-only'"
                )

            if ssl_protocol_version and ssl_protocol_version not in [
                "TLSv1.2_2018",
                "TLSv1.2_2019",
                "TLSv1.2_2021",
            ]:
                dist_result["remediation"].append("Update MinimumProtocolVersion to TLSv1.2_2021")

            if s3_origins_without_oai:
                dist_result["remediation"].append(
                    "Configure Origin Access Identity (OAI) or Origin Access Control (OAC) for S3 origins"
                )

            # Update counts
            if dist_result["compliant"]:
                results["compliant_resources"] += 1
            else:
                results["non_compliant_resources"] += 1

            results["resource_details"].append(dist_result)

        return results

    except botocore.exceptions.BotoCoreError as e:
        print(f"[DEBUG:NetworkSecurity] Error checking CloudFront distributions: {e}")
        await ctx.error(f"Error checking CloudFront distributions: {e}")
        return {
            "service": "cloudfront",
            "error": str(e),
            "resources_checked": 0,
            "compliant_resources": 0,
            "non_compliant_resources": 0,
            "resource_details": [],
        }
