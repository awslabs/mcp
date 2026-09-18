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

"""Error helpers for the Data Processing MCP Server."""

from botocore.exceptions import ClientError
from mcp.types import CallToolResult, TextContent


def create_error_result(exception: Exception, error_message: str) -> CallToolResult:
    """Create a tool error result, adding structured details for AWS client errors."""
    content = [TextContent(type='text', text=error_message)]

    if not isinstance(exception, ClientError):
        return CallToolResult(isError=True, content=content)

    error = exception.response.get('Error') or {}
    metadata = exception.response.get('ResponseMetadata') or {}
    return CallToolResult(
        isError=True,
        structured_content={
            'error': {
                'code': error.get('Code'),
                'error_type': type(exception).__name__,
                'message': error.get('Message'),
                'http_status': metadata.get('HTTPStatusCode'),
                'request_id': metadata.get('RequestId'),
            }
        },
        content=content,
    )
