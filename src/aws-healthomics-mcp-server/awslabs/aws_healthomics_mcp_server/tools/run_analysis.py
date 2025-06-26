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

"""Run analysis tools for the AWS HealthOmics MCP server."""

import json
import os
from awslabs.aws_healthomics_mcp_server.consts import DEFAULT_REGION
from awslabs.aws_healthomics_mcp_server.tools.workflow_analysis import (
    get_run_manifest_logs_internal,
)
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import get_aws_session
from datetime import datetime, timezone
from loguru import logger
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Any, Dict, List, Optional, Union


def _json_serializer(obj):
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f'Object of type {type(obj)} is not JSON serializable')


def _safe_json_dumps(data: Any, **kwargs) -> str:
    """Safely serialize data to JSON, handling datetime objects."""
    return json.dumps(data, default=_json_serializer, **kwargs)


def _convert_datetime_to_string(obj: Any) -> Any:
    """Recursively convert datetime objects to ISO strings in nested data structures."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: _convert_datetime_to_string(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [_convert_datetime_to_string(item) for item in obj]
    else:
        return obj


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


async def analyze_run_performance(
    ctx: Context,
    run_ids: Union[List[str], str] = Field(
        ...,
        description='List of run IDs to analyze for resource optimization. Can be provided as a JSON array string like ["run1", "run2"] or as a comma-separated string like "run1,run2"',
    ),
) -> str:
    """Analyze AWS HealthOmics workflow run performance and provide optimization recommendations.

    This tool analyzes HealthOmics workflow runs to help users optimize:
    - Resource utilization patterns (CPU, memory)
    - Cost optimization opportunities
    - Performance bottlenecks
    - Resource allocation efficiency
    - Runtime optimization suggestions

    Use this tool when users ask about:
    - "How can I optimize my HealthOmics runs?"
    - "Why is my workflow using too many resources?"
    - "How can I reduce costs for my genomic workflows?"
    - "What resources are being wasted in my runs?"
    - "How can I improve workflow performance?"

    The tool retrieves detailed manifest logs containing task-level metrics
    and provides structured data with analysis instructions for AI-powered insights.

    Args:
        ctx: MCP request context for error reporting
        run_ids: List of run IDs to analyze for optimization

    Returns:
        Formatted analysis string with structured manifest data and optimization recommendations
    """
    try:
        # Normalize run_ids to handle various input formats
        normalized_run_ids = _normalize_run_ids(run_ids)
        logger.info(f'Analyzing performance for runs {normalized_run_ids}')

        # Get the structured analysis data
        analysis_data = await _get_run_analysis_data(normalized_run_ids)

        if not analysis_data or not analysis_data.get('runs'):
            error_msg = f"""
Unable to retrieve manifest data for the specified run IDs: {run_ids}

This could be because:
- The runs are still in progress (manifest logs are only available after completion)
- The run IDs are invalid
- There was an error accessing the CloudWatch logs

