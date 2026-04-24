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

"""Chat tools for AWS Transform MCP server."""

from awslabs.aws_transform_mcp_server.audit import audited_tool
from awslabs.aws_transform_mcp_server.tool_utils import MUTATE
from awslabs.aws_transform_mcp_server.tools.chat.send_message import (
    send_message as _send_message_fn,
)
from typing import Any


class ChatHandler:
    """Registers chat-related MCP tools.

    This handler uses the package pattern: each tool function lives in its
    own module and is imported here for registration. Shared polling logic
    lives in _common.py.
    """

    def __init__(self, mcp: Any) -> None:
        """Register chat tools on the MCP server."""
        audited_tool(
            mcp,
            'send_message',
            title='Send Chat Message',
            annotations=MUTATE,
        )(_send_message_fn)
