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
- MetricsTracker: Track tool usage, success rates, hit rates
- Agent loop: Multi-turn conversation orchestration
- File tools: Generic file operations (list, read, write)
- Validation: LLM-as-judge evaluation with rubrics
"""

from .agent import execute_tool, run_agent_loop
from .file_tools import get_file_tools
from .mcp_client import connect_to_mcp_server, convert_mcp_tools_to_bedrock
from .metrics import MetricsTracker
from .validation import run_build_validation, validate_with_llm


__all__ = [
    'MetricsTracker',
    'connect_to_mcp_server',
    'convert_mcp_tools_to_bedrock',
    'get_file_tools',
    'execute_tool',
    'run_agent_loop',
    'validate_with_llm',
    'run_build_validation',
]