Please verify the run IDs and ensure the runs have completed successfully.
"""
            await ctx.error(error_msg)
            return error_msg

        # Generate the comprehensive analysis report
        report = await _generate_analysis_report(analysis_data)

        logger.info(f'Generated analysis report for {len(analysis_data["runs"])} runs')
        return report

    except Exception as e:
        error_message = f'Error analyzing run performance for runs {run_ids}: {str(e)}'
        logger.error(error_message)
        await ctx.error(error_message)
        return error_message


async def _generate_analysis_report(analysis_data: Dict[str, Any]) -> str:
    """Generate a comprehensive analysis report from the structured data."""
    try:
        report_sections = []

        # Header
        report_sections.append('# AWS HealthOmics Workflow Performance Analysis Report')
        report_sections.append('')

        # Summary
        summary = analysis_data['summary']
        report_sections.append('## Analysis Summary')
        report_sections.append(f'- **Total Runs Analyzed**: {summary["totalRuns"]}')
        report_sections.append(f'- **Analysis Timestamp**: {summary["analysisTimestamp"]}')
        report_sections.append(f'- **Analysis Type**: {summary["analysisType"]}')
        report_sections.append('')

        # Process each run
        for i, run_data in enumerate(analysis_data['runs'], 1):
            run_info = run_data['runInfo']
            run_summary = run_data['summary']
            task_metrics = run_data['taskMetrics']

            report_sections.append(f'## Run {i}: {run_info["runName"]} ({run_info["runId"]})')
            report_sections.append('')

            # Run overview
            report_sections.append('### Run Overview')
            report_sections.append(f'- **Status**: {run_info["status"]}')
            report_sections.append(f'- **Workflow ID**: {run_info["workflowId"]}')
            report_sections.append(f'- **Creation Time**: {run_info["creationTime"]}')
            report_sections.append(f'- **Start Time**: {run_info["startTime"]}')
            report_sections.append(f'- **Stop Time**: {run_info["stopTime"]}')
            report_sections.append('')

            # Resource summary
            report_sections.append('### Resource Utilization Summary')
            report_sections.append(f'- **Total Tasks**: {run_summary["totalTasks"]}')
            report_sections.append(
                f'- **Total Allocated CPUs**: {run_summary["totalAllocatedCpus"]:.2f}'
            )
            report_sections.append(
                f'- **Total Allocated Memory**: {run_summary["totalAllocatedMemoryGiB"]:.2f} GiB'
            )
            report_sections.append(
                f'- **Actual CPU Usage**: {run_summary["totalActualCpuUsage"]:.2f}'
            )
            report_sections.append(
                f'- **Actual Memory Usage**: {run_summary["totalActualMemoryUsageGiB"]:.2f} GiB'
            )
            report_sections.append(
                f'- **Overall CPU Efficiency**: {run_summary["overallCpuEfficiency"]:.1%}'
            )
            report_sections.append(
                f'- **Overall Memory Efficiency**: {run_summary["overallMemoryEfficiency"]:.1%}'
            )
            report_sections.append('')

            # Task analysis
            if task_metrics:
                report_sections.append('### Task Performance Analysis')

                # Identify optimization opportunities
                over_provisioned_tasks = [
                    t for t in task_metrics if t.get('isOverProvisioned', False)
                ]
                under_provisioned_tasks = [
                    t for t in task_metrics if t.get('isUnderProvisioned', False)
                ]

                if over_provisioned_tasks:
                    report_sections.append('#### Over-Provisioned Tasks (Wasting Resources)')
                    for task in over_provisioned_tasks:
                        cpu_waste = task.get('wastedCpus', 0)
                        memory_waste = task.get('wastedMemoryGiB', 0)
                        cpu_eff = task.get('cpuEfficiencyRatio', 0)
                        mem_eff = task.get('memoryEfficiencyRatio', 0)

                        report_sections.append(f'- **{task["taskName"]}**:')
                        report_sections.append(
                            f'  - CPU Efficiency: {cpu_eff:.1%} (Wasted: {cpu_waste:.2f} CPUs)'
                        )
                        report_sections.append(
                            f'  - Memory Efficiency: {mem_eff:.1%} (Wasted: {memory_waste:.2f} GiB)'
                        )
                        report_sections.append(
                            f'  - Instance Type: {task.get("instanceType", "N/A")}'
                        )
                        report_sections.append(
                            f'  - Runtime: {task.get("runningSeconds", 0)} seconds'
                        )
                    report_sections.append('')

                if under_provisioned_tasks:
                    report_sections.append(
                        '#### Under-Provisioned Tasks (May Need More Resources)'
                    )
                    for task in under_provisioned_tasks:
                        max_cpu_eff = task.get('maxCpuEfficiencyRatio', 0)
                        max_mem_eff = task.get('maxMemoryEfficiencyRatio', 0)

                        report_sections.append(f'- **{task["taskName"]}**:')
                        report_sections.append(f'  - Max CPU Utilization: {max_cpu_eff:.1%}')
                        report_sections.append(f'  - Max Memory Utilization: {max_mem_eff:.1%}')
                        report_sections.append(
                            f'  - Instance Type: {task.get("instanceType", "N/A")}'
                        )
                        report_sections.append(
                            f'  - Runtime: {task.get("runningSeconds", 0)} seconds'
                        )
                    report_sections.append('')

                # Optimization recommendations
                report_sections.append('#### Optimization Recommendations')

                total_wasted_cpus = sum(t.get('wastedCpus', 0) for t in task_metrics)
                total_wasted_memory = sum(t.get('wastedMemoryGiB', 0) for t in task_metrics)

                if total_wasted_cpus > 0 or total_wasted_memory > 0:
                    report_sections.append('**Resource Right-Sizing Opportunities:**')
                    report_sections.append(
                        f'- Total wasted CPUs across all tasks: {total_wasted_cpus:.2f}'
                    )
                    report_sections.append(
                        f'- Total wasted memory across all tasks: {total_wasted_memory:.2f} GiB'
                    )
                    report_sections.append('')

                # Instance type recommendations
                instance_types = {}
                for task in task_metrics:
                    inst_type = task.get('instanceType', 'unknown')
                    if inst_type not in instance_types:
                        instance_types[inst_type] = []
                    instance_types[inst_type].append(task)

                if len(instance_types) > 1:
                    report_sections.append('**Instance Type Analysis:**')
                    for inst_type, tasks in instance_types.items():
                        avg_cpu_eff = sum(t.get('cpuEfficiencyRatio', 0) for t in tasks) / len(
                            tasks
                        )
                        avg_mem_eff = sum(t.get('memoryEfficiencyRatio', 0) for t in tasks) / len(
                            tasks
                        )
                        report_sections.append(f'- **{inst_type}** ({len(tasks)} tasks):')
                        report_sections.append(f'  - Average CPU Efficiency: {avg_cpu_eff:.1%}')
                        report_sections.append(f'  - Average Memory Efficiency: {avg_mem_eff:.1%}')
                    report_sections.append('')

            # Detailed task data (JSON format for further analysis)
            report_sections.append('### Detailed Task Metrics (JSON)')
            report_sections.append('```json')
            report_sections.append(_safe_json_dumps(task_metrics, indent=2))
            report_sections.append('```')
            report_sections.append('')

        # General recommendations
        report_sections.append('## General Optimization Guidelines')
        report_sections.append('')
        report_sections.append('### HealthOmics Resource Recommendations')
        report_sections.append('- **Minimum CPU allocation**: 1 CPU per task')
        report_sections.append('- **Minimum Memory allocation**: 1 GB per task')
        report_sections.append('- **Instance family CPU:Memory ratios**:')
        report_sections.append('  - omics.c family: 2 GiB memory per CPU')
        report_sections.append('  - omics.m family: 4 GiB memory per CPU')
        report_sections.append('  - omics.r family: 8 GiB memory per CPU')
        report_sections.append('')
        report_sections.append('### Optimization Thresholds')
        report_sections.append('- **Over-provisioned threshold**: < 50% efficiency')
        report_sections.append('- **Under-provisioned threshold**: > 90% max utilization')
        report_sections.append(
            '- **Target efficiency**: ~80% for optimal cost/performance balance'
        )
        report_sections.append('')
        report_sections.append('### Next Steps')
        report_sections.append(
            '1. **Prioritize high-impact optimizations**: Focus on tasks with the most wasted resources'
        )
        report_sections.append(
            '2. **Test resource adjustments**: Gradually reduce resources for over-provisioned tasks'
        )
        report_sections.append(
            "3. **Monitor performance**: Ensure optimizations don't negatively impact runtime"
        )
        report_sections.append(
            '4. **Consider workflow parallelization**: Look for opportunities to run tasks concurrently'
        )

        return '\n'.join(report_sections)

    except Exception as e:
        logger.error(f'Error generating analysis report: {str(e)}')
        return f'Error generating analysis report: {str(e)}'


async def _get_run_analysis_data(run_ids: List[str]) -> Dict[str, Any]:
    """Get structured analysis data for the specified runs."""
    try:
        # Get AWS session and clients
        region = os.environ.get('AWS_REGION', DEFAULT_REGION)
        session = get_aws_session(region)
        omics_client = session.client('omics')

        analysis_results = {
            'runs': [],
            'summary': {
                'totalRuns': len(run_ids),
                'analysisTimestamp': datetime.now(timezone.utc).isoformat(),
                'analysisType': 'manifest-based',
            },
        }

        # Process each run
        for run_id in run_ids:
            try:
                logger.debug(f'Processing run {run_id}')

                # Get basic run information
                run_response = omics_client.get_run(id=run_id)
                run_uuid = run_response.get('uuid')

                if not run_uuid:
                    logger.warning(f'No UUID found for run {run_id}, skipping manifest analysis')
                    continue

                # Get manifest logs
                manifest_logs = await get_run_manifest_logs_internal(
                    run_id=run_id,
                    run_uuid=run_uuid,
                    limit=2999,  # Get comprehensive manifest data
                )

                # Parse and structure the manifest data
                run_analysis = await _parse_manifest_for_analysis(
                    run_id, run_response, manifest_logs
                )

                if run_analysis:
                    analysis_results['runs'].append(run_analysis)

            except Exception as e:
                logger.error(f'Error processing run {run_id}: {str(e)}')
                # Continue with other runs rather than failing completely
                continue

        # Convert any remaining datetime objects to strings before returning
        return _convert_datetime_to_string(analysis_results)

    except Exception as e:
        logger.error(f'Error getting run analysis data: {str(e)}')
        return {}


async def _parse_manifest_for_analysis(
    run_id: str, run_response: Any, manifest_logs: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Parse manifest logs to extract key metrics for analysis."""
    try:
        # Helper function to convert datetime to ISO string
        def datetime_to_iso(dt):
            if dt is None:
                return ''
            if isinstance(dt, datetime):
                return dt.isoformat()
            return str(dt)

        # Extract basic run information
        run_info = {
            'runId': run_id,
            'runName': run_response.get('name', ''),
            'status': run_response.get('status', ''),
            'workflowId': run_response.get('workflowId', ''),
            'creationTime': datetime_to_iso(run_response.get('creationTime')),
            'startTime': datetime_to_iso(run_response.get('startTime')),
            'stopTime': datetime_to_iso(run_response.get('stopTime')),
            'runOutputUri': run_response.get('runOutputUri', ''),
        }

        # Parse manifest log events
        log_events = manifest_logs.get('events', [])
        if not log_events:
            logger.warning(f'No manifest log events found for run {run_id}')
            return None

        # Extract task metrics and run details from manifest logs
        task_metrics = []
        run_details = {}

        for event in log_events:
            message = event.get('message', '').strip()

            try:
                # Each line in the manifest should be a JSON object
                if message.startswith('{') and message.endswith('}'):
                    parsed_message = json.loads(message)

                    # Check if this is a run-level object (has workflow info but no task-specific fields)
                    if (
                        'workflow' in parsed_message
                        and 'metrics' in parsed_message
                        and 'name' in parsed_message
                        and 'cpus' not in parsed_message
                    ):  # Run objects don't have cpus field
                        # This is run-level information
                        run_details = {
                            'arn': parsed_message.get('arn', ''),
                            'digest': parsed_message.get('digest', ''),
                            'runningSeconds': parsed_message.get('metrics', {}).get(
                                'runningSeconds', 0
                            ),
                            'parameters': parsed_message.get('parameters', {}),
                            'parameterTemplate': parsed_message.get('parameterTemplate', {}),
                            'storageType': parsed_message.get('storageType', ''),
                            'roleArn': parsed_message.get('roleArn', ''),
                            'startedBy': parsed_message.get('startedBy', ''),
                            'outputUri': parsed_message.get('outputUri', ''),
                            'resourceDigests': parsed_message.get('resourceDigests', {}),
                        }

                    # Check if this is a task-level object (has cpus, memory, instanceType)
                    elif (
                        'cpus' in parsed_message
                        and 'memory' in parsed_message
                        and 'instanceType' in parsed_message
                    ):
                        # This is task-level information
                        task_metric = _extract_task_metrics_from_manifest(parsed_message)
                        if task_metric:
                            task_metrics.append(task_metric)

            except json.JSONDecodeError:
                logger.debug(f'Non-JSON message in manifest (skipping): {message[:100]}...')
                continue
            except Exception as e:
                logger.warning(f'Error parsing manifest message: {str(e)}')
                continue

        # Calculate summary statistics
        total_tasks = len(task_metrics)
        total_allocated_cpus = sum(task.get('allocatedCpus', 0) for task in task_metrics)
        total_allocated_memory = sum(task.get('allocatedMemoryGiB', 0) for task in task_metrics)
        total_actual_cpu_usage = sum(task.get('avgCpuUtilization', 0) for task in task_metrics)
        total_actual_memory_usage = sum(
            task.get('avgMemoryUtilizationGiB', 0) for task in task_metrics
        )

        # Calculate efficiency ratios
        overall_cpu_efficiency = (
            (total_actual_cpu_usage / total_allocated_cpus) if total_allocated_cpus > 0 else 0
        )
        overall_memory_efficiency = (
            (total_actual_memory_usage / total_allocated_memory)
            if total_allocated_memory > 0
            else 0
        )

        result = {
            'runInfo': run_info,
            'runDetails': run_details,
            'taskMetrics': task_metrics,
            'summary': {
                'totalTasks': total_tasks,
                'totalAllocatedCpus': total_allocated_cpus,
                'totalAllocatedMemoryGiB': total_allocated_memory,
                'totalActualCpuUsage': total_actual_cpu_usage,
                'totalActualMemoryUsageGiB': total_actual_memory_usage,
                'overallCpuEfficiency': overall_cpu_efficiency,
                'overallMemoryEfficiency': overall_memory_efficiency,
                'manifestLogCount': len(log_events),
            },
        }

        # Convert any datetime objects to strings before returning
        return _convert_datetime_to_string(result)

    except Exception as e:
        logger.error(f'Error parsing manifest for run {run_id}: {str(e)}')
        return None


