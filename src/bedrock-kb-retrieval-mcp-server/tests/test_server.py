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

"""Tests for the server module of the bedrock-kb-retrieval-mcp-server."""

import json
import pytest
from awslabs.bedrock_kb_retrieval_mcp_server.server import (
    knowledgebases_resource,
    main,
    mcp,
    query_knowledge_bases_tool,
)
from unittest import mock
from unittest.mock import patch


class TestMCPServer:
    """Tests for the MCP server."""

    def test_mcp_initialization(self):
        """Test that the MCP server is initialized correctly."""
        assert mcp.name == 'awslabs.bedrock-kb-retrieval-mcp-server'
        assert (
            mcp.instructions is not None
            and 'AWS Labs Bedrock Knowledge Bases Retrieval MCP Server' in mcp.instructions
        )
        assert 'boto3' in mcp.dependencies


class TestKnowledgebasesResource:
    """Tests for the knowledgebases_resource function."""

    @pytest.mark.asyncio
    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.discover_knowledge_bases')
    async def test_knowledgebases_resource(self, mock_discover_knowledge_bases):
        """Test the knowledgebases_resource function."""
        # Set up the mock
        mock_discover_knowledge_bases.return_value = {
            'kb-12345': {
                'name': 'Test Knowledge Base',
                'data_sources': [
                    {'id': 'ds-12345', 'name': 'Test Data Source'},
                    {'id': 'ds-67890', 'name': 'Another Data Source'},
                ],
            },
            'kb-67890': {
                'name': 'Another Knowledge Base',
                'data_sources': [
                    {'id': 'ds-12345', 'name': 'Test Data Source'},
                ],
            },
        }

        # Call the function
        result = await knowledgebases_resource()

        # Parse the result as JSON
        kb_mapping = json.loads(result)

        # Check that the result is correct
        assert len(kb_mapping) == 2
        assert 'kb-12345' in kb_mapping
        assert 'kb-67890' in kb_mapping
        assert kb_mapping['kb-12345']['name'] == 'Test Knowledge Base'
        assert kb_mapping['kb-67890']['name'] == 'Another Knowledge Base'
        assert len(kb_mapping['kb-12345']['data_sources']) == 2
        assert len(kb_mapping['kb-67890']['data_sources']) == 1
        assert kb_mapping['kb-12345']['data_sources'][0]['id'] == 'ds-12345'
        assert kb_mapping['kb-12345']['data_sources'][0]['name'] == 'Test Data Source'
        assert kb_mapping['kb-12345']['data_sources'][1]['id'] == 'ds-67890'
        assert kb_mapping['kb-12345']['data_sources'][1]['name'] == 'Another Data Source'
        assert kb_mapping['kb-67890']['data_sources'][0]['id'] == 'ds-12345'
        assert kb_mapping['kb-67890']['data_sources'][0]['name'] == 'Test Data Source'

        # Check that discover_knowledge_bases was called with the correct arguments
        mock_discover_knowledge_bases.assert_called_once()


