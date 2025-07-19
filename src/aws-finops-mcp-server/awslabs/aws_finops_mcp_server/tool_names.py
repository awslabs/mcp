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

"""Tool name mapping for AWS FinOps MCP Server.

This file contains functions to generate shortened tool names that comply with MCP specifications
(max 64 chars when combined with server name, and matching the regex pattern ^[a-zA-Z][a-zA-Z0-9_]*$).
"""

from awslabs.aws_finops_mcp_server.consts import METHOD_ABBR, SERVICE_ABBR


def get_short_tool_name(service: str, method: str) -> str:
    """Get a shortened tool name that complies with MCP specifications.

    Args:
        service: Original service name
        method: Original method name

    Returns:
        str: Shortened tool name
    """
    service_short = SERVICE_ABBR.get(service, service)
    method_short = METHOD_ABBR.get(method, method)

    return f'{service_short}_{method_short}'
