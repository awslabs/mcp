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


"""Unit tests for CloudWAN policy tools."""

import json
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError


@pytest.fixture
def mock_policy_document():
    """Mock CloudWAN policy document fixture."""
    return {
        "version": "2021.12",
        "core-network-configuration": {
            "vpn-ecmp-support": False,
            "asn-ranges": ["64512-65534"],
            "edge-locations": [{"location": "us-east-1", "asn": 64512}],
        },
        "segments": [
            {"name": "production", "require-attachment-acceptance": False, "isolate-attachments": False},
            {"name": "development", "require-attachment-acceptance": True, "isolate-attachments": True},
        ],
    }


@pytest.fixture
def mock_aws_client():
    """Mock AWS client fixture."""
    client = Mock()
    return client


@pytest.fixture
def mock_get_aws_client():
    """Mock the get_aws_client function with NetworkManager responses."""

    def _mock_client(service, region=None):
        client = Mock()

        if service == "networkmanager":
            # Mock policy response
            client.get_core_network_policy.return_value = {
                "CoreNetworkPolicy": {
                    "PolicyVersionId": 1,
                    "PolicyDocument": {
                        "version": "2021.12",
                        "core-network-configuration": {"vpn-ecmp-support": False, "asn-ranges": ["64512-65534"]},
                        "segments": [{"name": "production", "require-attachment-acceptance": False}],
                    },
                    "Description": "Test policy",
                    "CreatedAt": "2023-01-01T00:00:00Z",
                }
            }

            # Mock change set response
            client.get_core_network_change_set.return_value = {
                "CoreNetworkChanges": [
                    {"Type": "SEGMENT_MAPPING_CREATE", "Action": "CREATE", "Identifier": "segment-mapping-1"}
                ]
            }

            # Mock change events response
            client.get_core_network_change_events.return_value = {
                "CoreNetworkChangeEvents": [
                    {"Type": "POLICY_VERSION_CREATED", "Status": "COMPLETED", "EventTime": "2023-01-01T00:00:00Z"}
                ]
            }

        return client

    with patch("awslabs.cloudwan_mcp_server.server.get_aws_client", side_effect=_mock_client) as mock:
        yield mock


class TestPolicyTools:
    """Test CloudWAN policy management tools."""

    @pytest.mark.asyncio
    async def test_get_core_network_policy_default_alias(self, mock_get_aws_client) -> None:
        """Test core network policy retrieval with default alias."""
        from awslabs.cloudwan_mcp_server.server import get_core_network_policy

        core_network_id = "core-network-1234567890abcdef0"

        result = await get_core_network_policy(core_network_id)
        response = json.loads(result)

        assert response["success"] is True
        assert response["core_network_id"] == core_network_id
        assert response["alias"] == "LIVE"  # Default alias
        assert response["policy_version_id"] == 1

    @pytest.mark.asyncio
    async def test_get_core_network_change_set_success(self, mock_get_aws_client) -> None:
        """Test successful change set retrieval."""
        from awslabs.cloudwan_mcp_server.server import get_core_network_change_set

        core_network_id = "core-network-1234567890abcdef0"
        policy_version_id = "1"

        result = await get_core_network_change_set(core_network_id, policy_version_id)
        response = json.loads(result)

        assert response["success"] is True
        assert response["core_network_id"] == core_network_id
        assert response["policy_version_id"] == policy_version_id
        assert "change_sets" in response
        assert len(response["change_sets"]) == 1

    @pytest.mark.asyncio
    async def test_get_core_network_change_events_success(self, mock_get_aws_client) -> None:
        """Test successful change events retrieval."""
        from awslabs.cloudwan_mcp_server.server import get_core_network_change_events

        core_network_id = "core-network-1234567890abcdef0"
        policy_version_id = "1"

        result = await get_core_network_change_events(core_network_id, policy_version_id)
        response = json.loads(result)

        assert response["success"] is True
        assert response["core_network_id"] == core_network_id
        assert response["policy_version_id"] == policy_version_id
        assert "change_events" in response

    @pytest.mark.asyncio
    async def test_validate_cloudwan_policy_with_fixture(self, mock_policy_document, mock_get_aws_client) -> None:
        """Test policy validation with fixture data."""
        from awslabs.cloudwan_mcp_server.server import validate_cloudwan_policy

        result = await validate_cloudwan_policy(mock_policy_document)
        response = json.loads(result)

        assert response["success"] is True
        assert response["overall_status"] == "valid"
        assert response["policy_version"] == "2021.12"

    @pytest.mark.asyncio
    async def test_policy_error_handling(self) -> None:
        """Test policy tools error handling."""
        from awslabs.cloudwan_mcp_server.server import get_core_network_policy

        # Mock client error - create new patch to override fixture
        with patch("awslabs.cloudwan_mcp_server.server.get_aws_client") as mock_get_client:
            mock_client = Mock()
            mock_client.get_core_network_policy.side_effect = ClientError(
                {"Error": {"Code": "ResourceNotFound", "Message": "Core network not found"}}, "GetCoreNetworkPolicy"
            )
            mock_get_client.return_value = mock_client

            result = await get_core_network_policy("nonexistent-core-network")
            response = json.loads(result)

            assert response["success"] is False
            assert "get_core_network_policy failed" in response["error"]
            assert response["error_code"] == "ResourceNotFound"
