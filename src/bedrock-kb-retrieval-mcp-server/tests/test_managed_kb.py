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
"""Tests for managed knowledge base retrieval."""

import pytest
from awslabs.bedrock_kb_retrieval_mcp_server.knowledgebases.kb_types import (
    MANAGED_DATA_SOURCE_ID_KEY,
    VECTOR_DATA_SOURCE_ID_KEY,
    clear_knowledge_base_type_cache,
    get_knowledge_base_type,
    is_managed_knowledge_base,
)
from awslabs.bedrock_kb_retrieval_mcp_server.knowledgebases.retrieval import query_knowledge_base
from unittest.mock import MagicMock


RESPONSE = {
    'retrievalResults': [
        {
            'content': {'text': 'managed result', 'type': 'TEXT'},
            'location': {'s3Location': {'uri': 's3://bucket/doc.pdf'}, 'type': 'S3'},
            'score': 0.9,
        }
    ]
}


def mgmt_client(kb_type):
    """Management client stub returning the given knowledge base type."""
    client = MagicMock()
    client.get_knowledge_base.return_value = {
        'knowledgeBase': {'knowledgeBaseConfiguration': {'type': kb_type}}
    }
    return client


def runtime_client(region='us-west-2'):
    """Runtime client stub."""
    client = MagicMock()
    client.meta.region_name = region
    client.retrieve.return_value = RESPONSE
    return client


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_knowledge_base_type_cache()
    yield
    clear_knowledge_base_type_cache()


class TestKnowledgeBaseTypeDetection:
    """Tests for knowledge base type detection."""

    def test_detects_managed(self):
        """Managed knowledge bases are detected as managed."""
        assert is_managed_knowledge_base('kb-1', mgmt_client('MANAGED')) is True

    def test_detects_vector(self):
        """Vector knowledge bases are not detected as managed."""
        assert is_managed_knowledge_base('kb-1', mgmt_client('VECTOR')) is False

    def test_unknown_without_client(self):
        """Type is unknown when no management client is supplied."""
        assert is_managed_knowledge_base('kb-1', None) is None

    def test_unknown_when_lookup_denied(self):
        """Type is unknown when the lookup call fails."""
        client = MagicMock()
        client.get_knowledge_base.side_effect = Exception('AccessDeniedException')
        assert is_managed_knowledge_base('kb-1', client) is None

    def test_result_is_cached(self):
        """The type lookup is performed only once per knowledge base."""
        client = mgmt_client('MANAGED')
        get_knowledge_base_type('kb-1', client)
        get_knowledge_base_type('kb-1', client)
        assert client.get_knowledge_base.call_count == 1


