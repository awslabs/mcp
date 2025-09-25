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

"""Test fixtures for the bedrock-kb-retrieval-mcp-server tests."""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_bedrock_agent_runtime_client():
    """Create a mock Bedrock Agent Runtime client."""
    client = MagicMock()
    client.meta.region_name = 'us-west-2'

    # Mock the retrieve method
    retrieve_response = {
        'retrievalResults': [
            {
                'content': {'text': 'This is a test document content.', 'type': 'TEXT'},
                'location': {'s3Location': {'uri': 's3://test-bucket/test-document.txt'}},
                'score': 0.95,
            },
            {
                'content': {'text': 'This is another test document content.', 'type': 'TEXT'},
                'location': {'s3Location': {'uri': 's3://test-bucket/another-document.txt'}},
                'score': 0.85,
            },
        ]
    }
    client.retrieve.return_value = retrieve_response

    return client


@pytest.fixture
def mock_bedrock_agent_client():
    """Create a mock Bedrock Agent client."""
    client = MagicMock()

    # Mock the get_paginator method for list_knowledge_bases
    kb_paginator = MagicMock()
    kb_paginator.paginate.return_value = [
        {
            'knowledgeBaseSummaries': [
                {'knowledgeBaseId': 'kb-12345', 'name': 'Test Knowledge Base'},
                {'knowledgeBaseId': 'kb-67890', 'name': 'Another Knowledge Base'},
                {'knowledgeBaseId': 'kb-95008', 'name': 'Yet another Knowledge Base'},
            ]
        }
    ]

    # Mock the get_paginator method for list_data_sources
    ds_paginator = MagicMock()
    ds_paginator.paginate.return_value = [
        {
            'dataSourceSummaries': [
                {'dataSourceId': 'ds-12345', 'name': 'Test Data Source'},
                {'dataSourceId': 'ds-67890', 'name': 'Another Data Source'},
            ]
        }
    ]

    # Mock the get_knowledge_base method
    client.get_knowledge_base.side_effect = lambda knowledgeBaseId: {
        'knowledgeBase': {
            'knowledgeBaseArn': f'arn:aws:bedrock:us-west-2:123456789012:knowledge-base/{knowledgeBaseId}'
        }
    }

    def list_tags_for_resource_side_effect(resourceArn: str):
        kb_id = resourceArn.split('/')[-1]

        if kb_id == 'kb-95008':
            return {'tags': {'custom-tag': 'true'}}

        return {'tags': {'mcp-multirag-kb': 'true'}}

    # Mock the list_tags_for_resource method
    client.list_tags_for_resource.side_effect = list_tags_for_resource_side_effect

    # Set up the paginator returns
    client.get_paginator.side_effect = lambda operation_name: {
        'list_knowledge_bases': kb_paginator,
        'list_data_sources': ds_paginator,
    }[operation_name]

    return client


@pytest.fixture
def mock_boto3():
    """Create a mock boto3 module."""
    with patch('boto3.client') as mock_client, patch('boto3.Session') as mock_session:
        mock_bedrock_agent_runtime = MagicMock()
        mock_bedrock_agent = MagicMock()

        mock_client.side_effect = lambda service, region_name=None: {
            'bedrock-agent-runtime': mock_bedrock_agent_runtime,
            'bedrock-agent': mock_bedrock_agent,
        }[service]

        mock_session_instance = MagicMock()
        mock_session_instance.client.side_effect = lambda service, region_name=None: {
            'bedrock-agent-runtime': mock_bedrock_agent_runtime,
            'bedrock-agent': mock_bedrock_agent,
        }[service]
        mock_session.return_value = mock_session_instance

        yield {
            'client': mock_client,
            'Session': mock_session,
            'bedrock_agent_runtime': mock_bedrock_agent_runtime,
            'bedrock_agent': mock_bedrock_agent,
        }
