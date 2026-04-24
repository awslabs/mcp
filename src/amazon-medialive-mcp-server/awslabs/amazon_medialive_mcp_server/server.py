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

"""MediaLive MCP Server — assembles generated code and overrides into a running FastMCP server.

Dynamically registers MCP tools from the generated operations metadata,
applying description overrides, Tier 2 validation, and read-only/destructive
annotations from the hand-written override modules.
"""

import boto3
import botocore
from awslabs.amazon_medialive_mcp_server.consts import BOTO3_SERVICE_NAME
from awslabs.amazon_medialive_mcp_server.errors import handle_client_error, handle_general_error
from awslabs.amazon_medialive_mcp_server.overrides.descriptions import (
    FIELD_DESCRIPTION_OVERRIDES,
    TOOL_DESCRIPTION_OVERRIDES,
)
from awslabs.amazon_medialive_mcp_server.overrides.instructions import INSTRUCTIONS
from awslabs.amazon_medialive_mcp_server.overrides.tool_config import (
    DESTRUCTIVE_OPERATIONS,
    INCLUDED_OPERATIONS,
    PAGINATION_DEFAULTS,
    READ_ONLY_OPERATIONS,
)
from awslabs.amazon_medialive_mcp_server.overrides.validation import VALIDATORS
from awslabs.amazon_medialive_mcp_server.workflow_context import (
    TOOL_DESCRIPTION as WORKFLOW_TOOL_DESCRIPTION,
)
from awslabs.amazon_medialive_mcp_server.workflow_context import get_media_workflow_context
from botocore.exceptions import ClientError, WaiterError
from loguru import logger
from mcp.server.fastmcp import FastMCP
from packaging.version import Version
from pydantic import BaseModel, Field
from typing import Optional


# Import generated modules — these contain Pydantic models, operations metadata,
# and enum types auto-generated from the botocore service model.
try:
    from awslabs.amazon_medialive_mcp_server import BOTOCORE_SOURCE_VERSION, models
    from awslabs.amazon_medialive_mcp_server.operations import OPERATIONS
except (ImportError, SyntaxError) as exc:  # pragma: no cover
    logger.warning(
        'Generated modules not available ({}). '
        'The generated/ directory must contain valid Python modules.',
        exc,
    )
    BOTOCORE_SOURCE_VERSION = None  # pragma: no cover
    OPERATIONS = {}  # pragma: no cover
    models = None  # pragma: no cover

try:
    from awslabs.amazon_medialive_mcp_server.waiter_config import WAITER_REGISTRY
except (ImportError, SyntaxError):  # pragma: no cover
    WAITER_REGISTRY = {}  # pragma: no cover

mcp = FastMCP('awslabs_medialive_mcp_server', instructions=INSTRUCTIONS)


class WaiterConfig(BaseModel):
    """Optional overrides for waiter polling behavior."""

    Delay: Optional[int] = Field(
        None,
        description='Seconds between polling attempts. Overrides the waiter default.',
    )
    MaxAttempts: Optional[int] = Field(
        None,
        description='Maximum number of polling attempts before timeout. Overrides the waiter default.',
    )


class WaitForResourceInput(BaseModel):
    """Input for the wait_for_resource tool."""

    waiter_name: str = Field(
        ...,
        description="Name of the waiter to invoke (e.g., 'channel_running', 'flow_active'). "
        'Use the tool description to see all supported waiter names for this service.',
    )
    params: dict = Field(
        ...,
        description="API call parameters passed to the waiter's underlying describe operation "
        "(e.g., {'ChannelId': '12345'} for channel_running).",
    )
    waiter_config: Optional[WaiterConfig] = Field(
        None,
        description='Optional overrides for polling interval (Delay) and maximum attempts (MaxAttempts).',
    )


