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

# TODO: Reorganize file structure in focused follow-up PR.
# Current structure has inconsistent naming and all modules in single core/ directory.
# Consider: grouping related modules into subdirectories (validation/, mocking/, execution/, etc.)

# Core abstractions
from .task import Task
from .captor import (
    Captor,
    GitDiffCaptor,
    ToolCallsCaptor,
    ConversationCaptor,
    FinalResponseCaptor,
    ToolResultsCaptor,
    GIT_DIFF,
    FINAL_RESPONSE,
    TOOL_CALLS,
)
from .validator import (
    Validator,
    LLMJudgeValidator,
    BuildValidator,
    ToolCallValidator,
)
from .validation_prompts import ValidationPromptType
from .llm_provider import LLMProvider, BedrockLLMProvider
from .process_executor import ProcessExecutor, SubprocessExecutor
from .mock_config_path_normalizer import MockConfigPathNormalizer
from .eval_runner import EvalRunner
from .task_result import TaskResult

# Mocking system
from .mcp_dependency_mocking_handler import (
    McpDependencyMockingHandler,
    Boto3DependencyMockingHandler,
    McpDependencyMockingHandlerRegistry,
    get_registry,
)

# Lower-level utilities
from .conversation_runner import execute_tool, run_conversation, convert_mcp_tools_to_bedrock
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
    'ToolCallValidator',
    'ValidationPromptType',
    # Captured data constants
    'GIT_DIFF',
    'FINAL_RESPONSE',
    'TOOL_CALLS',
    # LLM providers
    'LLMProvider',
    'BedrockLLMProvider',
    # Process executors
    'ProcessExecutor',
    'SubprocessExecutor',
    # Mock config path normalization
    'MockConfigPathNormalizer',
    # Mocking
    'McpDependencyMockingHandler',
    'Boto3DependencyMockingHandler',
    'McpDependencyMockingHandlerRegistry',
    'get_registry',
    # Utilities
    'MetricsTracker',
    'connect_to_mcp_server',
    'convert_mcp_tools_to_bedrock',
    'get_file_tools',
    'execute_tool',
    'run_conversation',
]
