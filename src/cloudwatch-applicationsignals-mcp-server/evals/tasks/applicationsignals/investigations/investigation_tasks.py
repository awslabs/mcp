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

"""Investigation tasks for Application Signals MCP evaluation.

Evaluates whether the AI agent can use the Application Signals MCP tool to effectively investigate, root cause, and fix issues.
"""

import shutil
import tempfile
from evals.core import (
    BedrockLLMProvider,
    Captor,
    FinalResponseCaptor,
    GitDiffCaptor,
    LLMJudgeValidator,
    ToolCallsCaptor,
    ToolCallValidator,
    ValidationPromptType,
    Validator,
)
from evals.tasks.applicationsignals import (
    SAMPLES_ROOT,
    ApplicationSignalsTask,
)
from pathlib import Path
from typing import Any, Dict, Optional


class InvestigationTask(ApplicationSignalsTask):
    """Task for evaluating AI agent investigation and root cause analysis capabilities."""

    def __init__(
        self,
        id: str,
        prompt: str,
        validation_rubric: list[str],
        expected_tool_calls: list[list[str]],
        mock_config: Optional[Dict[str, Any]] = None,
        modifies_code: bool = True,
    ):
        """Initialize investigation task."""
        super().__init__(id=id)
        self.fixtures_dir = Path(__file__).parent / 'fixtures'
        self.working_directory = None
        self.prompt = prompt
        self.mock_config = mock_config
        self.validation_rubric = validation_rubric
        self.expected_tool_calls = expected_tool_calls
        self.modifies_code = modifies_code

    def get_working_directory(self) -> Optional[Path]:
        """Get or create working directory for task execution."""
        if not self.working_directory:
            self.working_directory = Path(tempfile.mkdtemp())
        return self.working_directory

    def get_prompt(self, working_directory: Path) -> str:
        """Generate task prompt with working directory path."""
        return (
            self.prompt
            + f' Servce code can be found in {working_directory}. Steps to follow: 1. Determine if/what issue exists 2. Root cause identified issue 2. Make a fix in {working_directory} 3. Provide a summary of the problem (latency, faults, impacted api, etc.), root cause, and root cause location. DO: Focus your changes on just the issue at hand. DO NOT: Test your changes (changes will be tested automatically), make changes unrelated to the exact issue you have identified.'
        )

    def get_captors(self, working_directory: Path) -> list[Captor]:
        """Get captors for recording task execution."""
        return [GitDiffCaptor(), ToolCallsCaptor(), FinalResponseCaptor()]

    def get_validators(self, working_directory: Path) -> list[Validator]:
        """Get validators for verifying task completion."""
        validators = []
        validators.append(
            ToolCallValidator(expected_tool_calls=self.expected_tool_calls, ignore_file_tools=True)
        )
        validators.append(
            LLMJudgeValidator(
                validation_prompt_type=ValidationPromptType.CODE_MODIFICATION,
                llm_provider=BedrockLLMProvider(),
                rubric=self.validation_rubric,
            )
        )
        return validators

    def setup(self, working_directory: Path):
        """Copy sample app files to working directory and initialize git."""
        # Copy files from sample_app_dir to working_directory
        shutil.copytree(
            SAMPLES_ROOT / 'investigations-sample' / 'src', working_directory, dirs_exist_ok=True
        )

        # Initialize git repository
        self.process_executor.run(['git', 'init'], cwd=str(working_directory))
        self.process_executor.run(['git', 'add', '.'], cwd=str(working_directory))
        self.process_executor.run(
            ['git', 'commit', '-m', 'Initial commit'], cwd=str(working_directory)
        )

    def cleanup(self, working_directory: Path):
        """Delete the temporary working directory."""
        shutil.rmtree(working_directory, ignore_errors=True)


# Task definitions
TASKS = [
    InvestigationTask(
        id='bug-4-investigation',
        prompt='Is there anything wrong with my services?',
        validation_rubric=[
            'Agent identifies that the problem is that we are seeing elevated latency in GET /documents/{document_id}',
            'Agent identifies that the root cause is that we are getting ValidationException errors as the document_id is too long, and we do not validate the document_id parameter in DDB calls',
            'Agent makes a fix that would prevent ValidationExceptions due to document_id is too long OR improves error handling to not retry non-retryable errors',
        ],
        # Sometimes the agent will call with "all auditors" first, and other times it will call with "default auditors", then "all auditors".
        expected_tool_calls=[
            [
                'audit_services',
            ],
            [
                'audit_services',
                'audit_services',
            ],
        ],
        mock_config={
            'boto3': {
                'application-signals': {
                    'list_services': [{'request': {}, 'response': 'bug-4-list-services.json'}],
                    'list_audit_findings': [
                        {
                            'request': {},
                            'response': 'bug-4-list-audit-findings-all-services-all-auditors.json',
                        },
                        {
                            'request': {'Auditors': ['slo', 'operation_metric']},
                            'response': 'bug-4-list-audit-findings-all-services-default-auditors.json',
                        },
                        {
                            'request': {
                                'AuditTargets': [
                                    {
                                        'Type': 'service',
                                        'Data': {
                                            'Service': {
                                                'Type': 'Service',
                                                'Name': 'document-manager',
                                                'Environment': 'ec2:default',
                                            }
                                        },
                                    }
                                ]
                            },
                            'response': 'bug-4-list-audit-findings-document-service-and-all-auditors.json',
                        },
                    ],
                }
            }
        },
    ),
]
