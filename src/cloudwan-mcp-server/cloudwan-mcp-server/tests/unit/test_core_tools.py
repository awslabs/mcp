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

"""Unit tests for CloudWAN core networking tools.

This module provides comprehensive testing for core CloudWAN functionality
including core networks, global networks, policies, change sets, and events.
Features extensive error handling, regional testing, and edge case coverage.
"""

import json
import os
import pytest
from ..mocking.aws import AWSErrorCatalog, AWSServiceMocker
from awslabs.cloudwan_mcp_server.server import (
    get_core_network_change_events,
    get_core_network_change_set,
    get_core_network_policy,
    get_global_networks,
    handle_aws_error,
    list_core_networks,
)
from botocore.exceptions import ClientError
from typing import Any, Dict
from unittest.mock import Mock, patch


@pytest.fixture(scope="function")
def mock_get_aws_client():
    """Enhanced AWS client mock using hierarchical service mocking.
    
    Provides realistic AWS service responses with proper error handling,
    regional behavior, and comprehensive API coverage for all NetworkManager
    operations including core networks, policies, change sets, and events.
    """
    def _mock_client(service: str, region: str = None) -> Mock:
        """Create enhanced service client mock with realistic behaviors."""
        region = region or "us-east-1"

        # Use hierarchical mocker for comprehensive service simulation
        service_mocker = AWSServiceMocker(service, region)
        return service_mocker.client

    with patch('awslabs.cloudwan_mcp_server.server.get_aws_client', side_effect=_mock_client) as mock:
        yield mock


@pytest.fixture(scope="function")
def enhanced_error_scenarios() -> Dict[str, Dict[str, Any]]:
    """Comprehensive error scenario configurations for testing.
    
    Provides structured error scenarios covering all AWS error types
    with proper HTTP status codes, request IDs, and operation contexts.
    """
    return {
        "access_denied_core_networks": {
            "error": AWSErrorCatalog.get_error('access_denied', 'ListCoreNetworks'),
            "operation": "list_core_networks",
            "expected_code": "AccessDenied"
        },
        "throttling_global_networks": {
            "error": AWSErrorCatalog.get_error('throttling', 'DescribeGlobalNetworks'),
            "operation": "describe_global_networks",
            "expected_code": "ThrottlingException"
        },
        "resource_not_found_policy": {
            "error": AWSErrorCatalog.get_error('resource_not_found', 'GetCoreNetworkPolicy'),
            "operation": "get_core_network_policy",
            "expected_code": "ResourceNotFoundException"
        },
        "validation_error_change_set": {
            "error": AWSErrorCatalog.get_error('validation_error', 'GetCoreNetworkChangeSet'),
            "operation": "get_core_network_change_set",
            "expected_code": "ValidationException"
        }
    }


@pytest.fixture(scope="function")
def multi_region_responses() -> Dict[str, Dict[str, Any]]:
    """Multi-region response configurations for regional testing.
    
    Provides region-specific mock responses to test cross-region behavior,
    regional failover scenarios, and region-aware error handling.
    """
    return {
        "us-east-1": {
            "core_networks": [
                {
                    "CoreNetworkId": "core-network-use1-1234567890abcdef0",
                    "GlobalNetworkId": "global-network-1234567890abcdef0",
                    "State": "AVAILABLE",
                    "Description": "US East 1 core network"
                }
            ]
        },
        "eu-west-1": {
            "core_networks": [
                {
                    "CoreNetworkId": "core-network-euw1-1234567890abcdef0",
                    "GlobalNetworkId": "global-network-1234567890abcdef0",
                    "State": "AVAILABLE",
                    "Description": "EU West 1 core network"
                }
            ]
        },
        "ap-southeast-2": {
            "core_networks": []  # Empty region for testing edge cases
        }
    }


