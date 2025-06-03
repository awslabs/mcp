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
API for getting the status of ECS deployments.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from awslabs.ecs_mcp_server.utils.aws import get_aws_client

logger = logging.getLogger(__name__)


async def get_deployment_status(
    app_name: str,
    cluster_name: Optional[str] = None,
    stack_name: Optional[str] = None,
    service_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Gets the status of an ECS deployment and returns the ALB URL.

    This function also polls the CloudFormation stack status to provide
    more complete deployment information. When deployment is successful,
    it provides guidance on setting up custom domains and HTTPS.

    Args:
        app_name: Name of the application
        cluster_name: Name of the ECS cluster (optional, defaults to app_name)
        stack_name: Name of the CloudFormation stack
                   (optional, defaults to {app_name}-ecs-infrastructure)
        service_name: Name of the ECS service (optional, defaults to {app_name}-service)

    Returns:
        Dict containing deployment status, CloudFormation stack status, ALB URL,
        and guidance for custom domain and HTTPS setup when deployment is successful
    """
    logger.info(f"Getting deployment status for {app_name}")

    # Use provided cluster name or default
    cluster = cluster_name or f"{app_name}-cluster"

    # Use provided service name or default
    service_name_to_check = service_name or f"{app_name}-service"

    # Get CloudFormation stack status
    cfn_stack_name, stack_status = await _find_cloudformation_stack(app_name, stack_name)

    # If stack doesn't exist or is in a failed state, return early
    if not cfn_stack_name or stack_status.get("status") in [
        "NOT_FOUND",
        "ROLLBACK_COMPLETE",
        "ROLLBACK_IN_PROGRESS",
        "DELETE_COMPLETE",
    ]:
        return {
            "app_name": app_name,
            "status": "INFRASTRUCTURE_UNAVAILABLE",
            "stack_status": stack_status,
            "message": (
                f"Infrastructure for {app_name} is not available: {stack_status.get('status')}"
            ),
            "alb_url": None,
        }

    # Get ALB URL
    alb_url = await _get_alb_url(app_name, cfn_stack_name)

    # Get service status
    ecs_client = await get_aws_client("ecs")
    try:
        service_response = ecs_client.describe_services(
            cluster=cluster, services=[service_name_to_check]
        )

        if not service_response["services"]:
            return {
                "app_name": app_name,
                "status": "NOT_FOUND",
                "stack_status": stack_status,
                "message": f"Service {service_name_to_check} not found in cluster {cluster}",
                "alb_url": None,
            }

        service = service_response["services"][0]
        service_status = service["status"]

        # Get deployment status
        deployments = service.get("deployments", [])
        deployment_status = "UNKNOWN"
        if deployments:
            primary_deployment = next(
                (d for d in deployments if d.get("status") == "PRIMARY"), None
            )
            if primary_deployment:
                if primary_deployment.get("rolloutState"):
                    deployment_status = primary_deployment["rolloutState"]
                else:
                    # For older ECS versions
                    running_count = primary_deployment.get("runningCount", 0)
                    desired_count = primary_deployment.get("desiredCount", 0)
                    if running_count == desired_count and desired_count > 0:
                        deployment_status = "COMPLETED"
                    else:
                        deployment_status = "IN_PROGRESS"

        # Get task status
        tasks_response = ecs_client.list_tasks(cluster=cluster, serviceName=service_name_to_check)

        task_status = []
        if tasks_response.get("taskArns"):
            task_details = ecs_client.describe_tasks(
                cluster=cluster, tasks=tasks_response["taskArns"]
            )

            for task in task_details.get("tasks", []):
                task_status.append(
                    {
                        "task_id": task["taskArn"].split("/")[-1],
                        "status": task["lastStatus"],
                        "health_status": task.get("healthStatus", "UNKNOWN"),
                        "started_at": (
                            task.get("startedAt", "").isoformat() if task.get("startedAt") else None
                        ),
                    }
                )

        # Determine overall deployment status
        overall_status = "IN_PROGRESS"
        if (
            stack_status.get("status") in ["CREATE_COMPLETE", "UPDATE_COMPLETE"]
        ) and deployment_status == "COMPLETED":
            if (
                service.get("runningCount", 0) == service.get("desiredCount", 0)
                and service.get("desiredCount", 0) > 0
            ):
                overall_status = "COMPLETE"
        elif "FAIL" in stack_status.get("status", "") or "ROLLBACK" in stack_status.get(
            "status", ""
        ):
            overall_status = "FAILED"
        # Generate custom domain and HTTPS guidance if deployment is complete
        custom_domain_guidance = None
        if overall_status == "COMPLETE" and alb_url:
            custom_domain_guidance = _generate_custom_domain_guidance(app_name, alb_url)

        return {
            "app_name": app_name,
            "cluster": cluster,
            "status": overall_status,
            "service_status": service_status,
            "deployment_status": deployment_status,
            "stack_status": stack_status,
            "alb_url": alb_url,
            "tasks": task_status,
            "running_count": service.get("runningCount", 0),
            "desired_count": service.get("desiredCount", 0),
            "pending_count": service.get("pendingCount", 0),
            "message": f"Application {app_name} deployment status: {overall_status}",
            "custom_domain_guidance": custom_domain_guidance,
        }

    except Exception as e:
        logger.error(f"Error getting deployment status: {e}")
        return {
            "app_name": app_name,
            "status": "ERROR",
            "stack_status": stack_status,
            "message": f"Error getting deployment status: {str(e)}",
            "alb_url": alb_url if "alb_url" in locals() else None,
        }


async def _get_cfn_stack_status(stack_name: str) -> Dict[str, Any]:
    """
    Gets the status of a CloudFormation stack.

    Args:
        stack_name: Name of the CloudFormation stack

    Returns:
        Dictionary containing stack status information
    """
    cloudformation = await get_aws_client("cloudformation")

    try:
        # Use boto3 to describe the stack
        response = cloudformation.describe_stacks(StackName=stack_name)

        if not response.get("Stacks"):
            return {"status": "NOT_FOUND", "details": "Stack not found"}

        stack = response["Stacks"][0]

        # Get stack events for more detailed information
        events_response = cloudformation.describe_stack_events(StackName=stack_name)
        recent_events = events_response.get("StackEvents", [])[:5]  # Get 5 most recent events

        formatted_events = []
        for event in recent_events:
            formatted_events.append(
                {
                    "timestamp": (
                        event.get("Timestamp").isoformat() if event.get("Timestamp") else None
                    ),
                    "resource_type": event.get("ResourceType"),
                    "status": event.get("ResourceStatus"),
                    "reason": event.get("ResourceStatusReason", ""),
                }
            )

        # Extract outputs
        outputs = {}
        for output in stack.get("Outputs", []):
            outputs[output["OutputKey"]] = output["OutputValue"]

        return {
            "status": stack.get("StackStatus"),
            "creation_time": (
                stack.get("CreationTime").isoformat() if stack.get("CreationTime") else None
            ),
            "last_updated_time": (
                stack.get("LastUpdatedTime").isoformat() if stack.get("LastUpdatedTime") else None
            ),
            "outputs": outputs,
            "recent_events": formatted_events,
        }
    except Exception as e:
        logger.error(f"Error getting CloudFormation stack status: {e}")
        if "does not exist" in str(e):
            return {"status": "NOT_FOUND", "details": f"Stack {stack_name} not found"}
        return {"status": "ERROR", "details": str(e)}


def _get_stack_names_to_try(app_name: str, stack_name: Optional[str] = None) -> List[str]:
    """
    Get an ordered list of stack names to try.

    Args:
        app_name: Name of the application
        stack_name: A specific stack name to try first (optional)

    Returns:
        List of stack names to try in order of priority
    """
    STACK_NAME_PATTERNS = ["{}-ecs-infrastructure", "{}-ecs"]
    stack_names_to_try = []

    # If a specific stack name is provided, try it first
    if stack_name:
        stack_names_to_try.append(stack_name)

    # Add common pattern-based names
    for pattern in STACK_NAME_PATTERNS:
        name = pattern.format(app_name)
        if name not in stack_names_to_try:
            stack_names_to_try.append(name)

    return stack_names_to_try


async def _find_cloudformation_stack(
    app_name: str, stack_name: Optional[str] = None
) -> Tuple[Optional[str], Dict[str, Any]]:
    """
    Finds a CloudFormation stack using provided name or common patterns.

    Args:
        app_name: Name of the application
        stack_name: Specific stack name to try first (optional)

    Returns:
        Tuple of (stack_name or None, stack_status dict)
    """
    # Get stack names to try using the helper function
    stack_names_to_try = _get_stack_names_to_try(app_name, stack_name)

    # Try each stack name until we find one that exists
    for name in stack_names_to_try:
        current_status = await _get_cfn_stack_status(name)
        if current_status.get("status") != "NOT_FOUND":
            logger.info(f"Found stack with name: {name}")
            return name, current_status
        logger.debug(f"Stack {name} not found, trying next pattern if available")

    # If no stack found, return None with NOT_FOUND status
    return None, {"status": "NOT_FOUND", "details": "No stack found with any naming pattern"}


async def _get_alb_url(app_name: str, known_stack_name: Optional[str] = None) -> Optional[str]:
    """
    Gets the ALB URL from CloudFormation outputs.

    Args:
        app_name: Name of the application
        known_stack_name: If a valid stack name is already known, pass it to avoid extra API calls

    Returns:
        The ALB URL or None if not found
    """
    cloudformation = await get_aws_client("cloudformation")

    # Get stack names to try using the helper function
    stack_names_to_try = _get_stack_names_to_try(app_name, known_stack_name)

    for stack_name in stack_names_to_try:
        try:
            response = cloudformation.describe_stacks(StackName=stack_name)

            for output in response["Stacks"][0]["Outputs"]:
                # Check for both possible output key names
                if output["OutputKey"] in ["LoadBalancerDNS", "LoadBalancerUrl"]:
                    url = output["OutputValue"]
                    # Ensure URL has http:// prefix
                    if not url.startswith("http://") and not url.startswith("https://"):
                        url = f"http://{url}"
                    return url
        except Exception as e:
            logger.debug(f"Error getting ALB URL from stack {stack_name}: {e}")

    logger.error(f"Could not find ALB URL for application {app_name}")
    return None


def _generate_custom_domain_guidance(app_name: str, alb_url: str) -> Dict[str, Any]:
    """
    Generates guidance for setting up a custom domain and HTTPS for the deployed application.

    Args:
        app_name: Name of the application
        alb_url: The ALB URL for the deployed application

    Returns:
        Dictionary containing guidance for custom domain setup and HTTPS configuration
    """
    # Extract the ALB hostname from the URL
    alb_hostname = alb_url.replace("http://", "").strip("/")

    return {
        "custom_domain": {
            "title": "Setting up a Custom Domain",
            "description": (
                "Your application is currently accessible via the ALB URL. "
                "For a more professional setup, you can use a custom domain."
            ),
            "steps": [
                "Register a domain through Route 53 or another domain registrar "
                "if you don't already have one.",
                f"Create a CNAME record pointing to the ALB hostname: {alb_hostname}",
                "If using Route 53, create a hosted zone for your domain "
                "and add an alias record pointing to the ALB.",
            ],
            "route53_commands": [
                "# Create a hosted zone for your domain",
                (
                    f"aws route53 create-hosted-zone --name yourdomain.com "
                    f"--caller-reference {app_name}-$(date +%s)"
                ),
                "",
                "# Add an alias record pointing to the ALB",
                (
                    "aws route53 change-resource-record-sets --hosted-zone-id YOUR_HOSTED_ZONE_ID "
                    '--change-batch \'{"Changes": [{"Action": "CREATE", '
                    '"ResourceRecordSet": {"Name": "yourdomain.com", "Type": "A", '
                    '"AliasTarget": {"HostedZoneId": "YOUR_ALB_HOSTED_ZONE_ID", '
                    '"DNSName": "' + alb_hostname + '", "EvaluateTargetHealth": true}}}]}\''
                ),
            ],
        },
        "https_setup": {
            "title": "Setting up HTTPS with AWS Certificate Manager",
            "description": (
                "Secure your application with HTTPS using AWS Certificate Manager "
                "(ACM) and update your ALB listener."
            ),
            "steps": [
                "Request a certificate through AWS Certificate Manager for your domain.",
                "Validate the certificate (typically through DNS validation).",
                "Add an HTTPS listener to your ALB that uses the certificate.",
                "Optional: Redirect HTTP traffic to HTTPS for better security.",
            ],
            "acm_commands": [
                "# Request a certificate for your domain",
                "aws acm request-certificate --domain-name yourdomain.com --validation-method DNS",
                "",
                "# Get the certificate ARN",
                (
                    "aws acm list-certificates --query "
                    "\"CertificateSummaryList[?DomainName=='yourdomain.com'].CertificateArn\" "
                    "--output text"
                ),
                "",
                "# Add an HTTPS listener to your ALB",
                "aws elbv2 create-listener \\",
                "  --load-balancer-arn YOUR_ALB_ARN \\",
                "  --protocol HTTPS \\",
                "  --port 443 \\",
                "  --certificates CertificateArn=YOUR_CERTIFICATE_ARN \\",
                "  --ssl-policy ELBSecurityPolicy-2016-08 \\",
                "  --default-actions Type=forward,TargetGroupArn=YOUR_TARGET_GROUP_ARN",
                "",
                "# Optional: Create a redirect from HTTP to HTTPS",
                "aws elbv2 modify-listener \\",
                "  --listener-arn YOUR_HTTP_LISTENER_ARN \\",
                (
                    '  --default-actions Type=redirect,RedirectConfig=\'{"Protocol":"HTTPS",'
                    '"Port":"443","StatusCode":"HTTP_301"}\''
                ),
            ],
        },
        "cloudformation_update": {
            "title": "Update Your CloudFormation Stack for HTTPS",
            "description": "You can also update your CloudFormation stack to add HTTPS support.",
            "steps": [
                "Download your current CloudFormation template.",
                "Add an HTTPS listener to the ALB configuration.",
                "Update the stack with the modified template.",
            ],
            "commands": [
                "# Download your current CloudFormation template",
                (
                    f"aws cloudformation get-template --stack-name {app_name}-ecs-infrastructure "
                    f"--query TemplateBody --output json > {app_name}-template.json"
                ),
                "",
                "# After modifying the template, update the stack",
                (
                    f"aws cloudformation update-stack --stack-name {app_name}-ecs-infrastructure "
                    f"--template-body file://{app_name}-template.json --capabilities CAPABILITY_IAM"
                ),
            ],
        },
        "next_steps": [
            "Set up monitoring and alerts for your application using CloudWatch.",
            "Configure auto-scaling policies based on your application's traffic patterns.",
            "Implement a CI/CD pipeline for automated deployments.",
        ],
    }
