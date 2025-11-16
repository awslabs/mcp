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

"""Validators for evaluating agent outputs."""

import asyncio
import time
from .captor import (
    CONTENT_TEXT,
    FINAL_RESPONSE,
    GIT_DIFF,
    MESSAGE_CONTENT,
    MESSAGE_ROLE,
    ROLE_USER,
    TOOL_CALLS,
)
from .file_tools import PERMITTED_FILE_TOOLS
from .llm_provider import LLMProvider
from .validation_prompts import ValidationPromptType
from abc import ABC, abstractmethod
from loguru import logger
from pathlib import Path
from typing import Any, Dict, List, Literal, TypedDict


class CriterionResult(TypedDict):
    """Result for a single validation criterion."""

    criterion: str
    status: Literal['PASS', 'FAIL']
    reasoning: str


class ValidationResult(TypedDict, total=False):
    """Result from a validator's validate() method.

    Required fields:
        validator_name: Name of the validator
        overall_pass: Whether validation passed overall
        criteria_results: List of individual criterion results

    Optional fields:
        error: Error message if validation failed
        raw_validation_output: Raw validation output (response, execution logs, etc)
    """

    validator_name: str
    overall_pass: bool
    criteria_results: List[CriterionResult]

    error: str
    raw_validation_output: Dict[str, Any]


class Validator(ABC):
    """Base class for output validation."""

    @abstractmethod
    def get_name(self) -> str:
        """Return validator name for display."""
        pass

    # TODO: Refactor to construct validators with captors instead of passing captured_data dict.
    # Captors should have capture() (for framework) and get() (for validators) methods.
    # This would change validate(captured_data) -> validate(self).
    @abstractmethod
    async def validate(
        self,
        captured_data: Dict[str, Any],
    ) -> ValidationResult:
        """Validate captured data.

        Returns ValidationResult with validator_name, overall_pass, criteria_results.
        """
        pass