class TestQueryKnowledgeBasesTool:
    """Tests for the query_knowledge_bases_tool function."""

    @pytest.mark.asyncio
    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.query_knowledge_base')
    async def test_query_knowledge_bases_tool(self, mock_query_knowledge_base):
        """Test the query_knowledge_bases_tool function."""
        # Set up the mock
        mock_query_knowledge_base.return_value = json.dumps(
            {
                'content': {'text': 'This is a test document content.', 'type': 'TEXT'},
                'location': {'s3Location': {'uri': 's3://test-bucket/test-document.txt'}},
                'score': 0.95,
            }
        )

        # Call the function
        result = await query_knowledge_bases_tool(
            query='test query',
            knowledge_base_id='kb-12345',
            number_of_results=10,
            reranking=True,
            reranking_model_name='AMAZON',
            data_source_ids=['ds-12345', 'ds-67890'],
        )

        # Check that the result is correct
        assert 'This is a test document content.' in result
        assert 's3://test-bucket/test-document.txt' in result
        assert '0.95' in result

        # Check that query_knowledge_base was called with the correct arguments
        mock_query_knowledge_base.assert_called_once_with(
            query='test query',
            knowledge_base_id='kb-12345',
            kb_agent_client=mock.ANY,  # We can't directly access the global variable in tests
            number_of_results=10,
            reranking=True,
            reranking_model_name='AMAZON',
            data_source_ids=['ds-12345', 'ds-67890'],
        )

    @pytest.mark.asyncio
    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.query_knowledge_base')
    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.kb_id_override', 'EXAMPLEKBID')
    async def test_query_knowledge_bases_tool_with_override_no_kb_id(self, mock_query_knowledge_base):
        """Test the query_knowledge_bases_tool function with override and no knowledge_base_id."""
        # Set up the mock
        mock_query_knowledge_base.return_value = json.dumps(
            {
                'content': {'text': 'This is a test document from override KB.', 'type': 'TEXT'},
                'location': {'s3Location': {'uri': 's3://test-bucket/override-document.txt'}},
                'score': 0.92,
            }
        )

        # Call the function without knowledge_base_id (should use override)
        result = await query_knowledge_bases_tool(
            query='test query without kb id',
            knowledge_base_id=None,
            number_of_results=10,
            reranking=False,
            reranking_model_name='AMAZON',
            data_source_ids=None,
        )

        # Check that the result is correct
        assert 'This is a test document from override KB.' in result
        assert 's3://test-bucket/override-document.txt' in result
        assert '0.92' in result

        # Check that query_knowledge_base was called with the override KB ID
        mock_query_knowledge_base.assert_called_once_with(
            query='test query without kb id',
            knowledge_base_id='EXAMPLEKBID',  # Should use the override
            kb_agent_client=mock.ANY,
            number_of_results=10,
            reranking=False,  # Default value
            reranking_model_name='AMAZON',
            data_source_ids=None,
        )

    @pytest.mark.asyncio
    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.query_knowledge_base')
    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.kb_id_override', 'EXAMPLEKBID')
    async def test_query_knowledge_bases_tool_with_override_and_explicit_kb_id(self, mock_query_knowledge_base):
        """Test the query_knowledge_bases_tool function with override but explicit knowledge_base_id provided."""
        # Set up the mock
        mock_query_knowledge_base.return_value = json.dumps(
            {
                'content': {'text': 'This is a test document from explicit KB.', 'type': 'TEXT'},
                'location': {'s3Location': {'uri': 's3://test-bucket/explicit-document.txt'}},
                'score': 0.88,
            }
        )

        # Call the function with explicit knowledge_base_id (should use explicit, not override)
        result = await query_knowledge_bases_tool(
            query='test query with explicit kb id',
            knowledge_base_id='kb-explicit-123',
            number_of_results=10,
            reranking=False,
            reranking_model_name='AMAZON',
            data_source_ids=None,
        )

        # Check that the result is correct
        assert 'This is a test document from explicit KB.' in result
        assert 's3://test-bucket/explicit-document.txt' in result
        assert '0.88' in result

        # Check that query_knowledge_base was called with the explicit KB ID, not override
        mock_query_knowledge_base.assert_called_once_with(
            query='test query with explicit kb id',
            knowledge_base_id='kb-explicit-123',  # Should use the explicit ID, not override
            kb_agent_client=mock.ANY,
            number_of_results=10,
            reranking=False,  # Default value
            reranking_model_name='AMAZON',
            data_source_ids=None,
        )

    @pytest.mark.asyncio
    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.query_knowledge_base')
    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.kb_id_override', None)
    async def test_query_knowledge_bases_tool_no_override_no_kb_id_raises_error(self, mock_query_knowledge_base):
        """Test the query_knowledge_bases_tool function with no override and no knowledge_base_id raises error."""
        # This should raise a ValueError since neither override nor explicit KB ID is provided
        with pytest.raises(ValueError) as exc_info:
            await query_knowledge_bases_tool(
                query='test query without any kb id',
                knowledge_base_id=None,
                number_of_results=10,
                reranking=False,
                reranking_model_name='AMAZON',
                data_source_ids=None,
            )
        
        assert 'Either knowledge_base_id parameter or BEDROCK_KB_ID environment variable must be provided' in str(exc_info.value)
        
        # query_knowledge_base should not have been called
        mock_query_knowledge_base.assert_not_called()

    @pytest.mark.asyncio
    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.query_knowledge_base')
    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.kb_id_override', 'EXAMPLEKBID')
    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.kb_force_override', True)
    async def test_query_knowledge_bases_tool_force_override_ignores_provided_kb_id(self, mock_query_knowledge_base):
        """Test that force override ignores provided knowledge_base_id and uses environment KB ID."""
        # Set up the mock
        mock_query_knowledge_base.return_value = json.dumps(
            {
                'content': {'text': 'This is a test document from forced override KB.', 'type': 'TEXT'},
                'location': {'s3Location': {'uri': 's3://test-bucket/force-override-document.txt'}},
                'score': 0.95,
            }
        )

        # Call the function with explicit knowledge_base_id (should be ignored due to force override)
        result = await query_knowledge_bases_tool(
            query='test query with force override',
            knowledge_base_id='kb-should-be-ignored',
            number_of_results=10,
            reranking=False,
            reranking_model_name='AMAZON',
            data_source_ids=None,
        )

        # Check that the result is correct
        assert 'This is a test document from forced override KB.' in result
        assert 's3://test-bucket/force-override-document.txt' in result
        assert '0.95' in result

        # Check that query_knowledge_base was called with the force override KB ID, not the provided one
        mock_query_knowledge_base.assert_called_once_with(
            query='test query with force override',
            knowledge_base_id='EXAMPLEKBID',  # Should use the force override, not 'kb-should-be-ignored'
            kb_agent_client=mock.ANY,
            number_of_results=10,
            reranking=False,
            reranking_model_name='AMAZON',
            data_source_ids=None,
        )

    @pytest.mark.asyncio
    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.query_knowledge_base')
    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.kb_id_override', 'EXAMPLEKBID')
    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.kb_force_override', True)
    async def test_query_knowledge_bases_tool_force_override_with_no_kb_id(self, mock_query_knowledge_base):
        """Test that force override works even when no knowledge_base_id is provided."""
        # Set up the mock
        mock_query_knowledge_base.return_value = json.dumps(
            {
                'content': {'text': 'This is a test document from forced override KB without explicit ID.', 'type': 'TEXT'},
                'location': {'s3Location': {'uri': 's3://test-bucket/force-override-no-id-document.txt'}},
                'score': 0.97,
            }
        )

        # Call the function without knowledge_base_id (force override should provide it)
        result = await query_knowledge_bases_tool(
            query='test query with force override and no kb id',
            knowledge_base_id=None,
            number_of_results=10,
            reranking=False,
            reranking_model_name='AMAZON',
            data_source_ids=None,
        )

        # Check that the result is correct
        assert 'This is a test document from forced override KB without explicit ID.' in result
        assert 's3://test-bucket/force-override-no-id-document.txt' in result
        assert '0.97' in result

        # Check that query_knowledge_base was called with the force override KB ID
        mock_query_knowledge_base.assert_called_once_with(
            query='test query with force override and no kb id',
            knowledge_base_id='EXAMPLEKBID',  # Should use the force override
            kb_agent_client=mock.ANY,
            number_of_results=10,
            reranking=False,
            reranking_model_name='AMAZON',
            data_source_ids=None,
        )


