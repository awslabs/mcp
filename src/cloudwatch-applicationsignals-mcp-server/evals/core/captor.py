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

"""Captors for extracting data from agent execution."""

from .process_executor import ProcessExecutor, SubprocessExecutor
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional


# Captured data dictionary keys
GIT_DIFF = 'git_diff'
FINAL_RESPONSE = 'final_response'
TOOL_CALLS = 'tool_calls'

# LLM message structure constants
MESSAGE_ROLE = 'role'
ROLE_ASSISTANT = 'assistant'
ROLE_USER = 'user'
MESSAGE_CONTENT = 'content'
CONTENT_TEXT = 'text'
CONTENT_TOOL_USE = 'toolUse'
CONTENT_TOOL_RESULT = 'toolResult'


class Captor(ABC):
    """Base class for capturing agent outputs."""

    # TODO: Return subclassed CaptureData class or use Enums to specify outputs
    @abstractmethod
    def capture(
        self,
        messages: List[Dict[str, Any]],
        metrics_tracker: Any,
        project_root: Path,
    ) -> Dict[str, Any]:
        """Capture output from agent execution.

        Returns dictionary with captured data.
        """
        pass


class GitDiffCaptor(Captor):
    """Captures git diff of file changes made by agent."""

    def __init__(
        self,
        git_paths: Optional[List[str]] = None,
        process_executor: Optional[ProcessExecutor] = None,
    ):
        """Initialize GitDiffCaptor.

        Args:
            git_paths: Paths relative to working_directory to capture git diff for.
                       If None or empty, captures diff for all changes.
            process_executor: ProcessExecutor instance (default: SubprocessExecutor)
        """
        self.git_paths = git_paths
        self.process_executor = (
            process_executor if process_executor is not None else SubprocessExecutor()
        )

    def capture(
        self,
        messages: List[Dict[str, Any]],
        metrics_tracker: Any,
        project_root: Path,
    ) -> Dict[str, Any]:
        """Capture git diff for configured paths."""
        try:
            if self.git_paths:
                full_paths = [str(project_root / path) for path in self.git_paths]
                result = self.process_executor.run(
                    ['git', 'diff', '--'] + full_paths,
                    timeout=10,
                    cwd=str(project_root),
                )
            else:
                # Capture all changes if no specific paths provided
                result = self.process_executor.run(
                    ['git', 'diff'],
                    timeout=10,
                    cwd=str(project_root),
                )
            return {GIT_DIFF: result.stdout}
        except Exception as e:
            return {GIT_DIFF: '', 'error': str(e)}


class ToolCallsCaptor(Captor):
    """Captures sequence of tool calls made by agent."""

    def capture(
        self,
        messages: List[Dict[str, Any]],
        metrics_tracker: Any,
        project_root: Path,
    ) -> Dict[str, Any]:
        """Capture tool call sequence from metrics tracker."""
        tool_calls = [
            {
                'name': call['tool_name'],
                'input': call['parameters'],
                'success': call['success'],
                'duration': call['duration'],
                'error': call.get('error'),
            }
            for call in metrics_tracker.tool_calls
        ]

        return {TOOL_CALLS: tool_calls}


class ConversationCaptor(Captor):
    """Captures full conversation history."""

    def capture(
        self,
        messages: List[Dict[str, Any]],
        metrics_tracker: Any,
        project_root: Path,
    ) -> Dict[str, Any]:
        """Capture full conversation."""
        return {'conversation': messages}


class FinalResponseCaptor(Captor):
    """Captures agent's final text response."""

    def capture(
        self,
        messages: List[Dict[str, Any]],
        metrics_tracker: Any,
        project_root: Path,
    ) -> Dict[str, Any]:
        """Capture final response text."""
        for message in reversed(messages):
            if message.get(MESSAGE_ROLE) == ROLE_ASSISTANT:
                for content in message.get(MESSAGE_CONTENT, []):
                    if CONTENT_TEXT in content:
                        return {FINAL_RESPONSE: content[CONTENT_TEXT]}

        return {FINAL_RESPONSE: '', 'error': 'No final response found'}


class ToolResultsCaptor(Captor):
    """Captures results from tool executions."""

    def capture(
        self,
        messages: List[Dict[str, Any]],
        metrics_tracker: Any,
        project_root: Path,
    ) -> Dict[str, Any]:
        """Capture tool results."""
        tool_results = []

        for message in messages:
            if message.get(MESSAGE_ROLE) == ROLE_USER:
                for content in message.get(MESSAGE_CONTENT, []):
                    if CONTENT_TOOL_RESULT in content:
                        tool_result = content[CONTENT_TOOL_RESULT]
                        result_content = tool_result.get(MESSAGE_CONTENT, [])
                        result_text = ''
                        if result_content:
                            result_text = result_content[0].get(CONTENT_TEXT, '')

                        tool_results.append(
                            {
                                'toolUseId': tool_result.get('toolUseId'),
                                MESSAGE_CONTENT: result_text,
                            }
                        )

        return {'tool_results': tool_results}