class LLMJudgeValidator(Validator):
    """LLM-as-judge validator for evaluating captured data against rubric."""

    def __init__(
        self,
        validation_prompt_type: ValidationPromptType,
        llm_provider: LLMProvider,
        rubric: List[str],
    ):
        """Initialize LLM judge validator.

        Args:
            validation_prompt_type: ValidationPromptType enum specifying the template to use
                (e.g., ValidationPromptType.CODE_MODIFICATION, ValidationPromptType.DATA_INTERPRETATION)
            llm_provider: LLMProvider instance for text generation
            rubric: List of evaluation criteria
        """
        self.validation_prompt_type = validation_prompt_type
        self.llm_provider = llm_provider
        self.rubric = rubric
        self.rubric_items = '\n'.join(
            [f'{i + 1}. {criterion}' for i, criterion in enumerate(rubric)]
        )
        self.num_criteria = len(rubric)

    def get_name(self) -> str:
        """Return validator name."""
        return 'LLM Judge'

    async def validate(
        self,
        captured_data: Dict[str, Any],
    ) -> ValidationResult:
        """Validate using LLM as judge."""
        logger.info('Running LLM-as-judge validation...')

        captured_str = self._format_captured_data(captured_data)

        prompt = self.validation_prompt_type.format(
            rubric_items=self.rubric_items,
            captured_data=captured_str,
            num_criteria=self.num_criteria,
        )

        try:
            start = time.time()
            response = self.llm_provider.converse(
                messages=[{MESSAGE_ROLE: ROLE_USER, MESSAGE_CONTENT: [{CONTENT_TEXT: prompt}]}]
            )
            response_text = response['output']['message'][MESSAGE_CONTENT][0][CONTENT_TEXT]
            elapsed = time.time() - start
            logger.debug(f'LLM validation took {elapsed:.2f}s')

            criteria_results = self._parse_llm_response(response_text, self.rubric)
            overall_pass = all(r['status'] == 'PASS' for r in criteria_results)

            return {
                'validator_name': self.get_name(),
                'overall_pass': overall_pass,
                'criteria_results': criteria_results,
                'raw_validation_output': {'response': response_text},
            }
        except Exception as e:
            logger.error(f'LLM validation failed: {e}')
            return {
                'validator_name': self.get_name(),
                'overall_pass': False,
                'error': f'Validation error: {str(e)}',
                'criteria_results': [],
            }

    def _format_captured_data(self, captured_data: Dict[str, Any]) -> str:
        """Format captured data for LLM prompt."""
        sections = []

        if GIT_DIFF in captured_data and captured_data[GIT_DIFF]:
            sections.append(f'**Git Diff:**\n```\n{captured_data[GIT_DIFF]}\n```')

        if FINAL_RESPONSE in captured_data:
            sections.append(f'**Agent Response:**\n{captured_data[FINAL_RESPONSE]}')

        if TOOL_CALLS in captured_data and captured_data[TOOL_CALLS]:
            tool_calls_formatted = []
            for i, call in enumerate(captured_data[TOOL_CALLS], 1):
                status = '✓' if call.get('success') else '✗'
                duration = f'{call.get("duration", 0):.2f}s'
                tool_str = f'{i}. {status} {call["name"]} ({duration})'
                if call.get('input'):
                    tool_str += f'\n   Input: {call["input"]}'
                if call.get('error'):
                    tool_str += f'\n   Error: {call["error"]}'
                tool_calls_formatted.append(tool_str)
            sections.append(f'**Tools Called:**\n{chr(10).join(tool_calls_formatted)}')

        return '\n\n'.join(sections)

    def _parse_llm_response(self, response_text: str, rubric: List[str]) -> List[CriterionResult]:
        """Parse LLM response into structured criteria results.

        Expected format: "1. [PASS] Reasoning" or "1. [FAIL] Reasoning"
        """
        criteria_results = []
        lines = response_text.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            line_upper = line.upper()
            if '[PASS]' in line_upper:
                status = 'PASS'
                pass_idx = line_upper.find('[PASS]')
                reasoning = line[pass_idx + 6 :].strip()
            elif '[FAIL]' in line_upper:
                status = 'FAIL'
                fail_idx = line_upper.find('[FAIL]')
                reasoning = line[fail_idx + 6 :].strip()
            else:
                continue

            if len(criteria_results) < len(rubric):
                criteria_results.append(
                    {
                        'criterion': rubric[len(criteria_results)],
                        'status': status,
                        'reasoning': reasoning if reasoning else line,
                    }
                )

        if len(criteria_results) != len(rubric):
            logger.warning(
                f'LLM validation format mismatch: expected {len(rubric)} criteria, '
                f'parsed {len(criteria_results)} from response. '
                f'Some criteria may not have been evaluated.'
            )
            logger.debug(f'Raw LLM response:\n{response_text}')

            while len(criteria_results) < len(rubric):
                criteria_results.append(
                    {
                        'criterion': rubric[len(criteria_results)],
                        'status': 'FAIL',
                        'reasoning': 'LLM did not provide evaluation for this criterion',
                    }
                )

        return criteria_results


