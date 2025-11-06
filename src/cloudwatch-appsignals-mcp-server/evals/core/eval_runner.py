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

from .llm_provider import BedrockLLMProvider
from .mcp_client import connect_to_mcp_server
from .prompt_executor import PromptExecutor
from .task import Task
from .task_result import TaskResult
from loguru import logger
from mcp import ClientSession
from pathlib import Path
from typing import Any, Dict, List, Optional


class EvalRunner:
    """Orchestrates evaluation of MCP tools using agent-based testing."""

    def __init__(self, tasks: List[Task], executor: Optional[PromptExecutor] = None):
        """Initialize evaluation runner.

        Args:
            tasks: List of Task instances to evaluate
            executor: PromptExecutor instance (default: creates new PromptExecutor)
        """
        self.tasks = tasks
        self.prompt_executor = executor if executor is not None else PromptExecutor()

    async def run_all(
        self,
        bedrock_client: Any,
        verbose: bool = False,
    ) -> List[TaskResult]:
        """Run all tasks and return results."""
        results = []

        for task in self.tasks:
            logger.info(f'Running task: {task.id}')

            try:
                result = await self.run_task(task, bedrock_client, verbose)
                results.append(result)
            except Exception as e:
                logger.error(f'Task {task.id} failed: {e}')
                results.append(TaskResult.from_error(task.id, str(e)))

        return results

    async def run_task(
        self,
        task: Task,
        bedrock_client: Any,
        verbose: bool,
    ) -> TaskResult:
        """Run a single task.

        Connects to MCP server and executes prompt via PromptExecutor.
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

                context = self._create_context(working_directory, bedrock_client)

                task.setup(context)

                prompt = task.get_prompt(context)

                logger.debug(f'Running eval for task {task.id}')
                result = await self.prompt_executor.execute_prompt(
                    prompt=prompt,
                    task=task,
                    session=session,
                    tools_response=tools_response,
                    context=context,
                )

                return result

    def _create_context(self, working_directory: Path, bedrock_client: Any) -> Dict[str, Any]:
        """Create context dictionary for task execution."""
        llm_provider = BedrockLLMProvider(bedrock_client)
        return {
            'working_directory': working_directory,
            'bedrock_client': bedrock_client,
            'llm_provider': llm_provider,
        }
