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

"""Entry point for running evals as a module.

Auto-discovers and runs all tasks defined in *_tasks.py files in the specified directory.

Usage:
    python -m evals applicationsignals                                    # Run all tasks
    python -m evals applicationsignals --list                             # List all available tasks
    python -m evals applicationsignals --task investigation_tasks         # Run all investigation tasks
    python -m evals applicationsignals --task-id petclinic_scheduling_rca # Run specific task
    python -m evals applicationsignals --task investigation_tasks --task-id basic_service_health  # Combine filters
    python -m evals applicationsignals -v                                 # Verbose output
    python -m evals applicationsignals --no-cleanup                       # Skip cleanup after eval
"""

import argparse
import asyncio
import importlib
import sys
import traceback
from evals.core import EvalRunner, TaskResult
from evals.core.task import Task
from loguru import logger
from pathlib import Path
from typing import Dict, List


# TODO: Review print() vs logger usage pattern for consistency.
# Currently: print() for clean user output, logger for errors/debug with timestamps.
# TODO: Fix logging gap between module import and main() execution.
# Current logger.remove() disables logging during this period. Need better handler management.
logger.remove()


def _discover_tasks(task_dir: Path) -> tuple[List[Task], Dict[str, List[Task]]]:
    """Auto-discover all tasks from *_tasks.py files in the specified directory.

    Args:
        task_dir: Path to directory containing task modules

    Returns:
        Tuple of (all_tasks, tasks_by_module)
    """
    all_tasks = []
    tasks_by_module = {}

    # Add task directories to sys.path to enable bare module imports with importlib.import_module().
    # Alternative: require task directories to be proper packages (with __init__.py) and use fully qualified imports.
    evals_dir = task_dir.parent
    evals_dir_str = str(evals_dir.absolute())
    if evals_dir_str not in sys.path:
        sys.path.insert(0, evals_dir_str)

    task_dir_str = str(task_dir.absolute())
    if task_dir_str not in sys.path:
        sys.path.insert(0, task_dir_str)

    task_files = list(task_dir.rglob('*_tasks.py'))
    logger.debug(f'Discovered task files in {task_dir}: {task_files}')

    for task_file in task_files:
        # Convert file path to module name relative to task_dir
        rel_path = task_file.relative_to(task_dir)
        module_name = str(rel_path.with_suffix('')).replace('/', '.')

        try:
            module = importlib.import_module(module_name)

            if hasattr(module, 'TASKS'):
                tasks = module.TASKS
                # Validate that all items in TASKS are Task instances
                valid_tasks = []
                for task in tasks:
                    if isinstance(task, Task):
                        valid_tasks.append(task)
                    else:
                        logger.warning(
                            f'Skipping non-Task object in {module_name}.TASKS: {task} '
                            f'(type: {type(task).__name__})'
                        )

                if valid_tasks:
                    all_tasks.extend(valid_tasks)
                    tasks_by_module[module_name] = valid_tasks
                    logger.debug(f'Loaded {len(valid_tasks)} tasks from {module_name}')

        except Exception as e:
            logger.warning(f'Failed to load tasks from {module_name}: {e}')

    return all_tasks, tasks_by_module


def _report_task_results(task: Task, result: TaskResult, verbose: bool = False) -> None:
    """Report results for a single task.

    Args:
        task: Task instance
        result: TaskResult from EvalRunner
        verbose: If True, include captured data in output
    """
    # TODO: Export detailed results to file and print only brief summary (pass/fail).
    # Need more usage/feedback to determine what belongs in summary vs detailed report.
    print(result)

    if verbose:
        print('\n')
        print(result.get_captured_data_str())
        print('\n')


async def main():
    """Entry point for eval script."""
    parser = argparse.ArgumentParser(description='Evaluate MCP tools')
    parser.add_argument(
        'task_dir',
        help='Task directory name (relative to evals/, e.g., "applicationsignals")',
    )
    parser.add_argument(
        '--verbose', '-v', action='store_true', help='Enable verbose/debug logging'
    )
    # TODO: Support multiple values (--tasks, --task-ids with nargs='+')
    parser.add_argument(
        '--task',
        help='Run all tasks from specific task file (e.g., investigation_tasks). Can be combined with --task-id',
    )
    parser.add_argument(
        '--task-id',
        help='Run specific task by ID (e.g., petclinic_scheduling_rca). Can be combined with --task to limit scope',
    )
    parser.add_argument('--list', action='store_true', help='List all available tasks and exit')
    parser.add_argument(
        '--no-cleanup',
        action='store_true',
        help='Skip cleanup after evaluation (useful for inspecting changes)',
    )

    args = parser.parse_args()

    if args.verbose:
        logger.add(
            sys.stderr,
            level='DEBUG',
            format='<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{message}</level>',
        )
    else:
        # Without -v: Show only WARNING+ from all modules (user-facing output uses print())
        logger.add(
            sys.stderr,
            level='WARNING',
            format='<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{message}</level>',
        )

    # Resolve task directory (relative to evals/, which is parent of framework/)
    evals_dir = Path(__file__).parent
    task_dir = evals_dir / args.task_dir

    if not task_dir.exists():
        logger.error(f'Task directory not found: {task_dir}')
        logger.error(f'Expected to find it at: {task_dir.absolute()}')
        sys.exit(1)

    print(f'Starting MCP tool evaluation for {args.task_dir}\n')

    all_tasks, tasks_by_module = _discover_tasks(task_dir)

    if not all_tasks:
        logger.error('No tasks found in *_tasks.py files')
        sys.exit(1)

    if args.list:
        print('Available task modules and tasks:\n')
        for module_name, module_tasks in tasks_by_module.items():
            print(f'{module_name}:')
            for task in module_tasks:
                print(f'  - {task.id}')
            print('')
        sys.exit(0)

    # Filter by task module if specified
    if args.task:
        if args.task not in tasks_by_module:
            logger.error(f"Task module '{args.task}' not found")
            print(f'Available modules: {", ".join(tasks_by_module.keys())}')
            sys.exit(1)
        tasks = tasks_by_module[args.task]
    else:
        tasks = all_tasks

    # Filter by task ID if specified
    if args.task_id:
        filtered_tasks = [t for t in tasks if t.id == args.task_id]
        if not filtered_tasks:
            logger.error(f"Task ID '{args.task_id}' not found")
            if args.task:
                print(f'Available tasks in {args.task}: {", ".join(t.id for t in tasks)}')
            else:
                print(f'Available task IDs: {", ".join(t.id for t in all_tasks)}')
            sys.exit(1)
        tasks = filtered_tasks

    print(f'Loaded {len(tasks)} task(s)')
    for task in tasks:
        print(f'  - {task.id}')
    print('')

    # Create runner and execute tasks
    try:
        runner = EvalRunner(tasks=tasks)
        results = await runner.run_all(args.verbose, skip_cleanup=args.no_cleanup)

        # Report results
        for task, result in zip(tasks, results):
            _report_task_results(task, result, verbose=args.verbose)

        # TODO: Investigate more reliable subprocess cleanup mechanism
        # Give subprocess time to clean up before event loop closes (Python < 3.11)
        # MCP SDK's stdio_client relies on __del__ for subprocess cleanup
        await asyncio.sleep(0.1)

    except Exception as e:
        logger.error(f'Evaluation failed: {e}')
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info('\nInterrupted by user')
        sys.exit(0)