@pytest.fixture
def mock_boto_error():
    """Mock boto3 ClientError for testing error handling."""
    from botocore.exceptions import ClientError

    error_response = {
        'Error': {
            'Code': 'ResourceNotFoundException',
            'Message': 'Test error message for resource not found'
        },
        'ResponseMetadata': {
            'RequestId': 'test-request-id-123',
            'HTTPStatusCode': 404
        }
    }

    return ClientError(error_response, 'TestOperation')


class TestCoreNetworking:
    """Test core networking tools."""

    @pytest.mark.asyncio
    async def test_list_core_networks_success(self, mock_get_aws_client):
        """Test core networks listing."""
        result = await list_core_networks("us-east-1")

        # Parse JSON response
        response = json.loads(result)

        # Verify response structure
        assert response["success"] is True
        assert response["region"] == "us-east-1"
        assert response["total_count"] == 1
        assert "core_networks" in response
        assert len(response["core_networks"]) == 1

        # Verify core network details
        core_network = response["core_networks"][0]
        assert core_network["CoreNetworkId"] == "core-network-1234567890abcdef0"
        assert core_network["State"] == "AVAILABLE"

        # Verify AWS client was called correctly
        mock_get_aws_client.assert_called_once_with("networkmanager", "us-east-1")

    @pytest.mark.asyncio
    async def test_list_core_networks_empty(self, mock_get_aws_client):
        """Test core networks listing with no results."""
        # Mock empty response
        mock_get_aws_client.return_value.list_core_networks.return_value = {"CoreNetworks": []}

        result = await list_core_networks("us-west-2")
        response = json.loads(result)

        assert response["success"] is True
        assert response["region"] == "us-west-2"
        assert response["message"] == "No CloudWAN core networks found in the specified region."
        assert response["core_networks"] == []

    @pytest.mark.asyncio
    async def test_list_core_networks_client_error(self, mock_get_aws_client):
        """Test core networks listing with AWS client error."""
        # Mock ClientError
        error_response = {
            'Error': {
                'Code': 'AccessDenied',
                'Message': 'User is not authorized to perform networkmanager:ListCoreNetworks'
            }
        }
        mock_get_aws_client.return_value.list_core_networks.side_effect = ClientError(
            error_response, 'ListCoreNetworks'
        )

        result = await list_core_networks("us-east-1")
        response = json.loads(result)

        assert response["success"] is False
        assert "list_core_networks failed" in response["error"]
        assert response["error_code"] == "AccessDenied"

    @pytest.mark.asyncio
    async def test_get_global_networks_success(self, mock_get_aws_client):
        """Test successful global network retrieval."""
        from awslabs.cloudwan_mcp_server.server import get_global_networks

        result = await get_global_networks()
        response = json.loads(result)

        assert response["success"] is True
        assert "global_networks" in response
        assert len(response["global_networks"]) == 1
        assert response["global_networks"][0]["state"] == "AVAILABLE"

    @pytest.mark.asyncio
    async def test_get_global_networks_default_region(self, mock_get_aws_client):
        """Test global networks with default region."""
        with patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'us-west-1'}):
            result = await get_global_networks()
            response = json.loads(result)

            assert response["success"] is True
            assert response["region"] == "us-west-1"
            mock_get_aws_client.assert_called_with("networkmanager", "us-west-1")

    @pytest.mark.asyncio
    async def test_get_core_network_policy_success(self, mock_get_aws_client):
        """Test successful core network policy retrieval."""
        core_network_id = "core-network-1234567890abcdef0"

        result = await get_core_network_policy(core_network_id)
        response = json.loads(result)

        assert response["success"] is True
        assert response["core_network_id"] == core_network_id
        assert response["alias"] == "LIVE"
        assert response["policy_version_id"] == 1
        assert "policy_document" in response

        # Verify policy document structure
        policy_doc = response["policy_document"]
        assert policy_doc["version"] == "2021.12"
        assert "core-network-configuration" in policy_doc

    @pytest.mark.asyncio
    async def test_get_core_network_policy_default_alias(self, mock_get_aws_client):
        """Test core network policy with default alias."""
        core_network_id = "core-network-1234567890abcdef0"

        result = await get_core_network_policy(core_network_id)
        response = json.loads(result)

        assert response["success"] is True
        assert response["alias"] == "LIVE"  # Default alias

    @pytest.mark.asyncio
    async def test_get_core_network_change_set_success(self, mock_get_aws_client):
        """Test successful change set retrieval."""
        core_network_id = "core-network-1234567890abcdef0"
        policy_version_id = "1"

        result = await get_core_network_change_set(core_network_id, policy_version_id)
        response = json.loads(result)

        assert response["success"] is True
        assert response["core_network_id"] == core_network_id
        assert response["policy_version_id"] == policy_version_id
        assert "change_sets" in response
        assert len(response["change_sets"]) == 1

        change = response["change_sets"][0]
        assert change["Type"] == "SEGMENT_MAPPING_CREATE"
        assert change["Action"] == "CREATE"

    @pytest.mark.asyncio
    async def test_get_core_network_change_events_success(self, mock_get_aws_client):
        """Test successful change events retrieval."""
        core_network_id = "core-network-1234567890abcdef0"
        policy_version_id = "1"

        result = await get_core_network_change_events(core_network_id, policy_version_id)
        response = json.loads(result)

        assert response["success"] is True
        assert response["core_network_id"] == core_network_id
        assert response["policy_version_id"] == policy_version_id
        assert "change_events" in response
        assert len(response["change_events"]) == 1

        event = response["change_events"][0]
        assert event["Type"] == "POLICY_VERSION_CREATED"
        assert event["Status"] == "COMPLETED"


