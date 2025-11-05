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

"""Base Task class for MCP evaluations."""

from .captor import Captor
from .fixture_resolver import FixtureResolver
from .process_executor import ProcessExecutor, SubprocessExecutor
from .validator import Validator
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Task(ABC):
    """Base class for evaluation tasks.

    A Task defines an evaluation scenario for MCP tools, including the prompt to send
    to an agent and validation criteria. Tasks are defined in `*_tasks.py` files with
    a TASKS list for auto-discovery (see README.md for examples).

    Required Implementations:
        - get_prompt(context): Return the prompt string for the agent
        - rubric: Property returning validation criteria
        - get_server_file(): Return path to MCP server file
        - get_server_root_directory(): Return server root directory

    Optional Overrides:
        - get_captors(context): Return captors to collect execution data
        - get_validators(context): Return validators for custom validation
        - get_working_directory(): Return task working directory
        - cleanup(context): Clean up after execution

    Attributes:
        id: Unique identifier for the task
        max_turns: Maximum conversation turns allowed (default: 20)
        expected_tools: MCP tool names expected to be called (for hit rate metric)
        mock_config: Mock configuration for AWS APIs (relative paths, resolved via fixtures_dir)
        fixtures_dir: Base directory for resolving fixture paths
        process_executor: ProcessExecutor for shell commands (default: SubprocessExecutor)
    """

    id: str
    max_turns: int = 20
    expected_tools: List[str] = field(default_factory=list)
    mock_config: Optional[Dict[str, Any]] = None
    fixtures_dir: Optional[Path] = None
    process_executor: ProcessExecutor = field(default_factory=SubprocessExecutor)

    @abstractmethod
    def get_prompt(self, context: Dict[str, Any]) -> str:
        """Return the prompt/instruction to send to the AI agent.

        The prompt is the core instruction that defines what the agent should do. It triggers
        the agent's reasoning loop where it will use MCP tools to complete the task. The task's
        success is measured by how well the agent fulfills this prompt according to the rubric.

        Args:
            context: Runtime context containing:
                - working_directory: Path to task working directory
                - bedrock_client: Boto3 Bedrock client for LLM calls

        Returns:
            Prompt string describing the task the agent should complete
        """
        pass

    @property
    @abstractmethod
    def rubric(self) -> List[str]:
        """Return validation criteria that define task success.

        The rubric is a list of criteria describing what the agent should accomplish.
        Validators use these to judge whether the task was completed successfully.

        Returns:
            List of criteria strings (e.g., ["Identified root cause", "Proposed fix"])
        """
        pass

    def get_captors(self, context: Dict[str, Any]) -> List[Captor]:
        """Return captors to collect data during task execution.

        Captors extract information from the agent's execution (e.g., tool calls,
        conversation history, git diffs). This data is passed to validators.

        Common captors: GitDiffCaptor, ToolCallsCaptor, ConversationCaptor, FinalResponseCaptor

        Args:
            context: Runtime context (working_directory, bedrock_client)

        Returns:
            List of Captor instances (default: empty list)
        """
        return []

    def get_validators(self, context: Dict[str, Any]) -> List[Validator]:
        """Return validators to evaluate task success.

        Validators use the rubric and captured data to determine if the agent completed
        the task successfully. Multiple validators can be combined.

        Common validators: LLMJudgeValidator, BuildValidator

        Args:
            context: Runtime context (working_directory, bedrock_client)

        Returns:
            List of Validator instances (default: empty list)
        """
        return []

    @property
    def resolved_mock_config(self) -> Optional[dict]:
        """Mock configuration with fixture paths resolved to absolute paths.

        Converts relative fixture paths (e.g., 'services.json') to absolute paths
        based on fixtures_dir (e.g., '/fixtures/services.json').

        Raises:
            ValueError: If mock_config has fixture references but no fixtures_dir
        """
        if not self.mock_config:
            return None

        if self.fixtures_dir is None:
            if FixtureResolver.has_fixture_references(self.mock_config):
                raise ValueError(
                    f"Task '{self.id}' has fixture file references in mock_config but no fixtures_dir specified. "
                    f'Either provide fixtures_dir parameter or use absolute paths/inline mock data.'
                )
            return self.mock_config

        return FixtureResolver.resolve_mock_config(self.mock_config, self.fixtures_dir)

    def get_working_directory(self) -> Optional[Path]:
        """Return working directory for this task. None uses current directory."""
        return None

    @abstractmethod
    def get_server_file(self) -> Path:
        """Return path to the MCP server file."""
        pass

    @abstractmethod
    def get_server_root_directory(self) -> Path:
        """Return root directory of the MCP server (where imports work)."""
        pass

    def cleanup(self, context: Dict[str, Any]) -> None:
        """Clean up after task execution. Override to perform cleanup."""
        pass

    def __str__(self) -> str:
        """Return string representation of the task."""
        return f'Task({self.id})'
