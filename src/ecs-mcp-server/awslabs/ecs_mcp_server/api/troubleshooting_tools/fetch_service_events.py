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
"""
Service-level diagnostics for ECS services.

This module provides a function to analyze ECS service events and configuration to identify
service-level issues that may be affecting deployments.
"""

import datetime
import logging
from typing import Any, Dict, List, Optional

from botocore.exceptions import ClientError

from awslabs.ecs_mcp_server.utils.aws import get_aws_client
from awslabs.ecs_mcp_server.utils.time_utils import calculate_time_window

logger = logging.getLogger(__name__)


def _extract_filtered_events(
    service: Dict[str, Any], start_time: datetime.datetime, end_time: datetime.datetime
) -> List[Dict[str, Any]]:
    """Extract and filter service events by time window.

    Parameters
    ----------
    service : Dict[str, Any]
        Service description from ECS API
    start_time : datetime
        Start time for filtering events (timezone-aware)
    end_time : datetime
        End time for filtering events (timezone-aware)

    Returns
    -------
    List[Dict[str, Any]]
        List of filtered and formatted events
    """
    events = service.get("events", [])
    if not events:
        return []

    filtered_events = []

    for event in events:
        event_time = event.get("createdAt")
        if not event_time:
            continue

        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=datetime.timezone.utc)

        # Include events within the time window
        if start_time <= event_time <= end_time:
            filtered_events.append(
                {
                    "message": event["message"],
                    "timestamp": event_time.isoformat(),
                    "id": event.get("id", "unknown"),
                }
            )

    return filtered_events


async def _check_target_group_health(elb_client, target_group_arn: str) -> Optional[Dict[str, Any]]:
    """Check target group health and return any unhealthy targets."""
    try:
        tg_health = elb_client.describe_target_health(TargetGroupArn=target_group_arn)

        # Find unhealthy targets
        unhealthy_targets = [
            t
            for t in tg_health.get("TargetHealthDescriptions", [])
            if t.get("TargetHealth", {}).get("State") != "healthy"
        ]

        if unhealthy_targets:
            return {
                "type": "unhealthy_targets",
                "count": len(unhealthy_targets),
                "details": unhealthy_targets,
            }

        return None
    except ClientError as error:
        return {"type": "health_check_error", "error": str(error)}


async def _check_port_mismatch(
    elb_client, target_group_arn: str, container_port: int
) -> Optional[Dict[str, Any]]:
    """Check if container port and target group port match."""
    try:
        tg = elb_client.describe_target_groups(TargetGroupArns=[target_group_arn])
        if tg["TargetGroups"] and tg["TargetGroups"][0]["Port"] != container_port:
            return {
                "type": "port_mismatch",
                "container_port": container_port,
                "target_group_port": tg["TargetGroups"][0]["Port"],
            }
        return None
    except ClientError as error:
        return {"type": "target_group_error", "error": str(error)}