def _extract_task_metrics_from_manifest(task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract key metrics from a task manifest object based on the actual structure."""
    try:
        metrics = {
            'taskName': task_data.get('name', 'unknown'),
            'taskArn': task_data.get('arn', ''),
            'taskUuid': task_data.get('uuid', ''),
        }

        # Resource allocation (what was requested/reserved)
        metrics['allocatedCpus'] = task_data.get('cpus', 0)
        metrics['allocatedMemoryGiB'] = task_data.get('memory', 0)
        metrics['instanceType'] = task_data.get('instanceType', '')
        metrics['gpus'] = task_data.get('gpus', 0)
        metrics['image'] = task_data.get('image', '')

        # Extract metrics from the metrics object
        task_metrics = task_data.get('metrics', {})

        # CPU metrics
        metrics['reservedCpus'] = task_metrics.get('cpusReserved', 0)
        metrics['avgCpuUtilization'] = task_metrics.get('cpusAverage', 0)
        metrics['maxCpuUtilization'] = task_metrics.get('cpusMaximum', 0)

        # Memory metrics
        metrics['reservedMemoryGiB'] = task_metrics.get('memoryReservedGiB', 0)
        metrics['avgMemoryUtilizationGiB'] = task_metrics.get('memoryAverageGiB', 0)
        metrics['maxMemoryUtilizationGiB'] = task_metrics.get('memoryMaximumGiB', 0)

        # GPU metrics
        metrics['reservedGpus'] = task_metrics.get('gpusReserved', 0)

        # Timing information
        metrics['runningSeconds'] = task_metrics.get('runningSeconds', 0)
        metrics['startTime'] = task_data.get('startTime', '')
        metrics['stopTime'] = task_data.get('stopTime', '')
        metrics['creationTime'] = task_data.get('creationTime', '')
        metrics['status'] = task_data.get('status', '')

        # Calculate efficiency ratios (actual usage vs reserved resources)
        if metrics['reservedCpus'] > 0:
            metrics['cpuEfficiencyRatio'] = metrics['avgCpuUtilization'] / metrics['reservedCpus']
            metrics['maxCpuEfficiencyRatio'] = (
                metrics['maxCpuUtilization'] / metrics['reservedCpus']
            )
        else:
            metrics['cpuEfficiencyRatio'] = 0
            metrics['maxCpuEfficiencyRatio'] = 0

        if metrics['reservedMemoryGiB'] > 0:
            metrics['memoryEfficiencyRatio'] = (
                metrics['avgMemoryUtilizationGiB'] / metrics['reservedMemoryGiB']
            )
            metrics['maxMemoryEfficiencyRatio'] = (
                metrics['maxMemoryUtilizationGiB'] / metrics['reservedMemoryGiB']
            )
        else:
            metrics['memoryEfficiencyRatio'] = 0
            metrics['maxMemoryEfficiencyRatio'] = 0

        # Calculate potential waste (reserved but unused resources)
        metrics['wastedCpus'] = max(0, metrics['reservedCpus'] - metrics['avgCpuUtilization'])
        metrics['wastedMemoryGiB'] = max(
            0, metrics['reservedMemoryGiB'] - metrics['avgMemoryUtilizationGiB']
        )

        # Flag potential optimization opportunities
        metrics['isOverProvisioned'] = (
            metrics['cpuEfficiencyRatio'] < 0.5 or metrics['memoryEfficiencyRatio'] < 0.5
        )
        metrics['isUnderProvisioned'] = (
            metrics['maxCpuEfficiencyRatio'] > 0.9 or metrics['maxMemoryEfficiencyRatio'] > 0.9
        )

        return metrics

    except Exception as e:
        logger.warning(f'Error extracting task metrics: {str(e)}')
        return None
