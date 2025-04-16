# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""Tests for the discovery module of the bedrock-kb-retrieval-mcp-server."""

import pytest
from unittest.mock import MagicMock, patch

from awslabs.bedrock_kb_retrieval_mcp_server.knowledgebases.discovery import (
    discover_knowledge_bases,
    KNOWLEDGE_BASE_TAG_INCLUSION_KEY,
)


class TestDiscoverKnowledgeBases:
    """Tests for the discover_knowledge_bases function."""

    @pytest.mark.asyncio
    async def test_discover_knowledge_bases(self, mock_bedrock_agent_client):
        """Test discovering knowledge bases."""
        # Call the function
        result = await discover_knowledge_bases(mock_bedrock_agent_client)
        
        # Check that the result is correct
        assert len(result) == 2
        assert "kb-12345" in result
        assert "kb-67890" in result
        assert result["kb-12345"]["name"] == "Test Knowledge Base"
        assert result["kb-67890"]["name"] == "Another Knowledge Base"
        assert len(result["kb-12345"]["data_sources"]) == 2
        assert len(result["kb-67890"]["data_sources"]) == 2
        assert result["kb-12345"]["data_sources"][0]["id"] == "ds-12345"
        assert result["kb-12345"]["data_sources"][0]["name"] == "Test Data Source"
        assert result["kb-12345"]["data_sources"][1]["id"] == "ds-67890"
        assert result["kb-12345"]["data_sources"][1]["name"] == "Another Data Source"
        assert result["kb-67890"]["data_sources"][0]["id"] == "ds-12345"
        assert result["kb-67890"]["data_sources"][0]["name"] == "Test Data Source"
        assert result["kb-67890"]["data_sources"][1]["id"] == "ds-67890"
        assert result["kb-67890"]["data_sources"][1]["name"] == "Another Data Source"
        
        # Check that the client methods were called correctly
        mock_bedrock_agent_client.get_paginator.assert_any_call("list_knowledge_bases")
        mock_bedrock_agent_client.get_knowledge_base.assert_any_call(knowledgeBaseId="kb-12345")
        mock_bedrock_agent_client.get_knowledge_base.assert_any_call(knowledgeBaseId="kb-67890")
        mock_bedrock_agent_client.list_tags_for_resource.assert_any_call(
            resourceArn="arn:aws:bedrock:us-west-2:123456789012:knowledge-base/kb-12345"
        )
        mock_bedrock_agent_client.get_paginator.assert_any_call("list_data_sources")

    @pytest.mark.asyncio
    async def test_discover_knowledge_bases_with_custom_tag(self, mock_bedrock_agent_client):
        """Test discovering knowledge bases with a custom tag."""
        # Call the function with a custom tag
        result = await discover_knowledge_bases(
            mock_bedrock_agent_client, tag_key="custom-tag"
        )
        
        # Check that the result is correct
        assert len(result) == 0
        
        # Check that the client methods were called correctly
        mock_bedrock_agent_client.get_paginator.assert_any_call("list_knowledge_bases")
        mock_bedrock_agent_client.get_knowledge_base.assert_any_call(knowledgeBaseId="kb-12345")
        mock_bedrock_agent_client.get_knowledge_base.assert_any_call(knowledgeBaseId="kb-67890")
        mock_bedrock_agent_client.list_tags_for_resource.assert_any_call(
            resourceArn="arn:aws:bedrock:us-west-2:123456789012:knowledge-base/kb-12345"
        )
        
        # The data sources paginator should not be called because no knowledge bases match the tag
        assert not any(
            call[0][0] == "list_data_sources"
            for call in mock_bedrock_agent_client.get_paginator.call_args_list
        )

    @pytest.mark.asyncio
    async def test_discover_knowledge_bases_no_matching_tags(self, mock_bedrock_agent_client):
        """Test discovering knowledge bases with no matching tags."""
        # Modify the mock to return no matching tags
        mock_bedrock_agent_client.list_tags_for_resource.return_value = {"tags": {}}
        
        # Call the function
        result = await discover_knowledge_bases(mock_bedrock_agent_client)
        
        # Check that the result is correct
        assert len(result) == 0
        
        # Check that the client methods were called correctly
        mock_bedrock_agent_client.get_paginator.assert_any_call("list_knowledge_bases")
        mock_bedrock_agent_client.get_knowledge_base.assert_any_call(knowledgeBaseId="kb-12345")
        mock_bedrock_agent_client.get_knowledge_base.assert_any_call(knowledgeBaseId="kb-67890")
        mock_bedrock_agent_client.list_tags_for_resource.assert_any_call(
            resourceArn="arn:aws:bedrock:us-west-2:123456789012:knowledge-base/kb-12345"
        )
        
        # The data sources paginator should not be called because no knowledge bases match the tag
        assert not any(
            call[0][0] == "list_data_sources"
            for call in mock_bedrock_agent_client.get_paginator.call_args_list
        )
   
    @pytest.mark.asyncio
    async def test_discover_knowledge_bases_no_knowledge_bases(self, mock_bedrock_agent_client):
        """Test discovering knowledge bases when there are no knowledge bases."""
        # Modify the mock to return no knowledge bases
        kb_paginator = MagicMock()
        kb_paginator.paginate.return_value = [{"knowledgeBaseSummaries": []}]
        mock_bedrock_agent_client.get_paginator.side_effect = lambda operation_name: {
            "list_knowledge_bases": kb_paginator,
            "list_data_sources": MagicMock(),
        }[operation_name]
        
        # Call the function
        result = await discover_knowledge_bases(mock_bedrock_agent_client)
        
        # Check that the result is correct
        assert len(result) == 0
        
        # Check that the client methods were called correctly
        mock_bedrock_agent_client.get_paginator.assert_any_call("list_knowledge_bases")
        
        # The get_knowledge_base and list_tags_for_resource methods should not be called
        mock_bedrock_agent_client.get_knowledge_base.assert_not_called()
        mock_bedrock_agent_client.list_tags_for_resource.assert_not_called()
        
        # The data sources paginator should not be called
        assert not any(
            call[0][0] == "list_data_sources"
            for call in mock_bedrock_agent_client.get_paginator.call_args_list
        )

    @pytest.mark.asyncio
    async def test_discover_knowledge_bases_no_data_sources(self, mock_bedrock_agent_client):
        """Test discovering knowledge bases when there are no data sources."""
        # Create a mock for knowledge bases paginator
        kb_paginator = MagicMock()
        kb_paginator.paginate.return_value = [
            {
                "knowledgeBaseSummaries": [
                    {
                        "knowledgeBaseId": "kb-12345",
                        "name": "Test Knowledge Base"
                    },
                    {
                        "knowledgeBaseId": "kb-67890",
                        "name": "Another Knowledge Base"
                    }
                ]
            }
        ]
        
        # Create a mock for data sources paginator
        ds_paginator = MagicMock()
        ds_paginator.paginate.return_value = [{"dataSourceSummaries": []}]
        
        # Create a new side_effect function that doesn't cause recursion
        def get_paginator_side_effect(operation_name):
            if operation_name == "list_knowledge_bases":
                return kb_paginator
            elif operation_name == "list_data_sources":
                return ds_paginator
            else:
                return MagicMock()
        
        # Set the side_effect
        mock_bedrock_agent_client.get_paginator.side_effect = get_paginator_side_effect
        
        # Call the function
        result = await discover_knowledge_bases(mock_bedrock_agent_client)
        
        # Check that the result is correct
        assert len(result) == 2
        assert "kb-12345" in result
        assert "kb-67890" in result
        assert result["kb-12345"]["name"] == "Test Knowledge Base"
        assert result["kb-67890"]["name"] == "Another Knowledge Base"
        assert len(result["kb-12345"]["data_sources"]) == 0
        assert len(result["kb-67890"]["data_sources"]) == 0
        
        # Check that the client methods were called correctly
        mock_bedrock_agent_client.get_paginator.assert_any_call("list_knowledge_bases")
        mock_bedrock_agent_client.get_knowledge_base.assert_any_call(knowledgeBaseId="kb-12345")
        mock_bedrock_agent_client.get_knowledge_base.assert_any_call(knowledgeBaseId="kb-67890")
        mock_bedrock_agent_client.list_tags_for_resource.assert_any_call(
            resourceArn="arn:aws:bedrock:us-west-2:123456789012:knowledge-base/kb-12345"
        )
        mock_bedrock_agent_client.get_paginator.assert_any_call("list_data_sources")
