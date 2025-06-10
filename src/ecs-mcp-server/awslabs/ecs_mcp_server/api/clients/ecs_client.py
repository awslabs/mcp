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
Client for interacting with AWS ECS APIs.
"""

import datetime
import logging
from typing import Any, Dict, List, Tuple

from botocore.exceptions import ClientError

from awslabs.ecs_mcp_server.utils.aws import get_aws_client

logger = logging.getLogger(__name__)


class EcsClient:
    """Client for interacting with AWS ECS APIs."""

    async def check_cluster_exists(self, cluster_name: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if the specified ECS cluster exists.

        Parameters
        ----------
        cluster_name : str
            The name of the cluster to check

        Returns
        -------
        Tuple[bool, Dict[str, Any]]
            (cluster_exists, cluster_info)

        Raises
        ------
        ClientError
            If there is an issue with the AWS API call
        """
        try:
            ecs = await get_aws_client("ecs")
            clusters = await ecs.describe_clusters(clusters=[cluster_name])
            if not clusters["clusters"]:
                return False, {}
            return True, clusters["clusters"][0]
        except ClientError as e:
            logger.error(f"Error checking cluster existence: {e}")
            raise

    async def get_stopped_tasks(
        self, cluster_name: str, start_time: datetime.datetime
    ) -> List[Dict[str, Any]]:
        """
        Get stopped tasks within the specified time window.

        Parameters
        ----------
        cluster_name : str
            The name of the cluster
        start_time : datetime.datetime
            Start time for filtering tasks

        Returns
        -------
        List[Dict[str, Any]]
            List of stopped tasks
        """
        stopped_tasks = []
        try:
            # Get the ECS client
            ecs = await get_aws_client("ecs")

            # Get paginator for task listing
            paginator = await ecs.get_paginator("list_tasks")

            # Use the paginator to get pages of task ARNs
            async_iterator = paginator.paginate(cluster=cluster_name, desiredStatus="STOPPED")

            # Process each page of results
            async for page in async_iterator:
                task_arns = page.get("taskArns", [])

                if not task_arns:
                    continue

                # Get task details
                tasks_detail = await ecs.describe_tasks(cluster=cluster_name, tasks=task_arns)

                for task in tasks_detail.get("tasks", []):
                    # Check if the task has a stoppedAt timestamp
                    if "stoppedAt" in task:
                        stopped_at = task["stoppedAt"]

                        # Handle timezone awareness
                        if isinstance(stopped_at, datetime.datetime):
                            # Make stopped_at timezone-aware if it's naive
                            if stopped_at.tzinfo is None:
                                stopped_at = stopped_at.replace(tzinfo=datetime.timezone.utc)

                            # Make start_time timezone-aware if it's naive
                            compared_start_time = start_time
                            if start_time.tzinfo is None:
                                compared_start_time = start_time.replace(
                                    tzinfo=datetime.timezone.utc
                                )

                            # Only include tasks stopped after the start time
                            if stopped_at >= compared_start_time:
                                stopped_tasks.append(task)

        except ClientError as e:
            # Log but don't raise to maintain compatibility with original behavior
            logger.error(f"Error getting stopped tasks: {e}")
        except Exception as e:
            # Log but don't raise other exceptions either
            logger.error(f"Error in get_stopped_tasks: {e}")

        return stopped_tasks

    async def get_running_tasks_count(self, cluster_name: str) -> int:
        """
        Get the count of running tasks in the cluster.

        Parameters
        ----------
        cluster_name : str
            The name of the cluster

        Returns
        -------
        int
            Number of running tasks
        """
        running_tasks = []
        try:
            # Get the ECS client
            ecs = await get_aws_client("ecs")

            # Get paginator for task listing
            paginator = await ecs.get_paginator("list_tasks")

            # Use the paginator to get pages of task ARNs
            async_iterator = paginator.paginate(cluster=cluster_name, desiredStatus="RUNNING")

            # Process each page of results
            async for page in async_iterator:
                task_arns = page.get("taskArns", [])

                if not task_arns:
                    continue

                # Get task details
                tasks_detail = await ecs.describe_tasks(cluster=cluster_name, tasks=task_arns)
                running_tasks.extend(tasks_detail.get("tasks", []))

        except ClientError as e:
            # Log but don't raise to maintain compatibility with original behavior
            logger.error(f"Error getting running tasks: {e}")
        except Exception as e:
            # Log but don't raise other exceptions either
            logger.error(f"Error in get_running_tasks_count: {e}")

        return len(running_tasks)
