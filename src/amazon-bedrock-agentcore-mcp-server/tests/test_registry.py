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

"""Tests for Agent Registry tools."""

import json
from awslabs.amazon_bedrock_agentcore_mcp_server.tools.registry import (
    get_record,
    list_records,
    list_registries,
    search_registry,
)
from unittest.mock import MagicMock, patch


class TestSearchRegistry:
    """Test cases for the search_registry tool function."""

    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.tools.registry._get_dp_client')
    async def test_search_success_with_results(self, mock_get_client):
        """Test search returns JSON with all required fields for matching records."""
        mock_client = MagicMock()
        mock_client.search_registry_records.return_value = {
            'registryRecords': [
                {
                    'name': 'my-mcp-server',
                    'description': 'A useful MCP server',
                    'descriptorType': 'MCP',
                    'status': 'APPROVED',
                    'score': 0.95,
                }
            ]
        }
        mock_get_client.return_value = mock_client

        result = await search_registry(
            query='useful server',
            registry_arn='arn:aws:bedrock:us-west-2:123456789012:registry/my-registry',
        )

        parsed = json.loads(result)
        assert len(parsed) == 1
        record = parsed[0]
        assert record['name'] == 'my-mcp-server'
        assert record['description'] == 'A useful MCP server'
        assert record['type'] == 'MCP'
        assert record['status'] == 'APPROVED'
        assert record['score'] == 0.95

    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.tools.registry._get_dp_client')
    async def test_search_no_results(self, mock_get_client):
        """Test search returns 'No results found' when no records match."""
        mock_client = MagicMock()
        mock_client.search_registry_records.return_value = {'registryRecords': []}
        mock_get_client.return_value = mock_client

        result = await search_registry(
            query='nonexistent',
            registry_arn='arn:aws:bedrock:us-west-2:123456789012:registry/my-registry',
        )

        assert 'No results found' in result

    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.tools.registry._get_dp_client')
    async def test_search_api_error(self, mock_get_client):
        """Test search returns JSON error when API raises an exception."""
        mock_client = MagicMock()
        mock_client.search_registry_records.side_effect = Exception('API error')
        mock_get_client.return_value = mock_client

        result = await search_registry(
            query='test',
            registry_arn='arn:aws:bedrock:us-west-2:123456789012:registry/my-registry',
        )

        parsed = json.loads(result)
        assert 'error' in parsed
        assert 'API error' in parsed['error']

    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.tools.registry._get_dp_client')
    async def test_search_mcp_descriptor_parsing(self, mock_get_client):
        """Test search parses MCP descriptor inline JSON for endpoint, transport, and tools."""
        server_content = json.dumps(
            {
                'packages': [
                    {
                        'transport': {
                            'url': 'https://example.com/mcp',
                            'type': 'sse',
                        }
                    }
                ]
            }
        )
        tools_content = json.dumps(
            {
                'tools': [
                    {'name': 'tool_a'},
                    {'name': 'tool_b'},
                ]
            }
        )
        mock_client = MagicMock()
        mock_client.search_registry_records.return_value = {
            'registryRecords': [
                {
                    'name': 'mcp-server',
                    'description': 'An MCP server',
                    'descriptorType': 'MCP',
                    'status': 'APPROVED',
                    'score': 0.9,
                    'descriptors': {
                        'mcp': {
                            'server': {'inlineContent': server_content},
                            'tools': {'inlineContent': tools_content},
                        }
                    },
                }
            ]
        }
        mock_get_client.return_value = mock_client

        result = await search_registry(
            query='mcp',
            registry_arn='arn:aws:bedrock:us-west-2:123456789012:registry/my-registry',
        )

        parsed = json.loads(result)
        record = parsed[0]
        assert record['endpoint'] == 'https://example.com/mcp'
        assert record['transport_type'] == 'sse'
        assert record['tools'] == ['tool_a', 'tool_b']

    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.tools.registry._get_dp_client')
    async def test_search_malformed_mcp_descriptor(self, mock_get_client):
        """Test search handles malformed MCP descriptor JSON without raising."""
        mock_client = MagicMock()
        mock_client.search_registry_records.return_value = {
            'registryRecords': [
                {
                    'name': 'bad-mcp',
                    'description': 'Bad descriptor',
                    'descriptorType': 'MCP',
                    'status': 'APPROVED',
                    'score': 0.5,
                    'descriptors': {
                        'mcp': {
                            'server': {'inlineContent': '{not valid json!!!'},
                            'tools': {'inlineContent': 'also bad'},
                        }
                    },
                }
            ]
        }
        mock_get_client.return_value = mock_client

        result = await search_registry(
            query='bad',
            registry_arn='arn:aws:bedrock:us-west-2:123456789012:registry/my-registry',
        )

        parsed = json.loads(result)
        assert len(parsed) == 1
        record = parsed[0]
        assert record['name'] == 'bad-mcp'
        assert record['type'] == 'MCP'
        # MCP-specific fields should not be present when parsing fails
        assert 'endpoint' not in record
        assert 'transport_type' not in record


