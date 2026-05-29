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

"""User-agent utilities for AgentCore MCP server usage tracking.

All primitive clients (memory, runtime, browser, code_interpreter) should
use this module to build their user-agent strings. This ensures:

1. Consistent format across all primitives
2. Single source of truth for the server version
3. Distinguishable control plane vs data plane calls in AWS logs

Format: agentcore-mcp-server/{VERSION} {primitive}[-{plane}]

Examples:
    agentcore-mcp-server/0.1.0 memory
    agentcore-mcp-server/0.1.0 memory-control
    agentcore-mcp-server/0.1.0 runtime
    agentcore-mcp-server/0.1.0 runtime-control
    agentcore-mcp-server/0.1.0 browser
    agentcore-mcp-server/0.1.0 code-interpreter
"""

from importlib.metadata import PackageNotFoundError, version


try:
    MCP_SERVER_VERSION = version('awslabs.amazon-bedrock-agentcore-mcp-server')
except PackageNotFoundError:
    MCP_SERVER_VERSION = 'unknown'


def build_user_agent(primitive: str, plane: str = '') -> str:
    """Build a user-agent suffix for boto3 Config.

    Args:
        primitive: The AgentCore primitive name (e.g. 'memory',
            'runtime', 'browser', 'code-interpreter').
        plane: Optional qualifier (e.g. 'control' for control plane
            clients). Omit for data plane or single-client primitives.

    Returns:
        User-agent string like 'agentcore-mcp-server/0.1.0 memory'.
    """
    suffix = f'{primitive}-{plane}' if plane else primitive
    return f'agentcore-mcp-server/{MCP_SERVER_VERSION} {suffix}'