async def _analyze_load_balancer_issues(service: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Analyze load balancer configuration for common issues."""
    load_balancers = service.get("loadBalancers", [])
    if not load_balancers:
        return []

    load_balancer_issues = []
    elb = await get_aws_client("elbv2")

    for lb in load_balancers:
        lb_issues = []

        if "targetGroupArn" in lb:
            # Check target health
            health_issue = await _check_target_group_health(elb, lb["targetGroupArn"])
            if health_issue:
                lb_issues.append(health_issue)

            # Check port mismatch if container port is specified
            if "containerPort" in lb:
                port_issue = await _check_port_mismatch(
                    elb, lb["targetGroupArn"], lb["containerPort"]
                )
                if port_issue:
                    lb_issues.append(port_issue)

        if lb_issues:
            load_balancer_issues.append({"load_balancer": lb, "issues": lb_issues})

    return load_balancer_issues


async def fetch_service_events(
    app_name: str,
    cluster_name: str,
    service_name: str,
    time_window: int = 3600,
    start_time: Optional[datetime.datetime] = None,
    end_time: Optional[datetime.datetime] = None,
) -> Dict[str, Any]:
    """
    Service-level diagnostics for ECS services.

    Parameters
    ----------
    app_name : str
        The name of the application to analyze
    cluster_name : str
        The name of the ECS cluster
    service_name : str
        The name of the ECS service to analyze
    time_window : int, optional
        Time window in seconds to look back for events (default: 3600)
    start_time : datetime, optional
        Explicit start time for the analysis window
        (UTC, takes precedence over time_window if provided)
    end_time : datetime, optional
        Explicit end time for the analysis window (UTC, defaults to current time if not provided)

    Returns
    -------
    Dict[str, Any]
        Service events, configuration issues, deployment status
    """
    try:
        # Calculate time window
        actual_start_time, actual_end_time = calculate_time_window(
            time_window, start_time, end_time
        )

        response = {
            "status": "success",
            "service_exists": False,
            "events": [],
            "issues": [],
            "raw_data": {},
        }

        # Initialize ECS client using get_aws_client
        ecs = await get_aws_client("ecs")

        # Check if service exists
        try:
            services = ecs.describe_services(cluster=cluster_name, services=[service_name])

            if not services["services"] or services["services"][0]["status"] == "INACTIVE":
                response["message"] = (
                    f"Service '{service_name}' not found in cluster '{cluster_name}'"
                )
                return response

            service = services["services"][0]
            response["service_exists"] = True
            response["raw_data"]["service"] = service

            # Extract service events
            events = _extract_filtered_events(service, actual_start_time, actual_end_time)
            response["events"] = events

            # Analyze deployment status
            deployments = service.get("deployments", [])
            primary_deployment = next(
                (d for d in deployments if d.get("status") == "PRIMARY"), None
            )

            if primary_deployment:
                response["deployment"] = {
                    "id": primary_deployment.get("id", "unknown"),
                    "status": primary_deployment.get("status", "unknown"),
                    "rollout_state": primary_deployment.get("rolloutState", "unknown"),
                    "rollout_state_reason": primary_deployment.get("rolloutStateReason", ""),
                    "desired_count": primary_deployment.get("desiredCount", 0),
                    "pending_count": primary_deployment.get("pendingCount", 0),
                    "running_count": primary_deployment.get("runningCount", 0),
                    "created_at": (
                        primary_deployment.get("createdAt").isoformat()
                        if primary_deployment.get("createdAt")
                        else None
                    ),
                    "updated_at": (
                        primary_deployment.get("updatedAt").isoformat()
                        if primary_deployment.get("updatedAt")
                        else None
                    ),
                }

                # Identify potential issues
                issues = []

                # Check for failed deployment
                if primary_deployment.get("rolloutState") == "FAILED":
                    issues.append(
                        {
                            "type": "failed_deployment",
                            "reason": primary_deployment.get(
                                "rolloutStateReason", "Unknown reason"
                            ),
                        }
                    )

                # Check for stalled deployment
                elif primary_deployment.get("pendingCount", 0) > 0 and primary_deployment.get(
                    "runningCount", 0
                ) < primary_deployment.get("desiredCount", 0):
                    issues.append(
                        {
                            "type": "stalled_deployment",
                            "pending_count": primary_deployment.get("pendingCount", 0),
                            "running_count": primary_deployment.get("runningCount", 0),
                            "desired_count": primary_deployment.get("desiredCount", 0),
                        }
                    )

                # Check for load balancer issues
                lb_issues = await _analyze_load_balancer_issues(service)
                if lb_issues:
                    issues.extend(lb_issues)

                response["issues"] = issues

            # Add summary message
            if events:
                response["message"] = (
                    f"Found {len(events)} events for service '{service_name}' "
                    f"in the specified time window"
                )
            else:
                response["message"] = (
                    f"No events found for service '{service_name}' in the specified time window"
                )

            return response

        except ClientError as e:
            response["status"] = "error"
            response["error"] = f"AWS API error: {str(e)}"
            logger.error(f"Error in fetch_service_events: {e}")
            return response

    except Exception as e:
        logger.error(f"Error in fetch_service_events: {e}")
        return {"status": "error", "error": str(e)}
