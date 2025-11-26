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

"""Test cases for the detect_cloudwan_inspection tool."""

import importlib
import json
import pytest
from fastmcp.exceptions import ToolError
from unittest.mock import MagicMock, patch


# Get the actual module - this works according to debug
detect_module = importlib.import_module(
    'awslabs.aws_network_mcp_server.tools.cloud_wan.detect_cloudwan_inspection'
)


# WORKING: Use the actual module for patching and function calls
async def test_detect_cloudwan_inspection_with_nfgs():
    """Test successful detection with NFGs in path - WORKING VERSION."""
    with patch.object(detect_module, 'get_aws_client') as mock_get_client:
        mock_nm_client = MagicMock()
        mock_get_client.return_value = mock_nm_client

        policy_doc = {
            'segments': [{'name': 'prod'}, {'name': 'dev'}],
            'network-function-groups': [
                {'name': 'firewall-nfg', 'require-attachment-acceptance': True}
            ],
            'segment-actions': [
                {
                    'segment': 'prod',
                    'action': 'send-via',
                    'via': {'network-function-groups': ['firewall-nfg']},
                    'destinations': ['dev'],
                    'mode': 'single-hop',
                }
            ],
        }

        mock_nm_client.get_core_network_policy.return_value = {
            'CoreNetworkPolicy': {'PolicyDocument': json.dumps(policy_doc)}
        }

        result = await detect_module.detect_cwan_inspection(
            core_network_id='core-network-12345678',
            source_segment='prod',
            destination_segment='dev',
            cloudwan_region='us-east-1',
        )

        assert result['traffic_inspected'] is True
        assert result['total_inspection_nfgs'] == 1
        assert len(result['inspection_nfgs_in_path']) == 1
        assert result['inspection_nfgs_in_path'][0]['nfg_name'] == 'firewall-nfg'

    @patch(
        'awslabs.aws_network_mcp_server.tools.cloud_wan.detect_cloudwan_inspection.get_aws_client'
    )
    async def test_detect_cloudwan_inspection_no_nfgs(self, mock_get_client):
        """Test detection with no NFGs in path."""
        mock_nm_client = MagicMock()
        mock_get_client.return_value = mock_nm_client

        policy_doc = {
            'segments': [{'name': 'prod'}, {'name': 'dev'}],
            'network-function-groups': [],
            'segment-actions': [],
        }

        mock_nm_client.get_core_network_policy.return_value = {
            'CoreNetworkPolicy': {'PolicyDocument': json.dumps(policy_doc)}
        }

        result = await detect_module.detect_cwan_inspection(
            core_network_id='core-network-12345678',
            source_segment='prod',
            destination_segment='dev',
            cloudwan_region='us-east-1',
        )

        assert result['traffic_inspected'] is False
        assert result['total_inspection_nfgs'] == 0
        assert result['inspection_summary'] == 'No inspection NFGs in path - traffic not inspected'

    @patch(
        'awslabs.aws_network_mcp_server.tools.cloud_wan.detect_cloudwan_inspection.get_aws_client'
    )
    async def test_detect_cloudwan_inspection_invalid_segment(self, mock_get_client):
        """Test with invalid segment name."""
        mock_nm_client = MagicMock()
        mock_get_client.return_value = mock_nm_client

        policy_doc = {
            'segments': [{'name': 'prod'}],
            'network-function-groups': [],
            'segment-actions': [],
        }

        mock_nm_client.get_core_network_policy.return_value = {
            'CoreNetworkPolicy': {'PolicyDocument': json.dumps(policy_doc)}
        }

        result = await detect_module.detect_cwan_inspection(
            core_network_id='core-network-12345678',
            source_segment='prod',
            destination_segment='invalid',
            cloudwan_region='us-east-1',
        )

        assert result['success'] is False
        assert 'Destination segment "invalid" not found' in result['error']

    @patch(
        'awslabs.aws_network_mcp_server.tools.cloud_wan.detect_cloudwan_inspection.get_aws_client'
    )
    async def test_detect_cloudwan_inspection_aws_error(self, mock_get_client):
        """Test AWS API error handling."""
        mock_nm_client = MagicMock()
        mock_get_client.return_value = mock_nm_client
        mock_nm_client.get_core_network_policy.side_effect = Exception('AccessDenied')

        with pytest.raises(ToolError, match='Error detecting inspection in path'):
            await detect_module.detect_cwan_inspection(
                core_network_id='core-network-12345678',
                source_segment='prod',
                destination_segment='dev',
                cloudwan_region='us-east-1',
            )


async def test_detect_cloudwan_inspection_malformed_policy():
    """Test handling of malformed policy JSON - CRITICAL SECURITY FIX.

    This test validates that the function gracefully handles malformed policy
    documents from AWS API instead of crashing the entire security analysis.
    """
    with patch.object(detect_module, 'get_aws_client') as mock_get_client:
        mock_nm_client = MagicMock()
        mock_get_client.return_value = mock_nm_client

        # Test malformed JSON policy document
        mock_nm_client.get_core_network_policy.return_value = {
            'CoreNetworkPolicy': {'PolicyDocument': '{"invalid": json"}'}  # Invalid JSON
        }

        result = await detect_module.detect_cwan_inspection(
            core_network_id='core-network-12345678',
            source_segment='prod',
            destination_segment='dev',
            cloudwan_region='us-east-1',
        )

        assert result['success'] is False
        assert 'Invalid policy document JSON' in result['error']
        assert result['core_network_id'] == 'core-network-12345678'