class TestListRecords:
    """Test cases for the list_records tool function."""

    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.tools.registry._get_cp_client')
    async def test_list_records_success(self, mock_get_client):
        """Test list_records returns JSON with all required fields."""
        mock_client = MagicMock()
        mock_client.list_registry_records.return_value = {
            'registryRecords': [
                {
                    'name': 'record-one',
                    'recordId': 'rec-001',
                    'descriptorType': 'MCP',
                    'status': 'APPROVED',
                },
                {
                    'name': 'record-two',
                    'recordId': 'rec-002',
                    'descriptorType': 'A2A',
                    'status': 'PENDING',
                },
            ]
        }
        mock_get_client.return_value = mock_client

        result = await list_records(registry_id='test-registry')

        parsed = json.loads(result)
        assert len(parsed) == 2
        assert parsed[0]['name'] == 'record-one'
        assert parsed[0]['recordId'] == 'rec-001'
        assert parsed[0]['type'] == 'MCP'
        assert parsed[0]['status'] == 'APPROVED'
        assert parsed[1]['name'] == 'record-two'
        assert parsed[1]['recordId'] == 'rec-002'
        assert parsed[1]['type'] == 'A2A'
        assert parsed[1]['status'] == 'PENDING'

    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.tools.registry._get_cp_client')
    async def test_list_records_empty(self, mock_get_client):
        """Test list_records returns empty JSON array when no records exist."""
        mock_client = MagicMock()
        mock_client.list_registry_records.return_value = {'registryRecords': []}
        mock_get_client.return_value = mock_client

        result = await list_records(registry_id='empty-registry')

        parsed = json.loads(result)
        assert parsed == []

    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.tools.registry._get_cp_client')
    async def test_list_records_api_error(self, mock_get_client):
        """Test list_records returns JSON error when API raises an exception."""
        mock_client = MagicMock()
        mock_client.list_registry_records.side_effect = Exception('Access denied')
        mock_get_client.return_value = mock_client

        result = await list_records(registry_id='test-registry')

        parsed = json.loads(result)
        assert 'error' in parsed
        assert 'Access denied' in parsed['error']


