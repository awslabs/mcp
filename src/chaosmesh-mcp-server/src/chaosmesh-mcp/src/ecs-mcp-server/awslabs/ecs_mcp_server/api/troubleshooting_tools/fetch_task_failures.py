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
Task-level diagnostics for ECS task failures.

This module provides a function to analyze failed ECS tasks to identify patterns and
common failure reasons to help diagnose container-level issues.
"""

import datetime
import logging
from typing import Any, Dict, List, Optional, Tuple

from botocore.exceptions import ClientError

from awslabs.ecs_mcp_server.utils.aws import get_aws_client
from awslabs.ecs_mcp_server.utils.time_utils import calculate_time_window

logger = logging.getLogger(__name__)


def _categorize_container_failure(container: Dict[str, Any]) -> str:
    """
    Categorize container failure based on exit code and reason.

    Parameters
    ----------
    container : Dict[str, Any]
        Container information

    Returns
    -------
    str
        Failure category
    """
    reason = container.get("reason", "")
    exit_code = container.get("exitCode")

    # Image pull failures
    if "CannotPullContainerError" in reason or "ImagePull" in reason:
        return "image_pull_failure"

    # Resource constraints
    if "resource" in reason.lower() and (
        "constraint" in reason.lower() or "exceed" in reason.lower()
    ):
        return "resource_constraint"

    # Exit code 137 (OOM killed)
    if exit_code == 137:
        return "out_of_memory"

    # Exit code 139 (segmentation fault)
    if exit_code == 139:
        return "segmentation_fault"

    # Exit code 1 or other non-zero (application error)
    if exit_code is not None and exit_code != 0 and exit_code != "N/A":
        return "application_error"

    # Task stopped by user or deployment
    if "Essential container" in reason:
        return "dependent_container_stopped"

    # Catch-all for uncategorized failures
    return "other"


def _process_task_failure(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single task failure and extract relevant information.

    Parameters
    ----------
    task : Dict[str, Any]
        Task information from ECS

    Returns
    -------
    Dict[str, Any]
        Processed task failure information
    """
    task_failure = {
        "task_id": task["taskArn"].split("/")[-1],
        "task_definition": task["taskDefinitionArn"].split("/")[-1],
        "stopped_at": (
            task["stoppedAt"].isoformat()
            if isinstance(task["stoppedAt"], datetime.datetime)
            else task["stoppedAt"]
        ),
        "started_at": task.get("startedAt", "N/A"),
        "containers": [],
    }

    # Process container information
    for container in task.get("containers", []):
        container_info = {
            "name": container["name"],
            "exit_code": container.get("exitCode", "N/A"),
            "reason": container.get("reason", "No reason provided"),
        }
        task_failure["containers"].append(container_info)

    return task_failure


def _categorize_failures(
    tasks: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    """
    Process stopped tasks and categorize failures.

    Parameters
    ----------
    tasks : List[Dict[str, Any]]
        List of stopped tasks

    Returns
    -------
    Tuple[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]
        (failed_tasks, failure_categories)
    """
    failed_tasks = []
    failure_categories = {}

    for task in tasks:
        task_failure = _process_task_failure(task)
        failed_tasks.append(task_failure)

        # Categorize each container failure
        for container in task.get("containers", []):
            category = _categorize_container_failure(container)

            if category not in failure_categories:
                failure_categories[category] = []
            failure_categories[category].append(task_failure)

    return failed_tasks, failure_categories


async def fetch_task_failures(
    app_name: str,
    cluster_name: str,
    time_window: int = 3600,
    start_time: Optional[datetime.datetime] = None,
    end_time: Optional[datetime.datetime] = None,
    ecs_client=None,
) -> Dict[str, Any]:
    """
    Task-level diagnostics for ECS task failures.

    Parameters
    ----------
    app_name : str
        The name of the application to analyze
    cluster_name : str
        The name of the ECS cluster
    time_window : int, optional
        Time window in seconds to look back for failures (default: 3600)
    start_time : datetime, optional
        Explicit start time for the analysis window
        (UTC, takes precedence over time_window if provided)
    end_time : datetime, optional
        Explicit end time for the analysis window (UTC, defaults to current time if not provided)
    ecs_client : object, optional
        Client for ECS API interactions, useful for testing

    Returns
    -------
    Dict[str, Any]
        Failed tasks with timestamps, exit codes, status, and resource utilization
    """
    # Initialize response
    response = {
        "status": "success",
        "cluster_exists": False,
        "failed_tasks": [],
        "failure_categories": {},
        "raw_data": {},
    }

    try:
        # Calculate time window
        actual_start_time, actual_end_time = calculate_time_window(
            time_window, start_time, end_time
        )

        ecs = ecs_client or await get_aws_client("ecs")

        # Check if cluster exists
        cluster_exists, cluster_info = await ecs.check_cluster_exists(cluster_name)
        if not cluster_exists:
            response["message"] = f"Cluster '{cluster_name}' does not exist"
            return response

        response["cluster_exists"] = True
        response["raw_data"]["cluster"] = cluster_info

        # Get stopped tasks within time window
        stopped_tasks = await ecs.get_stopped_tasks(cluster_name, actual_start_time)

        # Get running tasks count
        running_tasks_count = await ecs.get_running_tasks_count(cluster_name)
        response["raw_data"]["running_tasks_count"] = running_tasks_count

        # Process and categorize failures
        failed_tasks, failure_categories = _categorize_failures(stopped_tasks)
        response["failed_tasks"] = failed_tasks
        response["failure_categories"] = failure_categories

        return response

    except ClientError as e:
        logger.error(f"AWS client error: {str(e)}")
        response["ecs_error"] = str(e)
        return response

    except Exception as e:
        logger.exception("Error in fetch_task_failures: %s", str(e))
        return {"status": "error", "error": str(e)}
