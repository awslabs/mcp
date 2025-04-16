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

"""Tests for the models module of the bedrock-kb-retrieval-mcp-server."""

import pytest
from awslabs.bedrock_kb_retrieval_mcp_server.models import DataSource, KnowledgeBase, KnowledgeBaseMapping


class TestDataSource:
    """Tests for the DataSource model."""

    def test_data_source_creation(self):
        """Test creating a DataSource."""
        data_source = DataSource(id="ds-12345", name="Test Data Source")
        
        assert data_source["id"] == "ds-12345"
        assert data_source["name"] == "Test Data Source"


class TestKnowledgeBase:
    """Tests for the KnowledgeBase model."""

    def test_knowledge_base_creation(self):
        """Test creating a KnowledgeBase."""
        data_sources = [
            DataSource(id="ds-12345", name="Test Data Source"),
            DataSource(id="ds-67890", name="Another Data Source")
        ]
        
        knowledge_base = KnowledgeBase(name="Test Knowledge Base", data_sources=data_sources)
        
        assert knowledge_base["name"] == "Test Knowledge Base"
        assert len(knowledge_base["data_sources"]) == 2
        assert knowledge_base["data_sources"][0]["id"] == "ds-12345"
        assert knowledge_base["data_sources"][0]["name"] == "Test Data Source"
        assert knowledge_base["data_sources"][1]["id"] == "ds-67890"
        assert knowledge_base["data_sources"][1]["name"] == "Another Data Source"


class TestKnowledgeBaseMapping:
    """Tests for the KnowledgeBaseMapping type."""

    def test_knowledge_base_mapping(self):
        """Test creating a KnowledgeBaseMapping."""
        data_sources1 = [DataSource(id="ds-12345", name="Test Data Source")]
        data_sources2 = [DataSource(id="ds-67890", name="Another Data Source")]
        
        kb1 = KnowledgeBase(name="Test Knowledge Base", data_sources=data_sources1)
        kb2 = KnowledgeBase(name="Another Knowledge Base", data_sources=data_sources2)
        
        kb_mapping: KnowledgeBaseMapping = {
            "kb-12345": kb1,
            "kb-67890": kb2
        }
        
        assert len(kb_mapping) == 2
        assert kb_mapping["kb-12345"]["name"] == "Test Knowledge Base"
        assert kb_mapping["kb-67890"]["name"] == "Another Knowledge Base"
        assert kb_mapping["kb-12345"]["data_sources"][0]["id"] == "ds-12345"
        assert kb_mapping["kb-67890"]["data_sources"][0]["id"] == "ds-67890"
