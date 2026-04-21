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

"""Common utilities for SSM for SAP MCP Server."""

import json
from datetime import datetime
from typing import Any, Dict


def remove_null_values(d: Dict) -> Dict:
    """Return a new dictionary with key-value pairs of any null value removed."""
    return {k: v for k, v in d.items() if v is not None}


def format_datetime(dt: Any) -> str:
    """Format a datetime value for display."""
    if not dt:
        return 'N/A'
    try:
        if isinstance(dt, datetime):
            return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        return str(dt)
    except Exception:
        return str(dt)


def safe_json_serialize(obj: Any) -> str:
    """Serialize an object to JSON, handling datetime and other non-serializable types."""
    return json.dumps(obj, indent=2, default=str)


def format_client_error(e) -> str:
    """Format a botocore ClientError into a readable 'Code: Message' string."""
    return f'{e.response["Error"]["Code"]}: {e.response["Error"]["Message"]}'


async def request_consent(operation_description: str, acknowledgment_text: str, ctx) -> None:
    """Request explicit user consent before executing a mutating operation.

    Raises ValueError if the user rejects or the client doesn't support elicitation.

    Args:
        operation_description: Human-readable description of the operation.
        acknowledgment_text: Text the user must acknowledge.
        ctx: MCP context object supporting elicitation.
    """
    from mcp.shared.exceptions import McpError
    from mcp.types import METHOD_NOT_FOUND
    from pydantic import BaseModel, Field

    try:
        ConsentModel = type(
            'Consent',
            (BaseModel,),
            {
                '__annotations__': {'acknowledge': bool},
                'acknowledge': Field(description=acknowledgment_text),
            },
        )

        elicitation_result = await ctx.elicit(
            message=(
                f'{operation_description}\n\n'
                'Please review and acknowledge the risk before proceeding.'
            ),
            schema=ConsentModel,
        )

        if elicitation_result.action != 'accept' or not elicitation_result.data.acknowledge:
            raise ValueError('User rejected the operation.')
    except McpError as e:
        if e.error.code == METHOD_NOT_FOUND:
            raise ValueError(
                'Client does not support elicitation. '
                'Cannot proceed without user confirmation for this operation.'
            )
        raise e