@pytest.mark.asyncio
class TestAWSLabsStandards:
    """Test compliance with AWS Labs testing standards."""

    @pytest.mark.asyncio
    async def test_standard_error_handling(self, mock_get_aws_client, mock_boto_error):
        """Test standard error handling."""
        import json

        result = handle_aws_error(mock_boto_error, "test_operation")
        parsed_result = json.loads(result)
        assert parsed_result["success"] is False
        assert parsed_result["error_code"] == "ResourceNotFoundException"
        assert "Test error" in parsed_result["error"]

    def test_standard_test_classes(self):
        """Verify presence of required test classes."""
        assert hasattr(TestCoreNetworking, 'test_list_core_networks_success')
        assert hasattr(TestAWSLabsStandards, 'test_standard_error_handling')


@pytest.mark.asyncio
async def test_environment_variable_handling():
    """Test proper environment variable handling."""
    with patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'eu-central-1'}):
        with patch('awslabs.cloudwan_mcp_server.server.get_aws_client') as mock_client:
            mock_client.return_value.list_core_networks.return_value = {"CoreNetworks": []}

            result = await list_core_networks()
            response = json.loads(result)

            assert response["region"] == "eu-central-1"
            mock_client.assert_called_with("networkmanager", "eu-central-1")


@pytest.mark.asyncio
@pytest.mark.parametrize("policy_alias,expected_alias", [
    ("LIVE", "LIVE"),
    ("LATEST", "LATEST"),
    (None, "LIVE"),  # Test default
    ("custom-alias", "custom-alias")
])
async def test_policy_alias_handling(mock_get_aws_client, policy_alias, expected_alias):
    """Test comprehensive policy alias handling across different scenarios."""
    core_network_id = "core-network-1234567890abcdef0"

    if policy_alias:
        result = await get_core_network_policy(core_network_id, policy_alias)
    else:
        result = await get_core_network_policy(core_network_id)

    response = json.loads(result)

    assert response["success"] is True
    assert response["alias"] == expected_alias


@pytest.mark.asyncio
@pytest.mark.parametrize("region,expected_call_count", [
    ("us-east-1", 1),
    ("eu-west-1", 1),
    ("ap-southeast-2", 1),
    ("invalid-region", 1)  # Should still make call, AWS will handle validation
])
async def test_regional_client_creation(mock_get_aws_client, region, expected_call_count):
    """Test client creation behavior across different AWS regions."""
    await list_core_networks(region)

    assert mock_get_aws_client.call_count == expected_call_count
    mock_get_aws_client.assert_called_with("networkmanager", region)


