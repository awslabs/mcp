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

import base64
import json
from awslabs.aws_healthomics_mcp_server.analysis.cost_analyzer import CostAnalyzer
from awslabs.aws_healthomics_mcp_server.tools.workflow_analysis import (
    get_run_manifest_logs_internal,
)
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import get_account_id, get_omics_client
from awslabs.aws_healthomics_mcp_server.utils.error_utils import handle_tool_error
from awslabs.aws_healthomics_mcp_server.utils.path_utils import write_svg_to_local
from awslabs.aws_healthomics_mcp_server.utils.s3_utils import write_svg_to_s3
from awslabs.aws_healthomics_mcp_server.visualization.gantt_generator import GanttGenerator
from botocore.exceptions import ClientError, NoCredentialsError
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Optional


# Valid time units for timeline visualization
VALID_TIME_UNITS = ['sec', 'min', 'hr', 'day']

# Valid output formats
VALID_OUTPUT_FORMATS = ['svg', 'base64']

# Default region for cost analysis
DEFAULT_REGION = 'us-east-1'

# Sentinel value for default bucket owner
_SENTINEL_DEFAULT_OWNER = '__DEFAULT__'


async def generate_run_timeline(
    ctx: Context,
    run_id: str = Field(
        ...,
        description='The run ID to generate timeline for.',
    ),
    time_unit: str = Field(
        default='hr',
        description='Time unit for the timeline axis. Valid values: sec, min, hr, day. Defaults to hr.',
    ),
    region: Optional[str] = Field(
        default=None,
        description='AWS region for pricing lookups. Defaults to us-east-1.',
    ),
    output_format: str = Field(
        default='svg',
        description=(
            'Output format for the timeline. Valid values: svg (raw SVG string, default), '
            'base64 (base64-encoded SVG, useful when transport safety is needed to avoid '
            'XML/SVG markup mangling in JSON or other text protocols; note the output must '
            'be base64-decoded before it can be rendered as SVG). Use svg when writing to a '
            'local or s3 path. Defaults to svg.'
        ),
    ),
    output_path: Optional[str] = Field(
        default=None,
        description=(
            'Optional file path or S3 URI (s3://bucket/key) where the SVG output '
            'will be written. When provided, the response contains only summary '
            'metadata instead of the full SVG content. Recommended for complex '
            'workflows to avoid context window overflow.'
        ),
    ),
    expected_bucket_owner: Optional[str] = Field(
        default=_SENTINEL_DEFAULT_OWNER,
        description=(
            'AWS account ID that must own the target S3 bucket. Defaults to the '
            'current caller identity account ID. Set to None to skip bucket owner '
            'verification. Only used when output_path is an S3 URI.'
        ),
    ),
) -> str:
    """Generate a Gantt-style timeline visualization for an AWS HealthOmics workflow run.

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
        run_id: The run ID to generate timeline for
        time_unit: Time unit for the timeline axis (sec, min, hr, day)
        region: AWS region for pricing lookups
        output_format: Output format (svg or base64)
        output_path: Optional file path or S3 URI to write SVG to
        expected_bucket_owner: AWS account ID for S3 bucket owner verification

    Returns:
        SVG string, base64-encoded SVG, or JSON summary when output_path is provided
    """
    try:
        logger.info(f'Generating timeline for run {run_id}')

        # Validate time_unit
        if time_unit not in VALID_TIME_UNITS:
            error_msg = (
                f"Invalid time_unit '{time_unit}'. Valid values are: {', '.join(VALID_TIME_UNITS)}"
            )
            await ctx.error(error_msg)
            return error_msg

        # Validate output_format
        if output_format not in VALID_OUTPUT_FORMATS:
            error_msg = (
                f"Invalid output_format '{output_format}'. "
                f'Valid values are: {", ".join(VALID_OUTPUT_FORMATS)}'
            )
            await ctx.error(error_msg)
            return error_msg

        # Get the omics client
        omics_client = get_omics_client()

        # Initialize cost analyzer for pricing lookups
        effective_region = region if region else DEFAULT_REGION
        cost_analyzer = CostAnalyzer(region=effective_region)
        logger.debug(f'Initialized CostAnalyzer for region {effective_region}')

        # Get run information
        try:
            logger.debug(f'Processing run {run_id} for timeline')

            run_response = omics_client.get_run(id=run_id)
            run_uuid = run_response.get('uuid')

            if not run_uuid:
                error_msg = f'No UUID found for run {run_id}. The run may not exist or may still be initializing.'
                await ctx.error(error_msg)
                return error_msg

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
            all_tasks = []
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
                            task_data = _extract_task_for_timeline(parsed_message, cost_analyzer)
                            if task_data:
                                all_tasks.append(task_data)

                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    logger.warning(f'Error parsing manifest message: {str(e)}')
                    continue

        except Exception as e:
            error_message = f'Error processing run {run_id}: {str(e)}'
            logger.error(error_message)
            await ctx.error(error_message)
            return error_message

        if not all_tasks:
            error_msg = f"""
Unable to retrieve task data for run {run_id}

This could be because:
- The run is still in progress (manifest logs are only available after completion)
- The run ID is invalid
- The run created no tasks
- All tasks were cache hits and no tasks ran
- There was an error accessing the CloudWatch logs

Please verify the run ID and ensure the run has completed successfully.
"""
            await ctx.error(error_msg)
            return error_msg

        # Generate the Gantt chart
        gantt_generator = GanttGenerator()
        svg_output = gantt_generator.generate_chart(
            tasks=all_tasks,
            run_info=run_info,
            time_unit=time_unit,
        )

        logger.info(f'Generated timeline with {len(all_tasks)} tasks')

        # If output_path is provided, write SVG to the specified destination
        if output_path is not None:
            try:
                if output_path.startswith('s3://'):
                    # Resolve expected_bucket_owner sentinel
                    resolved_owner = expected_bucket_owner
                    if resolved_owner == _SENTINEL_DEFAULT_OWNER:
                        resolved_owner = get_account_id()
                    # None means skip bucket owner check; string means use as-is
                    result_path = write_svg_to_s3(svg_output, output_path, resolved_owner)
                else:
                    result_path = write_svg_to_local(svg_output, output_path)

                return json.dumps(
                    {
                        'status': 'success',
                        'output_path': result_path,
                        'run_id': run_id,
                        'task_count': len(all_tasks),
                    }
                )
            except (
                ValueError,
                FileExistsError,
                OSError,
                ClientError,
                NoCredentialsError,
                PermissionError,
            ) as e:
                return json.dumps(await handle_tool_error(ctx, e, 'Error writing timeline output'))

        # Return in requested format (existing behavior when output_path is None)
        if output_format == 'base64':
            return base64.b64encode(svg_output.encode('utf-8')).decode('ascii')
        else:
            return svg_output

    except Exception as e:
        error_message = f'Error generating timeline for run {run_id}: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        return error_message


