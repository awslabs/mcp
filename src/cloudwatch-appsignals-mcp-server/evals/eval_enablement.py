"""Enablement Tool Evaluation Script.

Evaluates whether AI assistant can:
1. Call the get_enablement_guide MCP tool
2. Understand the returned instructions
3. Modify project files correctly
4. Pass validation criteria

Usage:
    python evals/eval_enablement.py
    python evals/eval_enablement.py -v
    python evals/eval_enablement.py --task ec2_python_flask
    python evals/eval_enablement.py --no-cleanup
"""

import argparse
import asyncio
import boto3
import json
import subprocess
import sys
import traceback
from framework import (
    MetricsTracker,
    connect_to_mcp_server,
    run_agent_loop,
    run_build_validation,
    validate_with_llm,
)
from framework.constants import DEFAULT_AWS_REGION, ENABLEMENT_TASK_PROMPT
from loguru import logger
from mcp import ClientSession
from pathlib import Path
from typing import Any, Dict


logger.remove()


def cleanup_enablement_changes(project_root: Path, task: Dict[str, Any]):
    """Clean up git changes made by enablement agent.

    Enablement-specific cleanup that resets IaC and app directories.
    """
    paths_to_clean = []
    if task.get('iac_directory'):
        paths_to_clean.append(task['iac_directory'])
    if task.get('app_directory'):
        paths_to_clean.append(task['app_directory'])

    if not paths_to_clean:
        logger.warning('No directories specified to clean')
        return

    try:
        for path in paths_to_clean:
            logger.debug(f'Cleaning path: {path}')
            subprocess.run(
                ['git', 'checkout', 'HEAD', '--', path],
                cwd=project_root,
                capture_output=True,
                timeout=10,
            )
            subprocess.run(
                ['git', 'clean', '-fd', path],
                cwd=project_root,
                capture_output=True,
                timeout=10,
            )
        logger.debug(f'Reset git state for: {", ".join(paths_to_clean)}')
    except Exception as e:
        logger.warning(f'Failed to reset git state: {e}')


def get_mock_project_path() -> Path:
    """Get the absolute path to the get-enablement-guide-samples directory.

    This is computed relative to the eval script location, making it portable across machines.
    """
    script_dir = Path(__file__).parent
    return (
        script_dir
        / '..'
        / '..'
        / '..'
        / 'samples'
        / 'cloudwatch-appsignals-mcp-server'
        / 'get-enablement-guide-samples'
    )