class TestGetRecord:
    """Test cases for the get_record tool function."""

    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.tools.registry._get_cp_client')
    async def test_get_record_success(self, mock_get_client):
        """Test get_record returns full record as JSON."""
        mock_client = MagicMock()
        mock_client.get_registry_record.return_value = {
            'name': 'my-record',
            'recordId': 'rec-123',
            'status': 'APPROVED',
            'descriptorType': 'CUSTOM',
            'ResponseMetadata': {'RequestId': 'abc'},
        }
        mock_get_client.return_value = mock_client

        result = await get_record(registry_id='test-registry', record_id='rec-123')

        parsed = json.loads(result)
        assert parsed['name'] == 'my-record'
        assert parsed['recordId'] == 'rec-123'
        assert parsed['status'] == 'APPROVED'

    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.tools.registry._get_cp_client')
    async def test_get_record_strips_response_metadata(self, mock_get_client):
        """Test get_record strips ResponseMetadata from output."""
        mock_client = MagicMock()
        mock_client.get_registry_record.return_value = {
            'name': 'my-record',
            'ResponseMetadata': {'RequestId': 'abc', 'HTTPStatusCode': 200},
        }
        mock_get_client.return_value = mock_client

        result = await get_record(registry_id='test-registry', record_id='rec-123')

        parsed = json.loads(result)
        assert 'ResponseMetadata' not in parsed
        assert parsed['name'] == 'my-record'

    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.tools.registry._get_cp_client')
    async def test_get_record_parses_inline_json(self, mock_get_client):
        """Test get_record parses valid inline JSON and adds 'parsed' field."""
        inline_data = {'key': 'value', 'nested': {'a': 1}}
        mock_client = MagicMock()
        mock_client.get_registry_record.return_value = {
            'name': 'mcp-record',
            'descriptors': {
                'mcp': {
                    'server': {
                        'inlineContent': json.dumps(inline_data),
                    }
                }
            },
            'ResponseMetadata': {'RequestId': 'xyz'},
        }
        mock_get_client.return_value = mock_client

        result = await get_record(registry_id='test-registry', record_id='rec-456')

        parsed = json.loads(result)
        server_desc = parsed['descriptors']['mcp']['server']
        assert 'parsed' in server_desc
        assert server_desc['parsed'] == inline_data

    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.tools.registry._get_cp_client')
    async def test_get_record_malformed_inline_json(self, mock_get_client):
        """Test get_record handles malformed inline JSON without raising."""
        mock_client = MagicMock()
        mock_client.get_registry_record.return_value = {
            'name': 'bad-record',
            'descriptors': {
                'mcp': {
                    'server': {
                        'inlineContent': 'this is not json {{{',
                    }
                }
            },
            'ResponseMetadata': {'RequestId': 'xyz'},
        }
        mock_get_client.return_value = mock_client

        result = await get_record(registry_id='test-registry', record_id='rec-789')

        parsed = json.loads(result)
        server_desc = parsed['descriptors']['mcp']['server']
        assert 'parsed' not in server_desc
        assert server_desc['inlineContent'] == 'this is not json {{{'

    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.tools.registry._get_cp_client')
    async def test_get_record_api_error(self, mock_get_client):
        """Test get_record returns JSON error when API raises an exception."""
        mock_client = MagicMock()
        mock_client.get_registry_record.side_effect = Exception('Record not found')
        mock_get_client.return_value = mock_client

        result = await get_record(registry_id='test-registry', record_id='bad-id')

        parsed = json.loads(result)
        assert 'error' in parsed
        assert 'Record not found' in parsed['error']


class TestListRegistries:
    """Test cases for the list_registries tool function."""

    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.tools.registry._get_cp_client')
    async def test_list_registries_success(self, mock_get_client):
        """Test list_registries returns JSON with all required fields."""
        mock_client = MagicMock()
        mock_client.list_registries.return_value = {
            'registries': [
                {
                    'name': 'prod-registry',
                    'registryId': 'reg-001',
                    'status': 'ACTIVE',
                    'approvalConfiguration': {'autoApproval': True},
                },
                {
                    'name': 'dev-registry',
                    'registryId': 'reg-002',
                    'status': 'ACTIVE',
                    'approvalConfiguration': {'autoApproval': False},
                },
            ]
        }
        mock_get_client.return_value = mock_client

        result = await list_registries()

        parsed = json.loads(result)
        assert len(parsed) == 2
        assert parsed[0]['name'] == 'prod-registry'
        assert parsed[0]['registryId'] == 'reg-001'
        assert parsed[0]['status'] == 'ACTIVE'
        assert parsed[0]['autoApproval'] is True
        assert parsed[1]['name'] == 'dev-registry'
        assert parsed[1]['registryId'] == 'reg-002'
        assert parsed[1]['autoApproval'] is False

    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.tools.registry._get_cp_client')
    async def test_list_registries_empty(self, mock_get_client):
        """Test list_registries returns empty JSON array when no registries exist."""
        mock_client = MagicMock()
        mock_client.list_registries.return_value = {'registries': []}
        mock_get_client.return_value = mock_client

        result = await list_registries()

        parsed = json.loads(result)
        assert parsed == []

    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.tools.registry._get_cp_client')
    async def test_list_registries_api_error(self, mock_get_client):
        """Test list_registries returns JSON error when API raises an exception."""
        mock_client = MagicMock()
        mock_client.list_registries.side_effect = Exception('Service unavailable')
        mock_get_client.return_value = mock_client

        result = await list_registries()

        parsed = json.loads(result)
        assert 'error' in parsed
        assert 'Service unavailable' in parsed['error']