def _extract_task_for_timeline(
    task_data: dict, cost_analyzer: Optional[CostAnalyzer] = None
) -> dict | None:
    """Extract task data needed for timeline visualization.

    Args:
        task_data: Task manifest data dictionary
        cost_analyzer: Optional CostAnalyzer for cost calculations

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
        instance_type = task_data.get('instanceType', 'N/A')
        running_seconds = metrics.get('runningSeconds', 0)

        # Calculate cost using CostAnalyzer
        estimated_cost = 0.0
        if cost_analyzer and instance_type and instance_type != 'N/A':
            cost = cost_analyzer.calculate_task_cost(instance_type, running_seconds)
            if cost is not None:
                estimated_cost = cost
                logger.debug(
                    f'Calculated cost for {task_data.get("name", "unknown")}: '
                    f'${estimated_cost:.4f} ({instance_type}, {running_seconds}s)'
                )

        return {
            'taskName': task_data.get('name', 'unknown'),
            'creationTime': creation_time,
            'startTime': task_data.get('startTime'),
            'stopTime': stop_time,
            'status': task_data.get('status', 'COMPLETED'),
            'allocatedCpus': task_data.get('cpus', 0),
            'allocatedMemoryGiB': task_data.get('memory', 0),
            'instanceType': instance_type,
            'estimatedUSD': estimated_cost,
            'reservedCpus': metrics.get('cpusReserved', 0),
            'reservedMemoryGiB': metrics.get('memoryReservedGiB', 0),
        }

    except Exception as e:
        logger.warning(f'Error extracting task for timeline: {str(e)}')
        return None
