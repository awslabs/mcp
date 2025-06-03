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
Application-level diagnostics through CloudWatch logs.

This module provides a function to retrieve and analyze CloudWatch logs for ECS tasks
to identify application-level issues.
"""

import datetime
import logging
from typing import Any, Dict, Optional

from botocore.exceptions import ClientError

from awslabs.ecs_mcp_server.utils.aws import get_aws_client
from awslabs.ecs_mcp_server.utils.time_utils import calculate_time_window

logger = logging.getLogger(__name__)


async def fetch_task_logs(
    app_name: str,
    cluster_name: str,
    task_id: Optional[str] = None,
    time_window: int = 3600,
    filter_pattern: Optional[str] = None,
    start_time: Optional[datetime.datetime] = None,
    end_time: Optional[datetime.datetime] = None,
) -> Dict[str, Any]:
    """
    Application-level diagnostics through CloudWatch logs.

    Parameters
    ----------
    app_name : str
        The name of the application to analyze
    cluster_name : str
        The name of the ECS cluster
    task_id : str, optional
        Specific task ID to retrieve logs for
    time_window : int, optional
        Time window in seconds to look back for logs (default: 3600)
    filter_pattern : str, optional
        CloudWatch logs filter pattern
    start_time : datetime, optional
        Explicit start time for the analysis window
        (UTC, takes precedence over time_window if provided)
    end_time : datetime, optional
        Explicit end time for the analysis window (UTC, defaults to current time if not provided)

    Returns
    -------
    Dict[str, Any]
        Log entries with severity markers, highlighted errors, context
    """
    try:
        # Calculate time window
        actual_start_time, actual_end_time = calculate_time_window(
            time_window, start_time, end_time
        )

        response = {
            "status": "success",
            "log_groups": [],
            "log_entries": [],
            "error_count": 0,
            "warning_count": 0,
            "info_count": 0,
            "pattern_summary": [],
        }

        # Initialize CloudWatch Logs client using get_aws_client
        logs = await get_aws_client("logs")

        # Determine log group name pattern
        # Usually follows the format /ecs/{cluster_name}/{task_or_service_name}
        log_group_pattern = f"/ecs/{cluster_name}/{app_name}"

        # List matching log groups
        log_groups = logs.describe_log_groups(logGroupNamePrefix=log_group_pattern)

        if not log_groups["logGroups"]:
            response["status"] = "not_found"
            response["message"] = f"No log groups found matching pattern '{log_group_pattern}'"
            return response

        # For each log group, get the log streams
        for log_group in log_groups["logGroups"]:
            log_group_name = log_group["logGroupName"]
            log_group_info = {"name": log_group_name, "log_streams": [], "entries": []}

            # Get log streams
            try:
                if task_id:
                    # If task_id is provided, look for matching log stream
                    stream_prefix = task_id.split("-")[
                        0
                    ]  # Usually task ID starts with log stream name
                    log_streams = logs.describe_log_streams(
                        logGroupName=log_group_name,
                        logStreamNamePrefix=stream_prefix,
                        orderBy="LastEventTime",
                        descending=True,
                    )
                else:
                    # Otherwise get all recent log streams
                    log_streams = logs.describe_log_streams(
                        logGroupName=log_group_name, orderBy="LastEventTime", descending=True
                    )

                for log_stream in log_streams["logStreams"]:
                    log_stream_name = log_stream["logStreamName"]

                    # Skip if it's a specific task request and this stream doesn't match
                    if task_id and task_id not in log_stream_name:
                        continue

                    # Get log events
                    try:
                        args = {
                            "logGroupName": log_group_name,
                            "logStreamName": log_stream_name,
                            "startTime": int(
                                actual_start_time.timestamp() * 1000
                            ),  # Convert to milliseconds
                            "endTime": int(actual_end_time.timestamp() * 1000),
                            "limit": 1000,  # Adjust as needed
                        }

                        if filter_pattern:
                            args["filterPattern"] = filter_pattern

                        log_events = logs.get_log_events(**args)

                        # Process log events
                        for event in log_events["events"]:
                            timestamp = datetime.datetime.fromtimestamp(event["timestamp"] / 1000.0)
                            message = event["message"]

                            # Determine log severity
                            severity = "INFO"
                            if (
                                "ERROR" in message.upper()
                                or "EXCEPTION" in message.upper()
                                or "FAIL" in message.upper()
                            ):
                                severity = "ERROR"
                                response["error_count"] += 1
                            elif "WARN" in message.upper():
                                severity = "WARN"
                                response["warning_count"] += 1
                            else:
                                response["info_count"] += 1

                            log_entry = {
                                "timestamp": timestamp.isoformat(),
                                "message": message,
                                "severity": severity,
                                "stream": log_stream_name,
                                "group": log_group_name,
                            }

                            response["log_entries"].append(log_entry)
                            log_group_info["entries"].append(log_entry)

                    except ClientError as e:
                        log_group_info["error"] = f"Error getting log events: {str(e)}"

                    log_group_info["log_streams"].append(log_stream_name)

            except ClientError as e:
                log_group_info["error"] = f"Error getting log streams: {str(e)}"

            response["log_groups"].append(log_group_info)

        # Sort log entries by timestamp
        response["log_entries"].sort(key=lambda x: x["timestamp"])

        # Generate pattern summary if there are errors
        if response["error_count"] > 0:
            error_patterns = {}
            for entry in response["log_entries"]:
                if entry["severity"] == "ERROR":
                    # Extract first line or first 100 chars as pattern
                    pattern = entry["message"].split("\n")[0][:100]
                    if pattern in error_patterns:
                        error_patterns[pattern] += 1
                    else:
                        error_patterns[pattern] = 1

            # Convert to list and sort by count
            pattern_list = [{"pattern": k, "count": v} for k, v in error_patterns.items()]
            pattern_list.sort(key=lambda x: x["count"], reverse=True)
            response["pattern_summary"] = pattern_list[:10]  # Top 10 patterns

        # Add summary message
        if response["log_entries"]:
            response["message"] = (
                f"Found {len(response['log_entries'])} log entries "
                f"({response['error_count']} errors, {response['warning_count']} warnings)"
            )
        else:
            response["message"] = "No log entries found for the specified criteria"

        return response

    except ClientError as e:
        logger.error(f"Error in fetch_task_logs: {e}")
        return {"status": "error", "error": f"AWS API error: {str(e)}"}
    except Exception as e:
        logger.error(f"Error in fetch_task_logs: {e}")
        return {"status": "error", "error": str(e)}