def _check_botocore_version() -> None:
    """Warn if the installed botocore is older than the version used during code generation."""
    if BOTOCORE_SOURCE_VERSION is None:
        logger.warning('BOTOCORE_SOURCE_VERSION not available — skipping version check.')
        return

    installed = Version(botocore.__version__)
    generated_from = Version(BOTOCORE_SOURCE_VERSION)

    if installed < generated_from:
        logger.warning(
            'Installed botocore {} is older than the version used to generate this server ({}). '
            'Consider upgrading boto3: pip install --upgrade boto3',
            botocore.__version__,
            BOTOCORE_SOURCE_VERSION,
        )


def _make_tool_handler(op_name: str, op_meta: dict, client):
    """Factory that creates an async tool handler for a given operation.

    The handler accepts a single typed Pydantic model parameter (required by
    FastMCP which does not support **kwargs), performs Tier 2 validation
    (if registered), serializes to CamelCase for boto3, and returns the
    response or a structured error.
    """
    input_model = op_meta['input_model']
    tool_name = op_meta['tool_name']
    pagination = op_meta.get('pagination')

    async def handler(config: input_model) -> dict:  # type: ignore[valid-type]
        # Serialize to dict with CamelCase aliases for boto3
        params = config.model_dump(by_alias=True, exclude_none=True)

        # Apply default page size for paginated operations
        if pagination is not None:
            limit_key = pagination.get('limit_key')
            if limit_key and limit_key not in params:
                default = PAGINATION_DEFAULTS.get(op_name)
                if default is not None:
                    params[limit_key] = default

        # Tier 2 validation — surgical cross-reference checks
        validator = VALIDATORS.get(op_name)
        if validator is not None:
            errors = validator(params)
            if errors:
                return {'error': 'ValidationError', 'messages': errors}

        # Call the boto3 client
        try:
            client_method = getattr(client, tool_name)
            response = client_method(**params)
            return response
        except ClientError as e:
            return handle_client_error(e)
        except Exception as e:
            return handle_general_error(e)

    # Preserve a meaningful name for debugging
    handler.__name__ = tool_name
    handler.__qualname__ = tool_name

    return handler


def _apply_field_description_overrides_to_model(model_cls: type) -> bool:
    """Apply field-level description overrides to a single Pydantic model class.

    Returns True if any overrides were applied.
    """
    model_name = model_cls.__name__
    overrides_applied = False

    for field_name, field_info in model_cls.model_fields.items():
        key = f'{model_name}.{field_name}'
        if key in FIELD_DESCRIPTION_OVERRIDES:
            field_info.description = FIELD_DESCRIPTION_OVERRIDES[key]
            overrides_applied = True

    if overrides_applied:
        model_cls.model_rebuild()

    return overrides_applied


def _apply_all_field_description_overrides() -> None:
    """Apply field-level description overrides to all generated Pydantic models.

    Iterates over every BaseModel subclass referenced in the generated models module,
    applying overrides keyed by "{ModelName}.{field_name}". This covers nested models
    like H264Settings that are not direct input models for any operation.
    """
    if models is None:
        return

    for attr_name in dir(models):
        attr = getattr(models, attr_name)
        if isinstance(attr, type) and issubclass(attr, BaseModel) and attr is not BaseModel:
            _apply_field_description_overrides_to_model(attr)


def _register_tools() -> None:
    """Iterate over generated OPERATIONS and register each included operation as an MCP tool."""
    if not OPERATIONS:
        logger.error('No operations available — cannot register tools.')
        return

    # Apply field-level description overrides to all generated models once
    _apply_all_field_description_overrides()

    client = boto3.client(BOTO3_SERVICE_NAME)

    for op_name, op_meta in OPERATIONS.items():
        if op_name not in INCLUDED_OPERATIONS:
            continue

        tool_name = op_meta['tool_name']

        # Determine description: override wins, then auto-generated fallback
        description = TOOL_DESCRIPTION_OVERRIDES.get(tool_name, op_meta['auto_description'])

        # Append pagination hints for paginated operations
        pagination = op_meta.get('pagination')
        if pagination is not None:
            output_tokens = pagination.get('output_tokens', [])
            input_tokens = pagination.get('input_tokens', [])
            limit_key = pagination.get('limit_key')

            hint_parts = ['This operation supports pagination.']
            if output_tokens:
                hint_parts.append(f"Check '{output_tokens[0]}' in the response for more pages.")
            if input_tokens:
                hint_parts.append(f"Pass '{input_tokens[0]}' to fetch the next page.")
            if limit_key:
                hint_parts.append(f"Use '{limit_key}' to control page size.")

            description = description + ' ' + ' '.join(hint_parts)

        # Determine annotations
        is_read_only = op_name in READ_ONLY_OPERATIONS
        is_destructive = op_name in DESTRUCTIVE_OPERATIONS

        handler = _make_tool_handler(op_name, op_meta, client)

        # Register with FastMCP
        mcp.tool(
            name=tool_name,
            description=description,
        )(handler)

        logger.debug(
            'Registered tool: {} (read_only={}, destructive={})',
            tool_name,
            is_read_only,
            is_destructive,
        )

    logger.info('Tool registration complete.')