async def run_enablement_task(
    bedrock_client,
    session: ClientSession,
    task: Dict[str, Any],
    mcp_tools,
    args,
) -> None:
    """Run a single enablement evaluation task.

    Args:
        bedrock_client: Boto3 Bedrock Runtime client
        session: MCP client session
        task: Task configuration dictionary
        mcp_tools: List of MCP tools from server
        args: Command line arguments
    """
    logger.info(f'Running: {task["id"]}...')

    # Get project root
    project_root = get_mock_project_path()

    # Construct enablement-specific prompt from task metadata
    iac_abs_path = project_root / task['iac_directory']
    app_abs_path = project_root / task['app_directory']

    prompt = ENABLEMENT_TASK_PROMPT.format(
        language=task['language'],
        framework=task['framework'],
        platform=task['platform'],
        iac_path=iac_abs_path,
        app_path=app_abs_path,
    )

    # Initialize metrics tracker
    metrics_tracker = MetricsTracker()

    try:
        # Run agent loop using generic framework
        await run_agent_loop(
            bedrock_client=bedrock_client,
            session=session,
            prompt=prompt,
            project_root=project_root,
            mcp_tools=mcp_tools,
            metrics_tracker=metrics_tracker,
        )

        # Get git diff for validation
        git_diff_result = subprocess.run(
            ['git', 'diff'], cwd=project_root, capture_output=True, text=True, timeout=10
        )
        git_diff = git_diff_result.stdout

        # Run build validation if configured
        build_result = None
        if task.get('build_config'):
            build_config = task['build_config']
            build_working_dir = project_root / build_config['working_dir']
            build_result = await run_build_validation(
                command=build_config['command'],
                working_dir=build_working_dir,
                install_command=build_config.get('install_command'),
            )

        # Run LLM-as-judge validation using generic framework
        validation = await validate_with_llm(
            bedrock_client=bedrock_client,
            validation_rubric=task['validation_rubric'],
            git_diff=git_diff,
            build_result=build_result,
        )

        # Calculate metrics
        expected_tools = task.get('expected_tools', ['get_enablement_guide'])
        metrics = metrics_tracker.get_metrics(expected_tools=expected_tools)

        # Report results
        logger.info('\n' + '=' * 60)
        logger.info(f'EVALUATION COMPLETE: {task["id"]}')
        logger.info('=' * 60)
        logger.info(f'Duration: {metrics["task_duration"]:.2f}s')
        logger.info(f'Hit Rate: {metrics.get("hit_rate", 0):.1%}')
        logger.info(f'Success Rate: {metrics["success_rate"]:.1%}')
        logger.info(f'File Operations: {metrics["file_operation_count"]}')

        if validation.get('error'):
            logger.info('Validation: ❌ ERROR')
            logger.error(validation['error'])
        else:
            passed = sum(1 for r in validation['criteria_results'] if r['status'] == 'PASS')
            total = len(validation['criteria_results'])
            status = '✅ PASS' if validation['overall_pass'] else '❌ FAIL'
            logger.info(f'Validation: {status} ({passed}/{total} criteria met)')

        logger.info('=' * 60 + '\n')

    except Exception as e:
        logger.error(f'Evaluation failed: {e}')
        if args.verbose:
            traceback.print_exc()
    finally:
        # Clean up enablement changes (IaC and app directories)
        if task.get('modifies_code', False):
            if not args.no_cleanup:
                cleanup_enablement_changes(project_root, task)
            else:
                logger.info('Skipping git cleanup (--no-cleanup flag set)')


async def main():
    """Entry point for eval script."""
    parser = argparse.ArgumentParser(description='Evaluate Application Signals enablement tool')
    parser.add_argument(
        '--verbose', '-v', action='store_true', help='Enable verbose/debug logging'
    )
    parser.add_argument('--task', help='Run specific task by ID (default: run all)')
    parser.add_argument(
        '--no-cleanup',
        action='store_true',
        help='Skip git cleanup after evaluation (useful for inspecting changes)',
    )

    args = parser.parse_args()

    if args.verbose:
        logger.add(sys.stderr, level='DEBUG', format='<level>{message}</level>')
    else:
        logger.add(sys.stderr, level='INFO', format='<level>{message}</level>')

    logger.info('Starting Application Signals enablement evaluation\n')

    # Initialize Bedrock client
    try:
        bedrock_client = boto3.client(
            service_name='bedrock-runtime', region_name=DEFAULT_AWS_REGION
        )
        logger.debug('Bedrock client initialized')
    except Exception as e:
        logger.error(f'Failed to initialize Bedrock client: {e}')
        logger.error('Make sure AWS credentials are configured')
        sys.exit(1)

    # Load tasks
    tasks_file = Path(__file__).parent / 'tasks' / 'enablement_tasks.json'
    with open(tasks_file) as f:
        all_tasks = json.load(f)

    if args.task:
        all_tasks = [t for t in all_tasks if t['id'] == args.task]
        if not all_tasks:
            logger.error(f"Task '{args.task}' not found")
            sys.exit(1)

    logger.info(f'Loaded {len(all_tasks)} task(s)')
    for task in all_tasks:
        logger.info(f'  - {task["id"]}: {task["platform"]} + {task["language"]}')
    logger.info('')

    logger.debug('Connecting to MCP server...')

    # Connect to MCP server using framework
    try:
        async with connect_to_mcp_server(verbose=args.verbose) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                tools_response = await session.list_tools()
                logger.debug(f'Connected to MCP server with {len(tools_response.tools)} tools')

                # Run each task
                for task in all_tasks:
                    await run_enablement_task(
                        bedrock_client, session, task, tools_response.tools, args
                    )
    finally:
        # Give subprocess time to clean up properly
        await asyncio.sleep(0.1)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info('\nInterrupted by user')
        sys.exit(0)
