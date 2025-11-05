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

"""Executes prompts with agent loop, captors, and validators."""

from .agent import run_agent_loop
from .eval_runner_result import EvalRunnerResult
from .metrics_tracker import MetricsTracker
from .task import Task
from loguru import logger
from mcp import ClientSession
from pathlib import Path
from typing import Any, Dict


class PromptExecutor:
    """Executes a single prompt through agent loop and validates results."""

    async def execute_prompt(
        self,
        prompt: str,
        task: Task,
        session: ClientSession,
        tools_response: Any,
        context: Dict[str, Any],
    ) -> EvalRunnerResult:
        """Execute a prompt and gather all results.

        Args:
            prompt: Prompt text to send to the agent
            task: Task instance being evaluated
            session: MCP ClientSession for tool calls
            tools_response: Response from session.list_tools()
            context: Context dictionary with working_directory, bedrock_client

        Returns:
            EvalRunnerResult with success, validation_results, metrics, captured_data
        """
        logger.debug('Running eval for task')

        bedrock_client = context['bedrock_client']
        working_directory = context['working_directory']

        metrics_tracker = MetricsTracker()
        messages = await run_agent_loop(
            bedrock_client=bedrock_client,
            session=session,
            prompt=prompt,
            project_root=working_directory,
            mcp_tools=tools_response.tools,
            metrics_tracker=metrics_tracker,
            max_turns=task.max_turns,
        )

        captured_data = await self._execute_captors(
            task, context, messages, metrics_tracker, working_directory, prompt
        )

        validation_results = await self._execute_validators(task, context, captured_data)

        metrics = metrics_tracker.get_metrics(expected_tools=task.expected_tools)

        overall_pass = all(v.get('overall_pass', False) for v in validation_results)

        return EvalRunnerResult.from_success(
            task_id=task.id,
            prompt=prompt,
            success=overall_pass,
            validation_results=validation_results,
            metrics=metrics,
            captured_data=captured_data,
        )

    async def _execute_captors(
        self,
        task: Task,
        context: Dict[str, Any],
        messages: list,
        metrics_tracker: MetricsTracker,
        working_directory: Path,
        prompt: str,
    ) -> Dict[str, Any]:
        """Execute all captors and gather captured data."""
        captured_data = {'prompt': prompt}
        captors = task.get_captors(context)

        for captor in captors:
            captor_output = captor.capture(messages, metrics_tracker, working_directory)
            captured_data.update(captor_output)

        return captured_data

    async def _execute_validators(
        self,
        task: Task,
        context: Dict[str, Any],
        captured_data: Dict[str, Any],
    ) -> list:
        """Execute all validators and gather validation results."""
        validation_results = []
        validators = task.get_validators(context)

        for validator in validators:
            validation_result = await validator.validate(captured_data, task.rubric)
            validation_results.append(validation_result)

        return validation_results