def _register_waiter_tool() -> None:
    """Register the wait_for_resource tool if waiters are available."""
    if not WAITER_REGISTRY:
        logger.info('No waiters available for this service — skipping waiter tool registration.')
        return

    waiter_lines = []
    for name, config in sorted(WAITER_REGISTRY.items()):
        waiter_lines.append(f'- {name}: {config["description"]}')
    waiter_list = '\n'.join(waiter_lines)

    description = (
        f'Wait for a resource to reach a desired state by polling the appropriate '
        f'describe API. Supported waiters:\n{waiter_list}'
    )

    client = boto3.client(BOTO3_SERVICE_NAME)

    async def wait_for_resource(config: WaitForResourceInput) -> dict:  # pragma: no cover
        if config.waiter_name not in WAITER_REGISTRY:
            return {
                'error': 'InvalidWaiterName',
                'message': f"Unknown waiter '{config.waiter_name}'. "
                f'Valid waiters: {sorted(WAITER_REGISTRY.keys())}',
            }

        registry_entry = WAITER_REGISTRY[config.waiter_name]
        boto3_name = registry_entry['boto3_waiter_name']

        waiter_kwargs = {
            'Delay': registry_entry['delay'],
            'MaxAttempts': registry_entry['max_attempts'],
        }
        if config.waiter_config is not None:
            overrides = config.waiter_config.model_dump(exclude_none=True)
            waiter_kwargs.update(overrides)

        logger.info("Invoking waiter '{}' with params={}", config.waiter_name, config.params)

        try:
            waiter = client.get_waiter(boto3_name)
            waiter.wait(WaiterConfig=waiter_kwargs, **config.params)
            return {
                'status': 'success',
                'waiter_name': config.waiter_name,
                'message': f'Resource reached desired state (waiter: {config.waiter_name})',
            }
        except WaiterError as e:
            logger.warning("Waiter '{}' failed: {}", config.waiter_name, e)
            return {
                'error': 'WaiterError',
                'waiter_name': config.waiter_name,
                'message': str(e),
            }
        except ClientError as e:
            return handle_client_error(e)
        except Exception as e:
            return handle_general_error(e)

    wait_for_resource.__name__ = 'wait_for_resource'
    wait_for_resource.__qualname__ = 'wait_for_resource'

    mcp.tool(name='wait_for_resource', description=description)(wait_for_resource)
    logger.info('Registered waiter tool with {} waiters.', len(WAITER_REGISTRY))


def _register_workflow_context_tool() -> None:
    """Register the cross-service workflow context tool on this server."""
    mcp.tool(name='get_media_workflow_context', description=WORKFLOW_TOOL_DESCRIPTION)(
        get_media_workflow_context
    )
    logger.debug('Registered tool: get_media_workflow_context')


# Perform startup checks and register tools at import time
_check_botocore_version()  # pragma: no cover
_register_tools()  # pragma: no cover
_register_waiter_tool()  # pragma: no cover
_register_workflow_context_tool()  # pragma: no cover


def main() -> None:
    """Entry point — run the MCP server over stdio transport."""
    mcp.run(transport='stdio')


if __name__ == '__main__':
    main()
