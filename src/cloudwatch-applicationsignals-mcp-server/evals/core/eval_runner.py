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

"""Evaluation runner orchestrating task execution."""

from .conversation_runner import run_conversation
from .eval_config import MAX_TURNS
from .llm_provider import BedrockLLMProvider
from .mcp_client import connect_to_mcp_server
from .metrics_tracker import MetricsTracker
from .task import Task
from .task_result import TaskResult
from .validator import ValidationResult
from loguru import logger
from mcp import ClientSession
from pathlib import Path
from typing import Any, Dict, List


class EvalRunner:
    """Orchestrates evaluation of MCP tools using agent-based testing."""

    def __init__(self, tasks: List[Task]):
        """Initialize evaluation runner.

        Args:
            tasks: List of Task instances to evaluate
        """
        self.tasks = tasks

    async def run_all(
        self,
        verbose: bool = False,
        skip_cleanup: bool = False,
    ) -> List[TaskResult]:
        """Run all tasks and return results."""
        results = []

        for task in self.tasks:
            logger.info(f'Running task: {task.id}')

            try:
                result = await self.run_task(task, verbose, skip_cleanup)
                results.append(result)
            except Exception as e:
                logger.error(f'Task {task.id} failed: {e}')
                results.append(TaskResult.from_error(task.id, str(e)))

        return results

    async def run_task(
        self,
        task: Task,
        verbose: bool,
        skip_cleanup: bool = False,
    ) -> TaskResult:
        """Run a single task.

        Connects to MCP server, executes agent loop, validates results, and cleans up.
        """
        # TODO: Separate server config from tasks. Task should specify server name,
        # and a separate module should handle server setup/configuration.
        server_file = str(task.get_server_file())
        server_root_dir = str(task.get_server_root_directory())
        mock_config = task.resolved_mock_config
        working_directory = task.get_working_directory() or Path.cwd()

        async with connect_to_mcp_server(
            server_file=server_file,
            server_root_dir=server_root_dir,
            verbose=verbose,
            mock_config=mock_config,
        ) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                tools_response = await session.list_tools()
                logger.debug(f'Connected to MCP server with {len(tools_response.tools)} tools')

                task.setup(working_directory)

                prompt = task.get_prompt(working_directory)

                logger.debug(f'Running eval for task {task.id}')

                # Execute agent loop
                llm_provider = BedrockLLMProvider()
                metrics_tracker = MetricsTracker()
                messages = await run_conversation(
                    llm_provider=llm_provider,
                    session=session,
                    prompt=prompt,
                    project_root=working_directory,
                    mcp_tools=tools_response.tools,
                    metrics_tracker=metrics_tracker,
                    max_turns=MAX_TURNS,
                )

                # Execute captors
                captured_data = await self._execute_captors(
                    task, working_directory, messages, metrics_tracker, prompt
                )

                # Execute validators
                validation_results = await self._execute_validators(
                    task, working_directory, captured_data
                )

                # Gather metrics
                metrics = metrics_tracker.get_metrics_report(expected_tools=task.expected_tools)
                overall_pass = all(v.get('overall_pass', False) for v in validation_results)

                result = TaskResult.from_execution(
                    task_id=task.id,
                    prompt=prompt,
                    success=overall_pass,
                    validation_results=validation_results,
                    metrics=metrics,
                    captured_data=captured_data,
                )

                # Cleanup task changes
                if not skip_cleanup:
                    task.cleanup(working_directory)

                return result

    async def _execute_captors(
        self,
        task: Task,
        working_directory: Path,
        messages: list,
        metrics_tracker: MetricsTracker,
        prompt: str,
    ) -> Dict[str, Any]:
        """Execute all captors and gather captured data."""
        captured_data = {'prompt': prompt}
        captors = task.get_captors(working_directory)

        for captor in captors:
            captor_output = captor.capture(messages, metrics_tracker, working_directory)
            captured_data.update(captor_output)

        return captured_data

    async def _execute_validators(
        self,
        task: Task,
        working_directory: Path,
        captured_data: Dict[str, Any],
    ) -> List[ValidationResult]:
        """Execute all validators and gather validation results."""
        validation_results = []
        validators = task.get_validators(working_directory)

        for validator in validators:
            validation_result = await validator.validate(captured_data)
            validation_results.append(validation_result)

        return validation_results
