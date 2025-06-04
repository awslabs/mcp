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
Infrastructure-level diagnostics for CloudFormation stacks.

This module provides a function to analyze CloudFormation stacks, check stack status,
identify failed resources, and extract error messages to help diagnose infrastructure-level issues.
"""

import datetime
import logging
from typing import Any, Dict

from botocore.exceptions import ClientError

from awslabs.ecs_mcp_server.utils.aws import get_aws_client

logger = logging.getLogger(__name__)


async def fetch_cloudformation_status(stack_id: str) -> Dict[str, Any]:
    """
    Infrastructure-level diagnostics for CloudFormation stacks.

    Parameters
    ----------
    stack_id : str
        The CloudFormation stack identifier to analyze

    Returns
    -------
    Dict[str, Any]
        Stack status, resources, failure reasons, and raw events
    """
    try:
        response = {
            "status": "success",
            "stack_exists": False,
            "stack_status": None,
            "resources": [],
            "failure_reasons": [],
            "raw_events": [],
        }

        # Initialize CloudFormation client using get_aws_client
        cloudformation = await get_aws_client("cloudformation")

        # Check if stack exists
        try:
            stack_response = cloudformation.describe_stacks(StackName=stack_id)
            stack = stack_response["Stacks"][0]
            response["stack_exists"] = True
            response["stack_status"] = stack["StackStatus"]

            # Get stack resources
            try:
                resources_response = cloudformation.list_stack_resources(StackName=stack_id)
                response["resources"] = resources_response["StackResourceSummaries"]

                # Extract failed resources
                for resource in response["resources"]:
                    if resource["ResourceStatus"].endswith("FAILED"):
                        failure_reason = {
                            "logical_id": resource["LogicalResourceId"],
                            "physical_id": resource.get("PhysicalResourceId", "N/A"),
                            "resource_type": resource["ResourceType"],
                            "status": resource["ResourceStatus"],
                            "reason": resource.get("ResourceStatusReason", "No reason provided"),
                        }
                        response["failure_reasons"].append(failure_reason)
            except ClientError as e:
                response["resources_error"] = str(e)

            # Get stack events for deeper analysis
            try:
                events_response = cloudformation.describe_stack_events(StackName=stack_id)
                response["raw_events"] = events_response["StackEvents"]

                # Extract additional failure reasons from events
                for event in response["raw_events"]:
                    if (
                        event["ResourceStatus"].endswith("FAILED")
                        and "ResourceStatusReason" in event
                        and not any(
                            failure["logical_id"] == event["LogicalResourceId"]
                            for failure in response["failure_reasons"]
                        )
                    ):
                        failure_reason = {
                            "logical_id": event["LogicalResourceId"],
                            "physical_id": event.get("PhysicalResourceId", "N/A"),
                            "resource_type": event["ResourceType"],
                            "status": event["ResourceStatus"],
                            "reason": event.get("ResourceStatusReason", "No reason provided"),
                            "timestamp": (
                                event["Timestamp"].isoformat()
                                if isinstance(event["Timestamp"], datetime.datetime)
                                else event["Timestamp"]
                            ),
                        }
                        response["failure_reasons"].append(failure_reason)
            except ClientError as e:
                response["events_error"] = str(e)

        except ClientError as e:
            if "does not exist" in str(e):
                # Stack doesn't exist, check for deleted stacks
                try:
                    deleted_stacks = []
                    paginator = cloudformation.get_paginator("list_stacks")
                    for page in paginator.paginate(StackStatusFilter=["DELETE_COMPLETE"]):
                        for stack_summary in page["StackSummaries"]:
                            if stack_summary["StackName"] == stack_id:
                                deleted_stacks.append(stack_summary)

                    if deleted_stacks:
                        response["deleted_stacks"] = deleted_stacks
                        response["message"] = (
                            f"Found {len(deleted_stacks)} deleted stacks with name '{stack_id}'"
                        )
                except ClientError as list_error:
                    response["list_error"] = str(list_error)
            else:
                raise

        return response

    except Exception as e:
        logger.exception("Error in fetch_cloudformation_status: %s", str(e))
        return {"status": "error", "error": str(e), "stack_exists": False}
