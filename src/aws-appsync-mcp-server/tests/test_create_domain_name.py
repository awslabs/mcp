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

"""Tests for the create_domain_name operation."""

import pytest
from awslabs.aws_appsync_mcp_server.operations.create_domain_name import (
    create_domain_name_operation,
)
from awslabs.aws_appsync_mcp_server.tools.create_domain_name import (
    register_create_domain_name_tool,
)
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_create_domain_name():
    """Test create_domain_name tool with all parameters."""
    mock_client = MagicMock()
    mock_response = {
        'domainNameConfig': {
            'domainName': 'api.example.com',
            'description': 'Custom domain for GraphQL API',
            'certificateArn': 'arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012',
            'appsyncDomainName': 'd-abcdefghij.appsync-api.us-east-1.amazonaws.com',
            'hostedZoneId': 'Z1D633PJN98FT9',
        }
    }
    mock_client.create_domain_name.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_domain_name.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_domain_name_operation(
            domain_name='api.example.com',
            certificate_arn='arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012',
            description='Custom domain for GraphQL API',
            tags={'Environment': 'test'},
        )

        mock_client.create_domain_name.assert_called_once_with(
            domainName='api.example.com',
            certificateArn='arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012',
            description='Custom domain for GraphQL API',
            tags={'Environment': 'test'},
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_domain_name_minimal():
    """Test create_domain_name tool with minimal parameters."""
    mock_client = MagicMock()
    mock_response = {
        'domainNameConfig': {
            'domainName': 'api.example.com',
            'certificateArn': 'arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012',
            'appsyncDomainName': 'd-abcdefghij.appsync-api.us-east-1.amazonaws.com',
            'hostedZoneId': 'Z1D633PJN98FT9',
        }
    }
    mock_client.create_domain_name.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_domain_name.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_domain_name_operation(
            domain_name='api.example.com',
            certificate_arn='arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012',
        )

        mock_client.create_domain_name.assert_called_once_with(
            domainName='api.example.com',
            certificateArn='arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012',
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_domain_name_with_tags_only():
    """Test create_domain_name tool with tags but no description."""
    mock_client = MagicMock()
    mock_response = {
        'domainNameConfig': {
            'domainName': 'api.example.com',
            'certificateArn': 'arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012',
            'appsyncDomainName': 'd-abcdefghij.appsync-api.us-east-1.amazonaws.com',
            'hostedZoneId': 'Z1D633PJN98FT9',
        }
    }
    mock_client.create_domain_name.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_domain_name.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_domain_name_operation(
            domain_name='api.example.com',
            certificate_arn='arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012',
            tags={'Environment': 'prod', 'Team': 'backend'},
        )

        mock_client.create_domain_name.assert_called_once_with(
            domainName='api.example.com',
            certificateArn='arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012',
            tags={'Environment': 'prod', 'Team': 'backend'},
        )
        assert result == mock_response


@pytest.mark.asyncio
async def test_create_domain_name_empty_response():
    """Test create_domain_name tool with empty response."""
    mock_client = MagicMock()
    mock_response = {}
    mock_client.create_domain_name.return_value = mock_response

    with patch(
        'awslabs.aws_appsync_mcp_server.operations.create_domain_name.get_appsync_client',
        return_value=mock_client,
    ):
        result = await create_domain_name_operation(
            domain_name='api.example.com',
            certificate_arn='arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012',
        )

        mock_client.create_domain_name.assert_called_once_with(
            domainName='api.example.com',
            certificateArn='arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012',
        )
        assert result == {'domainNameConfig': {}}


def test_register_create_domain_name_tool():
    """Test that create_domain_name tool is registered correctly."""
    mock_mcp = MagicMock()
    register_create_domain_name_tool(mock_mcp)
    mock_mcp.tool.assert_called_once()


@pytest.mark.asyncio
async def test_create_domain_name_tool_execution():
    """Test create_domain_name tool execution through MCP."""
    from awslabs.aws_appsync_mcp_server.decorators import set_write_allowed
    from typing import Any, Callable

    mock_mcp = MagicMock()
    captured_func: Callable[..., Any] | None = None

    def capture_tool(**kwargs):
        def decorator(func):
            nonlocal captured_func
            captured_func = func
            return func

        return decorator

    mock_mcp.tool = capture_tool
    set_write_allowed(True)

    register_create_domain_name_tool(mock_mcp)

    with patch(
        'awslabs.aws_appsync_mcp_server.tools.create_domain_name.create_domain_name_operation'
    ) as mock_op:
        mock_op.return_value = {'domainNameConfig': {'domainName': 'test.com'}}
        if captured_func is not None:
            result = await captured_func('test.com', 'cert-arn')
            mock_op.assert_called_once_with('test.com', 'cert-arn', None, None)
            assert result == {'domainNameConfig': {'domainName': 'test.com'}}
