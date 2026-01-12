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

"""Run timeline visualization tools for the AWS HealthOmics MCP server."""

import json
from awslabs.aws_healthomics_mcp_server.tools.workflow_analysis import (
    get_run_manifest_logs_internal,
)
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import get_omics_client
from awslabs.aws_healthomics_mcp_server.visualization.gantt_generator import GanttGenerator
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import List, Union


# Valid time units for timeline visualization
VALID_TIME_UNITS = ['sec', 'min', 'hr', 'day']


def _normalize_run_ids(run_ids: Union[List[str], str]) -> List[str]:
    """Normalize run_ids parameter to a list of strings.

    Handles various input formats:
    - List of strings: ["run1", "run2"]
    - JSON string: '["run1", "run2"]'
    - Comma-separated string: "run1,run2"
    - Single string: "run1"
    """
    if isinstance(run_ids, list):
        return run_ids

    if isinstance(run_ids, str):
        # Try to parse as JSON first
        try:
            parsed = json.loads(run_ids)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
            else:
                # Single item in JSON
                return [str(parsed)]
        except json.JSONDecodeError:
            # Not JSON, try comma-separated
            if ',' in run_ids:
                return [item.strip() for item in run_ids.split(',') if item.strip()]
            else:
                # Single run ID
                return [run_ids.strip()]

    # Fallback
    return [str(run_ids)]


async def generate_run_timeline(
    ctx: Context,
    run_ids: Union[List[str], str] = Field(
        ...,
        description='List of run IDs to generate timeline for. Can be provided as a JSON array string like ["run1", "run2"] or as a comma-separated string like "run1,run2"',
    ),
    time_unit: str = Field(
        default='hr',
        description='Time unit for the timeline axis. Valid values: sec, min, hr, day. Defaults to hr.',
    ),
) -> str:
    """Generate a Gantt-style timeline visualization for AWS HealthOmics workflow runs.

    This tool creates an SVG Gantt chart showing task execution phases (pending and running)
    with status-based coloring. The chart helps visualize task parallelism and identify
    bottlenecks in workflow execution.

    Use this tool when users ask about:
    - "Show me a timeline of my workflow run"
    - "Visualize the execution of my HealthOmics workflow"
    - "Create a Gantt chart for my run"
    - "How did my tasks execute over time?"
    - "What was the parallelism in my workflow?"

    The chart displays:
    - Pending/starting phase (light grey bars)
    - Running phase (colored by status: blue=COMPLETED, red=FAILED, orange=CANCELLED)
    - Interactive tooltips with task details (name, CPUs, memory, instance type, cost)
    - Time axis with configurable units (seconds, minutes, hours, days)

    Args:
        ctx: MCP request context for error reporting
        run_ids: List of run IDs to generate timeline for
        time_unit: Time unit for the timeline axis (sec, min, hr, day)

    Returns:
        SVG string representing the Gantt chart timeline
    """
    try:
        # Normalize run_ids to handle various input formats
        normalized_run_ids = _normalize_run_ids(run_ids)
        logger.info(f'Generating timeline for runs {normalized_run_ids}')

        # Validate time_unit
        if time_unit not in VALID_TIME_UNITS:
            error_msg = (
                f"Invalid time_unit '{time_unit}'. Valid values are: {', '.join(VALID_TIME_UNITS)}"
            )
            await ctx.error(error_msg)
            return error_msg

        # Get the omics client
        omics_client = get_omics_client()

        # Collect tasks from all runs
        all_tasks = []
        run_info = {}

        for run_id in normalized_run_ids:
            try:
                logger.debug(f'Processing run {run_id} for timeline')

                # Get basic run information
                run_response = omics_client.get_run(id=run_id)
                run_uuid = run_response.get('uuid')

                if not run_uuid:
                    logger.warning(f'No UUID found for run {run_id}, skipping')
                    continue

                # Store run info (use first run's info for chart title)
                if not run_info:
                    run_info = {
                        'runId': run_id,
                        'runName': run_response.get('name', run_id),
                        'arn': run_response.get('arn', ''),
                    }

                # Get manifest logs
                manifest_logs = await get_run_manifest_logs_internal(
                    run_id=run_id,
                    run_uuid=run_uuid,
                    limit=2999,  # Get comprehensive manifest data
                )

                # Parse manifest logs to extract task data
                log_events = manifest_logs.get('events', [])
                for event in log_events:
                    message = event.get('message', '').strip()

                    try:
                        if message.startswith('{') and message.endswith('}'):
                            parsed_message = json.loads(message)

                            # Check if this is a task-level object (has cpus, memory, instanceType)
                            if (
                                'cpus' in parsed_message
                                and 'memory' in parsed_message
                                and 'instanceType' in parsed_message
                            ):
                                task_data = _extract_task_for_timeline(parsed_message)
                                if task_data:
                                    all_tasks.append(task_data)

                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        logger.warning(f'Error parsing manifest message: {str(e)}')
                        continue

            except Exception as e:
                logger.error(f'Error processing run {run_id}: {str(e)}')
                continue

        if not all_tasks:
            error_msg = f"""
Unable to retrieve task data for the specified run IDs: {run_ids}

This could be because:
- The runs are still in progress (manifest logs are only available after completion)
- The run IDs are invalid
- There was an error accessing the CloudWatch logs

Please verify the run IDs and ensure the runs have completed successfully.
"""
            await ctx.error(error_msg)
            return error_msg

        # Update run_info with task count if multiple runs
        if len(normalized_run_ids) > 1:
            run_info['runName'] = (
                f'{run_info.get("runName", "Multiple Runs")} (+{len(normalized_run_ids) - 1} more)'
            )

        # Generate the Gantt chart
        gantt_generator = GanttGenerator()
        svg_output = gantt_generator.generate_chart(
            tasks=all_tasks,
            run_info=run_info,
            time_unit=time_unit,
        )

        logger.info(f'Generated timeline with {len(all_tasks)} tasks')
        return svg_output

    except Exception as e:
        error_message = f'Error generating timeline for runs {run_ids}: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        return error_message


def _extract_task_for_timeline(task_data: dict) -> dict | None:
    """Extract task data needed for timeline visualization.

    Args:
        task_data: Task manifest data dictionary

    Returns:
        Dictionary with task data for timeline, or None if missing required fields
    """
    try:
        # Extract timing information
        creation_time = task_data.get('creationTime')
        stop_time = task_data.get('stopTime')

        # Need at least creationTime and stopTime for timeline
        if not creation_time or not stop_time:
            return None

        # Extract metrics
        metrics = task_data.get('metrics', {})

        return {
            'taskName': task_data.get('name', 'unknown'),
            'creationTime': creation_time,
            'startTime': task_data.get('startTime'),
            'stopTime': stop_time,
            'status': task_data.get('status', 'COMPLETED'),
            'allocatedCpus': task_data.get('cpus', 0),
            'allocatedMemoryGiB': task_data.get('memory', 0),
            'instanceType': task_data.get('instanceType', 'N/A'),
            'estimatedUSD': 0,  # Cost not calculated for timeline
            'reservedCpus': metrics.get('cpusReserved', 0),
            'reservedMemoryGiB': metrics.get('memoryReservedGiB', 0),
        }

    except Exception as e:
        logger.warning(f'Error extracting task for timeline: {str(e)}')
        return None