class TestManagedRetrieval:
    """Tests that managed knowledge bases get the managed configuration."""

    @pytest.mark.asyncio
    async def test_managed_kb_uses_managed_search_configuration(self):
        """Managed knowledge bases receive managedSearchConfiguration."""
        kb_client = runtime_client()
        await query_knowledge_base(
            query='q',
            knowledge_base_id='kb-1',
            kb_agent_client=kb_client,
            kb_agent_mgmt_client=mgmt_client('MANAGED'),
        )
        config = kb_client.retrieve.call_args[1]['retrievalConfiguration']
        assert 'managedSearchConfiguration' in config
        assert 'vectorSearchConfiguration' not in config

    @pytest.mark.asyncio
    async def test_vector_kb_still_uses_vector_search_configuration(self):
        """Vector knowledge bases keep vectorSearchConfiguration."""
        kb_client = runtime_client()
        await query_knowledge_base(
            query='q',
            knowledge_base_id='kb-1',
            kb_agent_client=kb_client,
            kb_agent_mgmt_client=mgmt_client('VECTOR'),
        )
        config = kb_client.retrieve.call_args[1]['retrievalConfiguration']
        assert 'vectorSearchConfiguration' in config
        assert 'managedSearchConfiguration' not in config

    @pytest.mark.asyncio
    async def test_managed_kb_filters_on_underscore_data_source_id(self):
        """Managed KBs expose data-source identity as ``_data_source_id``.

        Filtering on the vector key is accepted by the API but matches nothing, so
        this assertion guards against silently empty results.
        """
        kb_client = runtime_client()
        await query_knowledge_base(
            query='q',
            knowledge_base_id='kb-1',
            kb_agent_client=kb_client,
            data_source_ids=['ds-1'],
            kb_agent_mgmt_client=mgmt_client('MANAGED'),
        )
        config = kb_client.retrieve.call_args[1]['retrievalConfiguration']
        assert config['managedSearchConfiguration']['filter'] == {
            'in': {'key': MANAGED_DATA_SOURCE_ID_KEY, 'value': ['ds-1']}
        }

    @pytest.mark.asyncio
    async def test_vector_kb_filters_on_reserved_key(self):
        """Vector knowledge bases filter on the reserved data-source key."""
        kb_client = runtime_client()
        await query_knowledge_base(
            query='q',
            knowledge_base_id='kb-1',
            kb_agent_client=kb_client,
            data_source_ids=['ds-1'],
            kb_agent_mgmt_client=mgmt_client('VECTOR'),
        )
        config = kb_client.retrieve.call_args[1]['retrievalConfiguration']
        assert config['vectorSearchConfiguration']['filter'] == {
            'in': {'key': VECTOR_DATA_SOURCE_ID_KEY, 'value': ['ds-1']}
        }

    @pytest.mark.asyncio
    async def test_managed_kb_reranking_nested_under_managed_configuration(self):
        """Reranking is nested under the managed configuration."""
        kb_client = runtime_client()
        await query_knowledge_base(
            query='q',
            knowledge_base_id='kb-1',
            kb_agent_client=kb_client,
            reranking=True,
            kb_agent_mgmt_client=mgmt_client('MANAGED'),
        )
        config = kb_client.retrieve.call_args[1]['retrievalConfiguration']
        reranking = config['managedSearchConfiguration']['rerankingConfiguration']
        assert reranking['type'] == 'BEDROCK_RERANKING_MODEL'


class TestConfigurationMismatchFallback:
    """Tests recovery when the knowledge base type could not be determined."""

    @pytest.mark.asyncio
    async def test_retries_as_managed_when_vector_rejected(self):
        """Without a management client the vector shape is tried, then corrected."""

        class ValidationException(Exception):
            pass

        kb_client = runtime_client()
        kb_client.retrieve.side_effect = [
            ValidationException(
                'An error occurred (ValidationException) when calling the Retrieve '
                'operation: Incompatible configuration: vectorSearchConfiguration is '
                'not supported for managed knowledge bases. Use '
                'managedSearchConfiguration instead.'
            ),
            RESPONSE,
        ]

        result = await query_knowledge_base(
            query='q',
            knowledge_base_id='kb-1',
            kb_agent_client=kb_client,
            kb_agent_mgmt_client=None,
        )

        assert 'managed result' in result
        assert kb_client.retrieve.call_count == 2
        first = kb_client.retrieve.call_args_list[0][1]['retrievalConfiguration']
        second = kb_client.retrieve.call_args_list[1][1]['retrievalConfiguration']
        assert 'vectorSearchConfiguration' in first
        assert 'managedSearchConfiguration' in second

    @pytest.mark.asyncio
    async def test_unrelated_errors_are_not_retried(self):
        """Errors unrelated to configuration shape propagate unchanged."""
        kb_client = runtime_client()
        kb_client.retrieve.side_effect = Exception('ResourceNotFoundException')

        with pytest.raises(Exception, match='ResourceNotFoundException'):
            await query_knowledge_base(
                query='q',
                knowledge_base_id='kb-1',
                kb_agent_client=kb_client,
                kb_agent_mgmt_client=None,
            )
        assert kb_client.retrieve.call_count == 1

    @pytest.mark.asyncio
    async def test_no_retry_when_type_was_known(self):
        """A known type means a mismatch is a real error, not a bad guess."""
        kb_client = runtime_client()
        kb_client.retrieve.side_effect = Exception(
            'ValidationException: managedSearchConfiguration is not supported'
        )

        with pytest.raises(Exception, match='ValidationException'):
            await query_knowledge_base(
                query='q',
                knowledge_base_id='kb-1',
                kb_agent_client=kb_client,
                kb_agent_mgmt_client=mgmt_client('MANAGED'),
            )
        assert kb_client.retrieve.call_count == 1
