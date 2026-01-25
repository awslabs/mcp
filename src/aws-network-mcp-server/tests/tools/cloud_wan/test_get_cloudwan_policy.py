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

"""Test cases for the get_cloudwan_policy tool."""

import importlib
import json
import pytest
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


# Get the actual module - prevents function/module resolution issues
policy_module = importlib.import_module(
    'awslabs.aws_network_mcp_server.tools.cloud_wan.get_cloudwan_policy'
)


@patch.object(policy_module, 'get_aws_client')
async def test_get_cwan_policy_success_live(mock_get_client):
    """Test successful Cloud WAN policy retrieval with LIVE alias."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    policy_document = {
        'version': '2021.12',
        'core-network-configuration': {
            'asn-ranges': ['64512-65534'],
            'edge-locations': [{'location': 'us-east-1'}],
        },
        'segments': [{'name': 'production', 'edge-locations': ['us-east-1']}],
    }

    mock_client.get_core_network_policy.return_value = {
        'CoreNetworkPolicy': {
            'CoreNetworkId': 'core-network-123',
            'PolicyVersionId': 1,
            'PolicyDocument': json.dumps(policy_document),
            'ChangeSetState': 'EXECUTED',
            'PolicyErrors': [],
        }
    }

    result = await policy_module.get_cwan_policy('core-network-123', 'us-east-1')

    assert result['core_network_id'] == 'core-network-123'
    assert result['policy_version_id'] == 1
    assert result['policy_document'] == policy_document
    assert result['change_set_state'] == 'EXECUTED'
    assert result['policy_errors'] == []

    mock_client.get_core_network_policy.assert_called_once_with(
        CoreNetworkId='core-network-123', Alias='LIVE'
    )


@patch.object(policy_module, 'get_aws_client')
async def test_get_cwan_policy_success_with_version_id(mock_get_client):
    """Test successful Cloud WAN policy retrieval with specific policy version ID."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    policy_document = {
        'version': '2021.12',
        'segments': [{'name': 'development', 'edge-locations': ['us-west-2']}],
    }

    mock_client.get_core_network_policy.return_value = {
        'CoreNetworkPolicy': {
            'CoreNetworkId': 'core-network-456',
            'PolicyVersionId': 5,
            'PolicyDocument': json.dumps(policy_document),
            'ChangeSetState': 'READY_TO_EXECUTE',
            'PolicyErrors': [],
        }
    }

    result = await policy_module.get_cwan_policy(
        'core-network-456', 'us-west-2', policy_version_id=5
    )

    assert result['core_network_id'] == 'core-network-456'
    assert result['policy_version_id'] == 5
    assert result['policy_document'] == policy_document
    assert result['change_set_state'] == 'READY_TO_EXECUTE'

    mock_client.get_core_network_policy.assert_called_once_with(
        CoreNetworkId='core-network-456', PolicyVersionId=5
    )


@patch.object(policy_module, 'get_aws_client')
async def test_get_cwan_policy_with_profile_name(mock_get_client):
    """Test Cloud WAN policy retrieval with custom profile name."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    mock_client.get_core_network_policy.return_value = {
        'CoreNetworkPolicy': {
            'CoreNetworkId': 'core-network-789',
            'PolicyVersionId': 1,
            'PolicyDocument': '{}',
            'ChangeSetState': 'EXECUTED',
        }
    }

    await policy_module.get_cwan_policy(
        'core-network-789', 'eu-west-1', profile_name='custom-profile'
    )

    mock_get_client.assert_called_once_with('networkmanager', 'eu-west-1', 'custom-profile')


@patch.object(policy_module, 'get_aws_client')
async def test_get_cwan_policy_with_policy_errors(mock_get_client):
    """Test Cloud WAN policy retrieval when policy has errors."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    policy_errors = [
        {'ErrorCode': 'InvalidSegment', 'Message': 'Segment not found'},
    ]

    mock_client.get_core_network_policy.return_value = {
        'CoreNetworkPolicy': {
            'CoreNetworkId': 'core-network-123',
            'PolicyVersionId': 2,
            'PolicyDocument': '{}',
            'ChangeSetState': 'FAILED_GENERATION',
            'PolicyErrors': policy_errors,
        }
    }

    result = await policy_module.get_cwan_policy('core-network-123', 'us-east-1')

    assert result['policy_errors'] == policy_errors
    assert result['change_set_state'] == 'FAILED_GENERATION'


@patch.object(policy_module, 'get_aws_client')
async def test_get_cwan_policy_resource_not_found(mock_get_client):
    """Test error handling when core network or policy is not found."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    # Create a mock exception class
    mock_client.exceptions.ResourceNotFoundException = type(
        'ResourceNotFoundException', (Exception,), {}
    )
    mock_client.get_core_network_policy.side_effect = (
        mock_client.exceptions.ResourceNotFoundException('Not found')
    )

    with pytest.raises(ToolError) as exc_info:
        await policy_module.get_cwan_policy('invalid-network', 'us-east-1')

    assert 'Core network or policy not found' in str(exc_info.value)
    assert 'invalid-network' in str(exc_info.value)


@patch.object(policy_module, 'get_aws_client')
async def test_get_cwan_policy_generic_error(mock_get_client):
    """Test error handling for generic AWS API errors."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    # Setup exception attribute to avoid AttributeError on ResourceNotFoundException check
    mock_client.exceptions.ResourceNotFoundException = type(
        'ResourceNotFoundException', (Exception,), {}
    )
    mock_client.get_core_network_policy.side_effect = Exception('Access denied')

    with pytest.raises(ToolError) as exc_info:
        await policy_module.get_cwan_policy('core-network-123', 'us-east-1')

    assert 'Error getting Cloud WAN policy document' in str(exc_info.value)
    assert 'Access denied' in str(exc_info.value)
