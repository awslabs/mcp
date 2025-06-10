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
Client for interacting with AWS CloudFormation APIs.
"""

import logging
from typing import Any, Dict, List

from botocore.exceptions import ClientError

from awslabs.ecs_mcp_server.utils.aws import get_aws_client

logger = logging.getLogger(__name__)


class CloudFormationClient:
    """Client for interacting with AWS CloudFormation APIs."""

    async def describe_stacks(self, stack_id: str) -> Dict[str, Any]:
        """
        Describe a CloudFormation stack.

        Parameters
        ----------
        stack_id : str
            The name or ARN of the stack to describe

        Returns
        -------
        Dict[str, Any]
            Stack details

        Raises
        ------
        ClientError
            If there is an issue with the AWS API call
        """
        try:
            # Get client using the context manager approach
            cloudformation = await get_aws_client("cloudformation")
            response = await cloudformation.describe_stacks(StackName=stack_id)
            return response
        except ClientError as e:
            logger.error(f"Error describing stack: {e}")
            raise

    async def list_stack_resources(self, stack_id: str) -> Dict[str, Any]:
        """
        List resources in a CloudFormation stack.

        Parameters
        ----------
        stack_id : str
            The name or ARN of the stack

        Returns
        -------
        Dict[str, Any]
            Stack resources
        """
        try:
            # Get client using the context manager approach
            cloudformation = await get_aws_client("cloudformation")
            response = await cloudformation.list_stack_resources(StackName=stack_id)
            return response
        except ClientError as e:
            logger.error(f"Error listing stack resources: {e}")
            return {"StackResourceSummaries": []}

    async def describe_stack_events(self, stack_id: str) -> Dict[str, Any]:
        """
        Describe events for a CloudFormation stack.

        Parameters
        ----------
        stack_id : str
            The name or ARN of the stack

        Returns
        -------
        Dict[str, Any]
            Stack events
        """
        try:
            # Get client using the context manager approach
            cloudformation = await get_aws_client("cloudformation")
            response = await cloudformation.describe_stack_events(StackName=stack_id)
            return response
        except ClientError as e:
            logger.error(f"Error describing stack events: {e}")
            return {"StackEvents": []}

    async def list_deleted_stacks(self, stack_name: str) -> List[Dict[str, Any]]:
        """
        List deleted stacks with the given name.

        Parameters
        ----------
        stack_name : str
            Name of the stack to search for

        Returns
        -------
        List[Dict[str, Any]]
            List of deleted stack summaries
        """
        deleted_stacks = []
        try:
            # Get client using the context manager approach
            cloudformation = await get_aws_client("cloudformation")
            paginator = await cloudformation.get_paginator("list_stacks")

            # Use the paginator to get pages of stack summaries
            async for page in paginator.paginate(StackStatusFilter=["DELETE_COMPLETE"]):
                for stack_summary in page.get("StackSummaries", []):
                    if stack_summary.get("StackName") == stack_name:
                        deleted_stacks.append(stack_summary)

        except ClientError as e:
            logger.error(f"Error listing deleted stacks: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in list_deleted_stacks: {e}")

        return deleted_stacks