class TestClientInitialization:
    """Test cases for lazy client initialization."""

    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.tools.registry.boto3.Session')
    def test_lazy_init_cp_client(self, mock_session_cls):
        """Test _get_cp_client creates client on first call."""
        import awslabs.amazon_bedrock_agentcore_mcp_server.tools.registry as reg_module

        # Reset module-level client
        reg_module._cp_client = None

        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client

        result = reg_module._get_cp_client()

        assert result is mock_client
        mock_session.client.assert_called_once_with('bedrock-agentcore-control')

        # Clean up
        reg_module._cp_client = None

    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.tools.registry.boto3.Session')
    def test_lazy_init_dp_client(self, mock_session_cls):
        """Test _get_dp_client creates client on first call."""
        import awslabs.amazon_bedrock_agentcore_mcp_server.tools.registry as reg_module

        # Reset module-level client
        reg_module._dp_client = None

        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client

        result = reg_module._get_dp_client()

        assert result is mock_client
        mock_session.client.assert_called_once()
        call_args = mock_session.client.call_args
        assert call_args[0][0] == 'bedrock-agentcore-registry'
        assert 'endpoint_url' in call_args[1]

        # Clean up
        reg_module._dp_client = None

    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.tools.registry.boto3.Session')
    def test_client_reuse(self, mock_session_cls):
        """Test _get_cp_client returns the same object on subsequent calls."""
        import awslabs.amazon_bedrock_agentcore_mcp_server.tools.registry as reg_module

        reg_module._cp_client = None

        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client

        first = reg_module._get_cp_client()
        second = reg_module._get_cp_client()

        assert first is second
        # Session should only be created once
        assert mock_session_cls.call_count == 1

        # Clean up
        reg_module._cp_client = None

    @patch.dict('os.environ', {}, clear=True)
    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.tools.registry.boto3.Session')
    def test_region_default(self, mock_session_cls):
        """Test default region is us-west-2 when AWS_REGION is not set."""
        import awslabs.amazon_bedrock_agentcore_mcp_server.tools.registry as reg_module

        reg_module._cp_client = None

        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_session.client.return_value = MagicMock()

        reg_module._get_cp_client()

        mock_session_cls.assert_called_once_with(region_name='us-west-2')

        # Clean up
        reg_module._cp_client = None

    @patch.dict('os.environ', {'AWS_REGION': 'eu-west-1'})
    @patch('awslabs.amazon_bedrock_agentcore_mcp_server.tools.registry.boto3.Session')
    def test_region_from_env(self, mock_session_cls):
        """Test region is read from AWS_REGION environment variable."""
        import awslabs.amazon_bedrock_agentcore_mcp_server.tools.registry as reg_module

        reg_module._cp_client = None

        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_session.client.return_value = MagicMock()

        reg_module._get_cp_client()

        mock_session_cls.assert_called_once_with(region_name='eu-west-1')

        # Clean up
        reg_module._cp_client = None
