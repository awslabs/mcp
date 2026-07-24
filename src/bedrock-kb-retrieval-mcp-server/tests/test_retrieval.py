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

"""Tests for the runtime module of the bedrock-kb-retrieval-mcp-server."""

import json
import pytest
from awslabs.bedrock_kb_retrieval_mcp_server.knowledgebases.retrieval import query_knowledge_base


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
    async def test_query_knowledge_base_includes_metadata(self, mock_bedrock_agent_runtime_client):
        """Test that document metadata is included in the query results."""
        # Call the function
        result = await query_knowledge_base(
            query='test query',
            knowledge_base_id='kb-12345',
            kb_agent_client=mock_bedrock_agent_runtime_client,
        )

        # Parse the result as JSON
        documents = [json.loads(doc) for doc in result.split('\n\n')]

        # Check that the metadata is included in the results
        assert len(documents) == 2
        assert documents[0]['metadata'] == {
            'x-amz-bedrock-kb-source-uri': 's3://test-bucket/test-document.txt',
            'x-amz-bedrock-kb-data-source-id': 'ds-12345',
            'doc_type': 'runbook',
            'service': 'test-service',
        }
        assert documents[1]['metadata'] == {
            'x-amz-bedrock-kb-source-uri': 's3://test-bucket/another-document.txt',
            'x-amz-bedrock-kb-data-source-id': 'ds-67890',
            'doc_type': 'faq',
            'service': 'another-service',
        }

    @pytest.mark.asyncio
    async def test_query_knowledge_base_without_metadata_in_response(
        self, mock_bedrock_agent_runtime_client
    ):
        """Test that documents without metadata default to an empty metadata object."""
        # Modify the mock to return a result without a metadata field
        mock_bedrock_agent_runtime_client.retrieve.return_value = {
            'retrievalResults': [
                {
                    'content': {'text': 'This is a test document content.', 'type': 'TEXT'},
                    'location': {'s3Location': {'uri': 's3://test-bucket/test-document.txt'}},
                    'score': 0.95,
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

        # Check that the metadata defaults to an empty object
        assert len(documents) == 1
        assert documents[0]['metadata'] == {}

    @pytest.mark.asyncio
    async def test_query_knowledge_base_with_metadata_filter(
        self, mock_bedrock_agent_runtime_client
    ):
        """Test querying a knowledge base with a metadata filter only."""
        metadata_filter = {'equals': {'key': 'doc_type', 'value': 'runbook'}}

        # Call the function with a metadata filter
        result = await query_knowledge_base(
            query='test query',
            knowledge_base_id='kb-12345',
            kb_agent_client=mock_bedrock_agent_runtime_client,
            metadata_filter=metadata_filter,
        )

        # Parse the result as JSON
        documents = [json.loads(doc) for doc in result.split('\n\n')]

        # Check that the result is correct
        assert len(documents) == 2

        # Check that the filter is passed through unchanged (no andAll wrapper)
        mock_bedrock_agent_runtime_client.retrieve.assert_called_once_with(
            knowledgeBaseId='kb-12345',
            retrievalQuery={'text': 'test query'},
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': 20,
                    'filter': metadata_filter,
                }
            },
        )

    @pytest.mark.asyncio
    async def test_query_knowledge_base_with_data_source_ids_only(
        self, mock_bedrock_agent_runtime_client
    ):
        """Test that data source IDs alone produce a bare filter condition."""
        # Call the function with data source IDs only
        result = await query_knowledge_base(
            query='test query',
            knowledge_base_id='kb-12345',
            kb_agent_client=mock_bedrock_agent_runtime_client,
            data_source_ids=['ds-12345', 'ds-67890'],
        )

        # Parse the result as JSON
        documents = [json.loads(doc) for doc in result.split('\n\n')]

        # Check that the result is correct
        assert len(documents) == 2

        # Check that the single condition is not wrapped in andAll
        mock_bedrock_agent_runtime_client.retrieve.assert_called_once_with(
            knowledgeBaseId='kb-12345',
            retrievalQuery={'text': 'test query'},
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': 20,
                    'filter': {
                        'in': {
                            'key': 'x-amz-bedrock-kb-data-source-id',
                            'value': ['ds-12345', 'ds-67890'],
                        }
                    },
                }
            },
        )

    @pytest.mark.asyncio
    async def test_query_knowledge_base_with_data_source_ids_and_metadata_filter(
        self, mock_bedrock_agent_runtime_client
    ):
        """Test that a simple metadata filter and data source IDs are wrapped in a new andAll."""
        metadata_filter = {'equals': {'key': 'doc_type', 'value': 'runbook'}}

        # Call the function with both data source IDs and a metadata filter
        result = await query_knowledge_base(
            query='test query',
            knowledge_base_id='kb-12345',
            kb_agent_client=mock_bedrock_agent_runtime_client,
            data_source_ids=['ds-12345', 'ds-67890'],
            metadata_filter=metadata_filter,
        )

        # Parse the result as JSON
        documents = [json.loads(doc) for doc in result.split('\n\n')]

        # Check that the result is correct
        assert len(documents) == 2

        # Check that both filters are composed with andAll
        mock_bedrock_agent_runtime_client.retrieve.assert_called_once_with(
            knowledgeBaseId='kb-12345',
            retrievalQuery={'text': 'test query'},
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': 20,
                    'filter': {
                        'andAll': [
                            metadata_filter,
                            {
                                'in': {
                                    'key': 'x-amz-bedrock-kb-data-source-id',
                                    'value': ['ds-12345', 'ds-67890'],
                                }
                            },
                        ]
                    },
                }
            },
        )

    @pytest.mark.asyncio
    async def test_query_knowledge_base_merges_data_source_ids_into_existing_and_all(
        self, mock_bedrock_agent_runtime_client
    ):
        """Test that a top-level andAll filter has the data-source condition merged in."""
        metadata_filter = {
            'andAll': [
                {
                    'orAll': [
                        {'equals': {'key': 'doc_type', 'value': 'runbook'}},
                        {'equals': {'key': 'doc_type', 'value': 'faq'}},
                    ]
                },
                {'equals': {'key': 'service', 'value': 'test-service'}},
            ]
        }

        # Call the function with both data source IDs and an andAll metadata filter
        await query_knowledge_base(
            query='test query',
            knowledge_base_id='kb-12345',
            kb_agent_client=mock_bedrock_agent_runtime_client,
            data_source_ids=['ds-12345'],
            metadata_filter=metadata_filter,
        )

        # Check that the data-source condition is appended to the existing andAll list,
        # preserving the filter's embedding depth
        mock_bedrock_agent_runtime_client.retrieve.assert_called_once_with(
            knowledgeBaseId='kb-12345',
            retrievalQuery={'text': 'test query'},
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': 20,
                    'filter': {
                        'andAll': [
                            *metadata_filter['andAll'],
                            {
                                'in': {
                                    'key': 'x-amz-bedrock-kb-data-source-id',
                                    'value': ['ds-12345'],
                                }
                            },
                        ]
                    },
                }
            },
        )

    @pytest.mark.asyncio
    async def test_query_knowledge_base_wraps_flat_or_all_with_data_source_ids(
        self, mock_bedrock_agent_runtime_client
    ):
        """Test that a top-level orAll with flat members is wrapped in a new andAll."""
        metadata_filter = {
            'orAll': [
                {'equals': {'key': 'doc_type', 'value': 'runbook'}},
                {'equals': {'key': 'doc_type', 'value': 'faq'}},
            ]
        }

        # Call the function with both data source IDs and a flat orAll metadata filter
        await query_knowledge_base(
            query='test query',
            knowledge_base_id='kb-12345',
            kb_agent_client=mock_bedrock_agent_runtime_client,
            data_source_ids=['ds-12345'],
            metadata_filter=metadata_filter,
        )

        # Check that the orAll filter and the data-source condition are wrapped in andAll,
        # which adds exactly one embedding level (within the API limit)
        mock_bedrock_agent_runtime_client.retrieve.assert_called_once_with(
            knowledgeBaseId='kb-12345',
            retrievalQuery={'text': 'test query'},
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': 20,
                    'filter': {
                        'andAll': [
                            metadata_filter,
                            {
                                'in': {
                                    'key': 'x-amz-bedrock-kb-data-source-id',
                                    'value': ['ds-12345'],
                                }
                            },
                        ]
                    },
                }
            },
        )

    @pytest.mark.asyncio
    async def test_query_knowledge_base_rejects_nested_or_all_with_data_source_ids(
        self, mock_bedrock_agent_runtime_client
    ):
        """Test that an orAll with embedded groups plus data source IDs raises ValueError."""
        metadata_filter = {
            'orAll': [
                {
                    'andAll': [
                        {'equals': {'key': 'doc_type', 'value': 'runbook'}},
                        {'equals': {'key': 'service', 'value': 'test-service'}},
                    ]
                },
                {'equals': {'key': 'doc_type', 'value': 'faq'}},
            ]
        }

        # Call the function with both data source IDs and a nested orAll metadata filter
        with pytest.raises(ValueError) as excinfo:
            await query_knowledge_base(
                query='test query',
                knowledge_base_id='kb-12345',
                kb_agent_client=mock_bedrock_agent_runtime_client,
                data_source_ids=['ds-12345'],
                metadata_filter=metadata_filter,
            )

        # Check that the error message is actionable
        assert 'Cannot combine data_source_ids with this metadata_filter' in str(excinfo.value)
        assert 'x-amz-bedrock-kb-data-source-id' in str(excinfo.value)

        # Check that the client methods were not called
        mock_bedrock_agent_runtime_client.retrieve.assert_not_called()

    @pytest.mark.asyncio
    async def test_query_knowledge_base_rejects_empty_metadata_filter(
        self, mock_bedrock_agent_runtime_client
    ):
        """Test that an empty metadata filter raises ValueError instead of failing silently."""
        # Call the function with an empty metadata filter
        with pytest.raises(ValueError) as excinfo:
            await query_knowledge_base(
                query='test query',
                knowledge_base_id='kb-12345',
                kb_agent_client=mock_bedrock_agent_runtime_client,
                metadata_filter={},
            )

        # Check that the error message is actionable
        assert 'metadata_filter must not be empty' in str(excinfo.value)

        # Check that the client methods were not called
        mock_bedrock_agent_runtime_client.retrieve.assert_not_called()

    @pytest.mark.asyncio
    async def test_query_knowledge_base_merges_empty_and_all_to_bare_condition(
        self, mock_bedrock_agent_runtime_client
    ):
        """Test that a vacuous andAll filter plus data source IDs emits a bare condition."""
        # Call the function with an empty andAll list and data source IDs
        await query_knowledge_base(
            query='test query',
            knowledge_base_id='kb-12345',
            kb_agent_client=mock_bedrock_agent_runtime_client,
            data_source_ids=['ds-12345'],
            metadata_filter={'andAll': []},
        )

        # Check that the single merged member is emitted bare, since the API
        # requires andAll to have at least 2 members
        mock_bedrock_agent_runtime_client.retrieve.assert_called_once_with(
            knowledgeBaseId='kb-12345',
            retrievalQuery={'text': 'test query'},
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': 20,
                    'filter': {
                        'in': {
                            'key': 'x-amz-bedrock-kb-data-source-id',
                            'value': ['ds-12345'],
                        }
                    },
                }
            },
        )

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
