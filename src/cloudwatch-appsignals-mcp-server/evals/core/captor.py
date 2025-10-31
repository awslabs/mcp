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


class Captor(ABC):
    """Base class for capturing agent outputs."""

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

    def __init__(self, git_paths: List[str], process_executor: Optional[ProcessExecutor] = None):
        """Initialize GitDiffCaptor.

        Args:
            git_paths: Paths relative to project root to capture git diff for
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
            full_paths = [str(project_root / path) for path in self.git_paths]
            result = self.process_executor.run(
                ['git', 'diff', '--'] + full_paths,
                timeout=10,
            )
            return {'git_diff': result.stdout}
        except Exception as e:
            return {'git_diff': '', 'error': str(e)}


class ToolCallsCaptor(Captor):
    """Captures sequence of tool calls made by agent."""

    def capture(
        self,
        messages: List[Dict[str, Any]],
        metrics_tracker: Any,
        project_root: Path,
    ) -> Dict[str, Any]:
        """Capture tool call sequence."""
        tool_calls = []

        for message in messages:
            if message.get('role') == 'assistant':
                for content in message.get('content', []):
                    if 'toolUse' in content:
                        tool_use = content['toolUse']
                        tool_calls.append(
                            {
                                'name': tool_use['name'],
                                'input': tool_use.get('input', {}),
                            }
                        )

        return {'tool_calls': tool_calls}


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
            if message.get('role') == 'assistant':
                for content in message.get('content', []):
                    if 'text' in content:
                        return {'final_response': content['text']}

        return {'final_response': '', 'error': 'No final response found'}


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
            if message.get('role') == 'user':
                for content in message.get('content', []):
                    if 'toolResult' in content:
                        tool_result = content['toolResult']
                        result_content = tool_result.get('content', [])
                        result_text = ''
                        if result_content:
                            result_text = result_content[0].get('text', '')

                        tool_results.append(
                            {
                                'toolUseId': tool_result.get('toolUseId'),
                                'content': result_text,
                            }
                        )

        return {'tool_results': tool_results}
