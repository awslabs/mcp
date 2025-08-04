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

"""Unit tests for CloudWAN core networking tools."""

import json
import pytest
import os
from unittest.mock import patch, Mock
from botocore.exceptions import ClientError

from awslabs.cloudwan_mcp_server.server import (
    list_core_networks,
    get_global_networks,
    get_core_network_policy,
    get_core_network_change_set,
    get_core_network_change_events
)

@pytest.fixture
def mock_get_aws_client():
    """Mock get_aws_client function with realistic responses."""
    def _mock_client(service, region=None):
        mock_client = Mock()
        
        if service == "networkmanager":
            # Mock core networks response
            mock_client.list_core_networks.return_value = {
                "CoreNetworks": [
                    {
                        "CoreNetworkId": "core-network-1234567890abcdef0",
                        "GlobalNetworkId": "global-network-1234567890abcdef0",
                        "State": "AVAILABLE",
                        "Description": "Test core network",
                        "CreatedAt": "2023-01-01T00:00:00Z"
                    }
                ]
            }
            
            # Mock global networks response
            mock_client.describe_global_networks.return_value = {
                "GlobalNetworks": [
                    {
                        "GlobalNetworkId": "global-network-1234567890abcdef0",
                        "State": "AVAILABLE",
                        "Description": "Test global network",
                        "CreatedAt": "2023-01-01T00:00:00Z"
                    }
                ]
            }
            
            # Mock policy response
            mock_client.get_core_network_policy.return_value = {
                "CoreNetworkPolicy": {
                    "PolicyVersionId": 1,
                    "PolicyDocument": {
                        "version": "2021.12",
                        "core-network-configuration": {
                            "vpn-ecmp-support": False,
                            "asn-ranges": ["64512-65534"]
                        },
                        "segments": [
                            {"name": "production", "require-attachment-acceptance": False}
                        ]
                    },
                    "Description": "Test policy",
                    "CreatedAt": "2023-01-01T00:00:00Z"
                }
            }
            
            # Mock change set response
            mock_client.get_core_network_change_set.return_value = {
                "CoreNetworkChanges": [
                    {
                        "Type": "SEGMENT_MAPPING_CREATE",
                        "Action": "CREATE",
                        "Identifier": "segment-mapping-1"
                    }
                ]
            }
            
            # Mock change events response
            mock_client.get_core_network_change_events.return_value = {
                "CoreNetworkChangeEvents": [
                    {
                        "Type": "POLICY_VERSION_CREATED",
                        "Status": "COMPLETED",
                        "EventTime": "2023-01-01T00:00:00Z"
                    }
                ]
            }
            
        return mock_client
    
    with patch('awslabs.cloudwan_mcp_server.server.get_aws_client', side_effect=_mock_client) as mock:
        yield mock

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
        from awslabs.cloudwan_mcp_server.server import handle_aws_error
        
        result = handle_aws_error(mock_boto_error)
        assert result["success"] is False
        assert result["error_code"] == "ResourceNotFoundException"
        assert "Test error" in result["error"]
        
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