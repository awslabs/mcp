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

from .fixture_resolver import FixtureResolver
from .process_executor import ProcessExecutor, SubprocessExecutor
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Task(ABC):
    """Base class for evaluation tasks.

    Subclasses implement get_prompt() and rubric to define the task prompt and validation criteria.

    Attributes:
        id: Unique identifier for the task
        max_turns: Maximum conversation turns allowed
        expected_tools: MCP tool names expected to be called (for hit rate metric)
        mock_config: Mock configuration for AWS APIs (relative paths, resolved via fixtures_dir)
        fixtures_dir: Base directory for resolving fixture paths
        process_executor: ProcessExecutor for shell commands
    """

    id: str
    max_turns: int = 20
    expected_tools: List[str] = field(default_factory=list)
    mock_config: Optional[Dict[str, Any]] = None
    fixtures_dir: Optional[Path] = None
    process_executor: ProcessExecutor = field(default_factory=SubprocessExecutor)

    @abstractmethod
    def get_prompt(self, context: Dict[str, Any]) -> str:
        """Return task prompt to send to the agent.

        Args:
            context: Runtime context (working_directory, bedrock_client)

        Returns:
            Prompt string to send to agent
        """
        pass

    @property
    @abstractmethod
    def rubric(self) -> list[str]:
        """Return validation criteria for this task."""
        pass

    def get_captors(self, context: Dict[str, Any]) -> List[Any]:
        """Return captors for this task. Override to specify data to capture."""
        return []

    def get_validators(self, context: Dict[str, Any]) -> List[Any]:
        """Return validators for this task. Override to specify validation."""
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
