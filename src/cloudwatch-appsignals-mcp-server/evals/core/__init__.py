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

"""Generic evaluation framework for MCP tools.

This framework provides reusable components for evaluating MCP tools:
- Task: Base class for defining evaluation tasks with prompts, rubrics, and mocks
- Captors: Extract specific outputs (git diff, tool calls, responses)
- Validators: Evaluate captured data against rubrics (LLM judge, build validation)
- Mocking: Mock external dependencies (boto3, etc.) in MCP server subprocess
- EvalRunner: Orchestrate task execution and validation
- MetricsTracker: Track tool usage, success rates, hit rates
"""

# Core abstractions
from .task import Task
from .captor import (
    Captor,
    GitDiffCaptor,
    ToolCallsCaptor,
    ConversationCaptor,
    FinalResponseCaptor,
    ToolResultsCaptor,
)
from .validator import Validator, LLMJudgeValidator, BuildValidator, ValidationPromptType
from .llm_provider import LLMProvider, BedrockLLMProvider
from .process_executor import ProcessExecutor, SubprocessExecutor
from .mock_config_path_normalizer import MockConfigPathNormalizer
from .eval_runner import EvalRunner
from .task_result import TaskResult

# Mocking system
from .mocking import MockHandler, Boto3MockHandler, MockHandlerRegistry, get_registry

# Lower-level utilities
from .agent_loop import execute_tool, run_agent_loop, convert_mcp_tools_to_bedrock
from .file_tools import get_file_tools
from .mcp_client import connect_to_mcp_server
from .metrics_tracker import MetricsTracker


__all__ = [
    # Core classes
    'Task',
    'Captor',
    'Validator',
    'EvalRunner',
    'TaskResult',
    # Built-in captors
    'GitDiffCaptor',
    'ToolCallsCaptor',
    'ConversationCaptor',
    'FinalResponseCaptor',
    'ToolResultsCaptor',
    # Built-in validators
    'LLMJudgeValidator',
    'BuildValidator',
    'ValidationPromptType',
    # LLM providers
    'LLMProvider',
    'BedrockLLMProvider',
    # Process executors
    'ProcessExecutor',
    'SubprocessExecutor',
    # Mock config path normalization
    'MockConfigPathNormalizer',
    # Mocking
    'MockHandler',
    'Boto3MockHandler',
    'MockHandlerRegistry',
    'get_registry',
    # Utilities
    'MetricsTracker',
    'connect_to_mcp_server',
    'convert_mcp_tools_to_bedrock',
    'get_file_tools',
    'execute_tool',
    'run_agent_loop',
]
