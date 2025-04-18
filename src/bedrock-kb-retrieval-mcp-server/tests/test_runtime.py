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

"""Tests for the runtime module of the bedrock-kb-retrieval-mcp-server."""

import json
import pytest
from awslabs.bedrock_kb_retrieval_mcp_server.knowledgebases.runtime import query_knowledge_base


class TestQueryKnowledgeBase:
    """Tests for the query_knowledge_base function."""

    @pytest.mark.asyncio
    async def test_query_knowledge_base_default(self, mock_bedrock_agent_runtime_client):
        """Test querying a knowledge base with default parameters."""
        # Call the function
        result = await query_knowledge_base(
            query='test query',
            knowledge_base_id='kb-12345',
            kb_agent_client=mock_bedrock_agent_runtime_client,
        )

        # Parse the result as JSON
        documents = [json.loads(doc) for doc in result.split('\n\n')]

        # Check that the result is correct
        assert len(documents) == 2
        assert documents[0]['content']['text'] == 'This is a test document content.'
        assert documents[0]['content']['type'] == 'TEXT'
        assert (
            documents[0]['location']['s3Location']['uri'] == 's3://test-bucket/test-document.txt'
        )
        assert documents[0]['score'] == 0.95
        assert documents[1]['content']['text'] == 'This is another test document content.'
        assert documents[1]['content']['type'] == 'TEXT'
        assert (
            documents[1]['location']['s3Location']['uri']
            == 's3://test-bucket/another-document.txt'
        )
        assert documents[1]['score'] == 0.85

        # Check that the client methods were called correctly
        mock_bedrock_agent_runtime_client.retrieve.assert_called_once_with(
            knowledgeBaseId='kb-12345',
            retrievalQuery={'text': 'test query'},
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': 20,
                    'rerankingConfiguration': {
                        'type': 'BEDROCK_RERANKING_MODEL',
                        'bedrockRerankingConfiguration': {
                            'modelConfiguration': {
                                'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/amazon.rerank-v1:0'
                            }
                        },
                    },
                }
            },
        )

    @pytest.mark.asyncio
    async def test_query_knowledge_base_with_custom_parameters(
        self, mock_bedrock_agent_runtime_client
    ):
        """Test querying a knowledge base with custom parameters."""
        # Call the function with custom parameters
        result = await query_knowledge_base(
            query='test query',
            knowledge_base_id='kb-12345',
            kb_agent_client=mock_bedrock_agent_runtime_client,
            number_of_results=10,
            reranking=True,
            reranking_model_name='COHERE',
            data_source_ids=['ds-12345', 'ds-67890'],
        )

        # Parse the result as JSON
        documents = [json.loads(doc) for doc in result.split('\n\n')]

        # Check that the result is correct
        assert len(documents) == 2

        # Check that the client methods were called correctly
        mock_bedrock_agent_runtime_client.retrieve.assert_called_once_with(
            knowledgeBaseId='kb-12345',
            retrievalQuery={'text': 'test query'},
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': 10,
                    'filter': {
                        'in': {
                            'key': 'x-amz-bedrock-kb-data-source-id',
                            'value': ['ds-12345', 'ds-67890'],
                        }
                    },
                    'rerankingConfiguration': {
                        'type': 'BEDROCK_RERANKING_MODEL',
                        'bedrockRerankingConfiguration': {
                            'modelConfiguration': {
                                'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/cohere.rerank-v3-5:0'
                            }
                        },
                    },
                }
            },
        )

    @pytest.mark.asyncio
    async def test_query_knowledge_base_without_reranking(self, mock_bedrock_agent_runtime_client):
        """Test querying a knowledge base without reranking."""
        # Call the function with reranking disabled
        result = await query_knowledge_base(
            query='test query',
            knowledge_base_id='kb-12345',
            kb_agent_client=mock_bedrock_agent_runtime_client,
            reranking=False,
        )

        # Parse the result as JSON
        documents = [json.loads(doc) for doc in result.split('\n\n')]

        # Check that the result is correct
        assert len(documents) == 2

        # Check that the client methods were called correctly
        mock_bedrock_agent_runtime_client.retrieve.assert_called_once_with(
            knowledgeBaseId='kb-12345',
            retrievalQuery={'text': 'test query'},
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': 20,
                }
            },
        )

    @pytest.mark.asyncio
    async def test_query_knowledge_base_with_unsupported_region(
        self, mock_bedrock_agent_runtime_client
    ):
        """Test querying a knowledge base with an unsupported region for reranking."""
        # Modify the mock to use an unsupported region
        mock_bedrock_agent_runtime_client.meta.region_name = 'eu-west-1'

        # Call the function with reranking enabled
        with pytest.raises(ValueError) as excinfo:
            await query_knowledge_base(
                query='test query',
                knowledge_base_id='kb-12345',
                kb_agent_client=mock_bedrock_agent_runtime_client,
                reranking=True,
            )

        # Check that the error message is correct
        assert 'Reranking is not supported in region eu-west-1' in str(excinfo.value)

        # Check that the client methods were not called
        mock_bedrock_agent_runtime_client.retrieve.assert_not_called()

    @pytest.mark.asyncio
    async def test_query_knowledge_base_with_image_content(
        self, mock_bedrock_agent_runtime_client
    ):
        """Test querying a knowledge base that returns image content."""
        # Modify the mock to return image content
        mock_bedrock_agent_runtime_client.retrieve.return_value = {
            'retrievalResults': [
                {
                    'content': {'type': 'IMAGE', 'data': 'base64-encoded-image-data'},
                    'location': {'s3Location': {'uri': 's3://test-bucket/image.jpg'}},
                    'score': 0.95,
                },
                {
                    'content': {'text': 'This is a text document content.', 'type': 'TEXT'},
                    'location': {'s3Location': {'uri': 's3://test-bucket/document.txt'}},
                    'score': 0.85,
                },
            ]
        }

        # Call the function
        result = await query_knowledge_base(
            query='test query',
            knowledge_base_id='kb-12345',
            kb_agent_client=mock_bedrock_agent_runtime_client,
        )

        # Parse the result as JSON
        documents = [json.loads(doc) for doc in result.split('\n\n')]

        # Check that the result is correct - only the text document should be included
        assert len(documents) == 1
        assert documents[0]['content']['text'] == 'This is a text document content.'
        assert documents[0]['content']['type'] == 'TEXT'
        assert documents[0]['location']['s3Location']['uri'] == 's3://test-bucket/document.txt'
        assert documents[0]['score'] == 0.85