class ToolCallValidator(Validator):
    """Validator that checks tool call ordering."""

    def __init__(self, expected_tool_calls: List[List[str]], ignore_file_tools: bool = False):
        """Initialize tool call validator.

        Args:
            expected_tool_calls: List of possible tool call sequences (list of lists).
                                Only one sequence needs to match exactly.
            ignore_file_tools: If True, filter out file-related tools before validation
        """
        self.expected_tool_calls = expected_tool_calls
        self.ignore_file_tools = ignore_file_tools

    def get_name(self) -> str:
        """Return validator name."""
        return 'Tool Call'

    async def validate(
        self,
        captured_data: Dict[str, Any],
    ) -> ValidationResult:
        """Validate tool calls match one of the expected sequences."""
        logger.info('Validating tool calls...')

        tool_calls = captured_data.get(TOOL_CALLS, [])
        called_tools = [call['name'] for call in tool_calls]

        # Filter out file tools if requested
        if self.ignore_file_tools:
            called_tools = [tool for tool in called_tools if tool not in PERMITTED_FILE_TOOLS]

        # Check if any expected sequence matches
        matched_sequence = None
        for expected_sequence in self.expected_tool_calls:
            if called_tools == expected_sequence:
                matched_sequence = expected_sequence
                break

        if matched_sequence is not None:
            return {
                'validator_name': self.get_name(),
                'overall_pass': True,
                'criteria_results': [
                    {
                        'criterion': 'Tools called in one of expected orders',
                        'status': 'PASS',
                        'reasoning': f'Matched sequence: {" → ".join(matched_sequence)}',
                    }
                ],
                'raw_validation_output': {
                    'expected_tool_calls': self.expected_tool_calls,
                    'called_tools': called_tools,
                    'matched_sequence': matched_sequence,
                    'ignore_file_tools': self.ignore_file_tools,
                },
            }
        else:
            expected_sequences_str = ' OR '.join(
                [f'[{" → ".join(seq)}]' for seq in self.expected_tool_calls]
            )
            return {
                'validator_name': self.get_name(),
                'overall_pass': False,
                'criteria_results': [
                    {
                        'criterion': 'Tools called in one of expected orders',
                        'status': 'FAIL',
                        'reasoning': f'Expected one of: {expected_sequences_str}, got: [{" → ".join(called_tools)}]',
                    }
                ],
                'raw_validation_output': {
                    'expected_tool_calls': self.expected_tool_calls,
                    'called_tools': called_tools,
                    'matched_sequence': None,
                    'ignore_file_tools': self.ignore_file_tools,
                },
            }


class BuildValidator(Validator):
    """Validator that runs build commands and checks exit code."""

    def __init__(
        self,
        command: str,
        working_dir: Path,
        timeout: int = 120,
    ):
        """Initialize build validator.

        Args:
            command: Build command to execute
            working_dir: Directory to run command in
            timeout: Command timeout in seconds
        """
        self.command = command
        self.working_dir = working_dir
        self.timeout = timeout

    def get_name(self) -> str:
        """Return validator name."""
        return 'Build'

    async def validate(
        self,
        captured_data: Dict[str, Any],
    ) -> ValidationResult:
        """Validate by running build command."""
        logger.info(f'Running build command: {self.command}')
        try:
            process = await asyncio.create_subprocess_shell(
                self.command,
                cwd=self.working_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(), timeout=self.timeout
                )
                stdout = stdout_bytes.decode('utf-8', errors='replace')
                stderr = stderr_bytes.decode('utf-8', errors='replace')
                exit_code = process.returncode
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise TimeoutError(f'Build command timed out after {self.timeout} seconds')

            result = {
                'exit_code': exit_code,
                'stdout': stdout,
                'stderr': stderr,
                'success': exit_code == 0,
            }

            if result['success']:
                logger.info('✓ Build succeeded')
                return {
                    'validator_name': self.get_name(),
                    'overall_pass': True,
                    'criteria_results': [
                        {
                            'criterion': 'Build succeeds',
                            'status': 'PASS',
                            'reasoning': 'Build completed with exit code 0',
                        }
                    ],
                    'raw_validation_output': result,
                }
            else:
                logger.error(f'✗ Build failed with exit code {exit_code}')
                return {
                    'validator_name': self.get_name(),
                    'overall_pass': False,
                    'criteria_results': [
                        {
                            'criterion': 'Build succeeds',
                            'status': 'FAIL',
                            'reasoning': f'Build failed with exit code {exit_code}',
                        }
                    ],
                    'raw_validation_output': result,
                }
        except Exception as e:
            logger.error(f'Build validation error: {e}')
            return {
                'validator_name': self.get_name(),
                'overall_pass': False,
                'error': str(e),
                'criteria_results': [
                    {
                        'criterion': 'Build succeeds',
                        'status': 'FAIL',
                        'reasoning': f'Build error: {str(e)}',
                    }
                ],
                'raw_validation_output': {
                    'exit_code': -1,
                    'stdout': '',
                    'stderr': str(e),
                    'success': False,
                },
            }