class TestMain:
    """Tests for the main function."""

    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.mcp')
    def test_main_default(self, mock_mcp):
        """Test the main function with default arguments."""
        # Set up the mock

        # Call the function
        main()

        # Check that mcp.run was called with the correct arguments
        mock_mcp.run.assert_called_once_with()


class TestServerIntegration:
    """Integration tests for the server module."""

    @pytest.mark.asyncio
    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.discover_knowledge_bases')
    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.query_knowledge_base')
    async def test_server_integration(
        self, mock_query_knowledge_base, mock_discover_knowledge_bases
    ):
        """Test the server integration."""
        # Set up the mocks
        mock_discover_knowledge_bases.return_value = {
            'kb-12345': {
                'name': 'Test Knowledge Base',
                'data_sources': [
                    {'id': 'ds-12345', 'name': 'Test Data Source'},
                ],
            },
        }
        mock_query_knowledge_base.return_value = json.dumps(
            {
                'content': {'text': 'This is a test document content.', 'type': 'TEXT'},
                'location': {'s3Location': {'uri': 's3://test-bucket/test-document.txt'}},
                'score': 0.95,
            }
        )

        # Call the resource function
        kb_result = await knowledgebases_resource()
        kb_mapping = json.loads(kb_result)

        # Check that the resource function returns the correct result
        assert len(kb_mapping) == 1
        assert 'kb-12345' in kb_mapping
        assert kb_mapping['kb-12345']['name'] == 'Test Knowledge Base'
        assert len(kb_mapping['kb-12345']['data_sources']) == 1
        assert kb_mapping['kb-12345']['data_sources'][0]['id'] == 'ds-12345'
        assert kb_mapping['kb-12345']['data_sources'][0]['name'] == 'Test Data Source'

        # Call the tool function
        tool_result = await query_knowledge_bases_tool(
            query='test query',
            knowledge_base_id='kb-12345',
        )

        # Check that the tool function returns the correct result
        assert 'This is a test document content.' in tool_result
        assert 's3://test-bucket/test-document.txt' in tool_result
        assert '0.95' in tool_result