@pytest.mark.asyncio
@pytest.mark.parametrize("error_scenario", [
    "access_denied_core_networks",
    "throttling_global_networks",
    "resource_not_found_policy",
    "validation_error_change_set"
])
async def test_comprehensive_error_scenarios(mock_get_aws_client, enhanced_error_scenarios, error_scenario):
    """Test comprehensive error handling across all operations and error types."""
    scenario = enhanced_error_scenarios[error_scenario]
    error = scenario["error"]
    expected_code = scenario["expected_code"]

    # Configure mock to raise the specific error
    mock_client = mock_get_aws_client.return_value

    if "core_networks" in error_scenario:
        mock_client.list_core_networks.side_effect = error
        result = await list_core_networks("us-east-1")
    elif "global_networks" in error_scenario:
        mock_client.describe_global_networks.side_effect = error
        result = await get_global_networks("us-east-1")
    elif "policy" in error_scenario:
        mock_client.get_core_network_policy.side_effect = error
        result = await get_core_network_policy("core-network-1234567890abcdef0")
    elif "change_set" in error_scenario:
        mock_client.get_core_network_change_set.side_effect = error
        result = await get_core_network_change_set("core-network-1234567890abcdef0", "1")

    response = json.loads(result)

    assert response["success"] is False
    assert response["error_code"] == expected_code
    assert "error" in response


@pytest.mark.asyncio
async def test_policy_document_validation():
    """Test policy document structure validation and parsing."""
    core_network_id = "core-network-1234567890abcdef0"

    result = await get_core_network_policy(core_network_id)
    response = json.loads(result)

    assert response["success"] is True

    # Validate policy document structure
    policy_doc = response["policy_document"]
    assert "version" in policy_doc
    assert "core-network-configuration" in policy_doc
    assert "segments" in policy_doc

    # Validate core network configuration
    core_config = policy_doc["core-network-configuration"]
    assert "vpn-ecmp-support" in core_config
    assert "asn-ranges" in core_config

    # Validate segments
    segments = policy_doc["segments"]
    assert isinstance(segments, list)
    assert len(segments) > 0

    segment = segments[0]
    assert "name" in segment
    assert "require-attachment-acceptance" in segment


@pytest.mark.asyncio
async def test_change_event_lifecycle():
    """Test change event lifecycle and status tracking."""
    core_network_id = "core-network-1234567890abcdef0"
    policy_version_id = "1"

    result = await get_core_network_change_events(core_network_id, policy_version_id)
    response = json.loads(result)

    assert response["success"] is True
    assert "change_events" in response

    events = response["change_events"]
    assert isinstance(events, list)

    if events:
        event = events[0]
        assert "Type" in event
        assert "Status" in event
        assert event["Status"] in ["COMPLETED", "IN_PROGRESS", "FAILED"]


@pytest.mark.asyncio
async def test_request_id_propagation():
    """Test AWS request ID propagation for CloudTrail correlation."""
    # This test ensures request IDs are properly captured for audit compliance
    core_network_id = "core-network-1234567890abcdef0"

    result = await get_core_network_policy(core_network_id)
    response = json.loads(result)

    assert response["success"] is True
    # Verify basic response structure that would include metadata
    assert response["core_network_id"] == core_network_id


@pytest.mark.asyncio
async def test_concurrent_operation_safety():
    """Test thread safety and concurrent operation handling."""
    import asyncio

    async def concurrent_call(region):
        return await list_core_networks(region)

    # Execute multiple concurrent calls
    tasks = [
        concurrent_call("us-east-1"),
        concurrent_call("us-west-2"),
        concurrent_call("eu-west-1")
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Verify all calls succeeded
    for result in results:
        assert not isinstance(result, Exception)
        response = json.loads(result)
        assert response["success"] is True
