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
