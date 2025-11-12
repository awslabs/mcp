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

"""Enablement task for Application Signals MCP evaluation.

Evaluates whether the AI agent can use the get_enablement_guide tool
to enable Application Signals monitoring on various platforms.
"""

from evals.core import (
    BuildValidator,
    Captor,
    GitDiffCaptor,
    LLMJudgeValidator,
    Task,
    ToolCallsCaptor,
    ToolResultsCaptor,
    ValidationPromptType,
    Validator,
)
from loguru import logger
from pathlib import Path
from typing import Optional


# MCP server file path
SERVER_PATH = (
    Path(__file__).parent.parent.parent.parent
    / 'awslabs'
    / 'cloudwatch_applicationsignals_mcp_server'
    / 'server.py'
)
# MCP server working directory (cloudwatch-applicationsignals-mcp-server root)
SERVER_CWD = Path(__file__).parent.parent.parent.parent

# Prompt templates
ENABLEMENT_PROMPT = """Enable Application Signals for my {language} {framework} on {platform}.

My infrastructure as code directory is: {iac_abs_path}
My application directory is: {app_abs_path}"""


class EnablementTask(Task):
    """Task for evaluating Application Signals enablement.

    Tests whether the agent can:
    1. Call get_enablement_guide MCP tool correctly
    2. Understand the returned enablement instructions
    3. Modify IaC and application files appropriately
    4. Pass build validation and rubric criteria
    """

    def __init__(
        self,
        id: str,
        prompt_template: str,
        git_paths: list[str],
        iac_dir: str,
        app_dir: str,
        language: str,
        framework: str,
        platform: str,
        validation_rubric: list[str],
        expected_tools: Optional[list[str]] = None,
        build_command: Optional[str] = None,
        build_working_dir: Optional[str] = None,
        modifies_code: bool = True,
    ):
        """Initialize EnablementTask.

        Args:
            id: Task identifier
            prompt_template: Prompt passed to the AI agent doing Application Signals enablement
            git_paths: List of paths (relative to working_directory) for git diff/cleanup
            iac_dir: IaC directory path (relative to working_directory)
            app_dir: Application directory path (relative to working_directory)
            language: Programming language (e.g., 'python', 'java')
            framework: Framework (e.g., 'flask', 'spring-boot')
            platform: Platform (e.g., 'ec2', 'ecs', 'eks')
            validation_rubric: List of validation criteria
            expected_tools: Expected MCP tools to be called
            build_command: Optional build command (e.g., 'npm install && npm run build')
            build_working_dir: Optional build working directory (relative to working_directory)
            modifies_code: Whether task modifies files (for cleanup)
        """
        super().__init__(id=id)
        self.prompt_template = prompt_template
        self.git_paths = git_paths
        self.iac_dir = iac_dir
        self.app_dir = app_dir
        self.language = language
        self.framework = framework
        self.platform = platform
        self.validation_rubric = validation_rubric
        self.expected_tools = expected_tools or ['get_enablement_guide']
        self.build_command = build_command
        self.build_working_dir = build_working_dir
        self.modifies_code = modifies_code

    def get_working_directory(self):
        """Return path to Application Signals samples directory.

        Returns:
            Path to cloudwatch-appplicationsignals-mcp samples directory
        """
        # Calculate path to samples: enablement_tasks.py -> get_enablement_guide/ -> tasks/
        # -> evals/ -> cloudwatch-applicationsignals-mcp-server/ -> src/ -> mcp/ -> samples/
        return (
            Path(__file__).parent.parent.parent.parent.parent.parent
            / 'samples'
            / 'cloudwatch-appplicationsignals-mcp'
            / 'get-enablement-guide-samples'
        )

    def get_server_file(self) -> Path:
        """Return MCP server file path."""
        return SERVER_PATH

    def get_server_root_directory(self) -> Path:
        """Return MCP server root directory."""
        return SERVER_CWD

    def get_prompt(self, working_directory: Path) -> str:
        """Return enablement prompt with absolute paths.

        Args:
            working_directory: Path to task working directory

        Returns:
            Enablement prompt string
        """
        iac_abs_path = working_directory / self.iac_dir
        app_abs_path = working_directory / self.app_dir

        return self.prompt_template.format(
            language=self.language,
            framework=self.framework,
            platform=self.platform,
            iac_abs_path=iac_abs_path,
            app_abs_path=app_abs_path,
        )

    @property
    def rubric(self) -> list[str]:
        """Return validation rubric."""
        return self.validation_rubric

    def get_captors(self, working_directory: Path) -> list[Captor]:
        """Return captors for this task.

        Captures git diff, tool calls, and tool results for evaluation.

        Args:
            working_directory: Path to task working directory

        Returns:
            List of captors
        """
        return [
            GitDiffCaptor(git_paths=self.git_paths),
            ToolCallsCaptor(),
            ToolResultsCaptor(),
        ]

    def get_validators(self, working_directory: Path) -> list[Validator]:
        """Return validators for this task.

        Args:
            working_directory: Path to task working directory

        Returns:
            List of validators (BuildValidator and LLMJudgeValidator)
        """
        from evals.core.llm_provider import BedrockLLMProvider

        validators = []

        if self.build_command and self.build_working_dir:
            build_working_dir = working_directory / self.build_working_dir
            validators.append(
                BuildValidator(
                    command=self.build_command,
                    working_dir=build_working_dir,
                )
            )

        llm_provider = BedrockLLMProvider()
        validators.append(
            LLMJudgeValidator(
                validation_prompt_type=ValidationPromptType.CODE_MODIFICATION,
                llm_provider=llm_provider,
                rubric=self.rubric,
            )
        )

        return validators

    def cleanup(self, working_directory: Path):
        """Clean up git changes made by enablement agent.

        Resets git state for paths specified in git_paths.

        Args:
            working_directory: Path to task working directory
        """
        if not self.git_paths:
            logger.warning('No git_paths specified to clean')
            return

        try:
            for rel_path in self.git_paths:
                full_path = str(working_directory / rel_path)
                logger.debug(f'Cleaning path: {full_path}')
                self.process_executor.run(
                    ['git', 'checkout', 'HEAD', '--', full_path],
                    timeout=10,
                )
                self.process_executor.run(
                    ['git', 'clean', '-fd', full_path],
                    timeout=10,
                )
            logger.debug(f'Reset git state for: {", ".join(self.git_paths)}')
        except Exception as e:
            logger.warning(f'Failed to reset git state: {e}')


# Task definitions
TASKS = []
