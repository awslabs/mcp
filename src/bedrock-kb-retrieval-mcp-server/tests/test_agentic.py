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
"""Tests for agentic retrieval."""

import json
import pytest
from awslabs.bedrock_kb_retrieval_mcp_server.knowledgebases.agentic import (
    MANAGED_DATA_SOURCE_ID_KEY,
    AgenticRetrievalError,
    agentic_retrieve_knowledge_bases,
)
from awslabs.bedrock_kb_retrieval_mcp_server.knowledgebases.kb_types import (
    clear_knowledge_base_type_cache,
)
from unittest.mock import MagicMock


def result_event(count=2, answer='The answer.', citations=True):
    """Build a terminal result event with `count` results."""
    event = {
        'result': {
            'results': [
                {
                    'content': {'text': f'passage {i}', 'mimeType': 'text/plain'},
                    'metadata': {MANAGED_DATA_SOURCE_ID_KEY: f'ds-{i}'},
                    'sourceRetriever': {'identifier': 'kb-managed-1'},
                }
                for i in range(count)
            ]
        }
    }
    if answer is not None:
        generated = {'answer': answer}
        if citations:
            generated['citations'] = [
                {'startIndex': 0, 'endIndex': 10, 'references': [{'resultIndex': 0}]}
            ]
        event['result']['generatedResponse'] = generated
    return event


def trace_event(step='Planning', status='SUCCEEDED', message='done', **extra):
    """Build a trace event."""
    return {
        'traceEvent': {'attributes': {'step': step, 'status': status, 'message': message, **extra}}
    }


def runtime_client(stream):
    """Runtime client stub returning the given stream."""
    client = MagicMock()
    client.meta.region_name = 'us-west-2'
    client.agentic_retrieve_stream.return_value = {'stream': stream}
    return client


def mgmt_client(kb_type='MANAGED'):
    """Management client stub returning the given knowledge base type."""
    client = MagicMock()
    client.get_knowledge_base.return_value = {
        'knowledgeBase': {'knowledgeBaseConfiguration': {'type': kb_type}}
    }
    return client


@pytest.fixture(autouse=True)
def _clear_cache():
    """Clear the knowledge base type cache around each test."""
    clear_knowledge_base_type_cache()
    yield
    clear_knowledge_base_type_cache()


class TestAgenticRetrieval:
    """Tests for aggregating the agentic retrieval stream."""

    @pytest.mark.asyncio
    async def test_aggregates_results_answer_and_citations(self):
        """Results, answer and citations are all surfaced."""
        client = runtime_client([trace_event(), result_event()])
        payload = json.loads(
            await agentic_retrieve_knowledge_bases(
                query='q',
                knowledge_base_ids=['kb-managed-1'],
                kb_agent_client=client,
                kb_agent_mgmt_client=mgmt_client(),
            )
        )
        assert payload['answer'] == 'The answer.'
        assert len(payload['results']) == 2
        assert payload['citations'] == [{'startIndex': 0, 'endIndex': 10, 'resultIndexes': [0]}]
        assert payload['results'][0]['index'] == 0
        assert payload['results'][0]['text'] == 'passage 0'
        assert payload['results'][0]['knowledgeBaseId'] == 'kb-managed-1'

    @pytest.mark.asyncio
    async def test_generate_response_false_omits_answer(self):
        """With generation off, answer and citations keys are absent."""
        client = runtime_client([result_event(answer=None)])
        payload = json.loads(
            await agentic_retrieve_knowledge_bases(
                query='q',
                knowledge_base_ids=['kb-managed-1'],
                kb_agent_client=client,
                kb_agent_mgmt_client=mgmt_client(),
                generate_response=False,
            )
        )
        assert 'answer' not in payload
        assert 'citations' not in payload
        assert len(payload['results']) == 2

    @pytest.mark.asyncio
    async def test_falls_back_to_streamed_chunks_when_no_generated_answer(self):
        """Streamed responseEvent chunks are joined if the result carries no answer."""
        stream = [
            {'responseEvent': {'text': 'Hello '}},
            {'responseEvent': {'text': 'world'}},
            result_event(answer=None),
        ]
        payload = json.loads(
            await agentic_retrieve_knowledge_bases(
                query='q',
                knowledge_base_ids=['kb-managed-1'],
                kb_agent_client=runtime_client(stream),
                kb_agent_mgmt_client=mgmt_client(),
            )
        )
        assert payload['answer'] == 'Hello world'

    @pytest.mark.asyncio
    async def test_trace_only_included_when_requested(self):
        """The condensed trace is opt-in."""
        stream = [trace_event(step='Retrieval', status='SUCCEEDED'), result_event()]

        without = json.loads(
            await agentic_retrieve_knowledge_bases(
                query='q',
                knowledge_base_ids=['kb-managed-1'],
                kb_agent_client=runtime_client(stream),
                kb_agent_mgmt_client=mgmt_client(),
            )
        )
        assert 'trace' not in without

        with_trace = json.loads(
            await agentic_retrieve_knowledge_bases(
                query='q',
                knowledge_base_ids=['kb-managed-1'],
                kb_agent_client=runtime_client(stream),
                kb_agent_mgmt_client=mgmt_client(),
                include_trace=True,
            )
        )
        assert with_trace['trace'] == [
            {'step': 'Retrieval', 'status': 'SUCCEEDED', 'message': 'done'}
        ]

    @pytest.mark.asyncio
    async def test_data_source_filter_uses_managed_key(self):
        """Data-source filtering uses the managed metadata key, via retrievalOverrides."""
        client = runtime_client([result_event()])
        await agentic_retrieve_knowledge_bases(
            query='q',
            knowledge_base_ids=['kb-managed-1'],
            kb_agent_client=client,
            kb_agent_mgmt_client=mgmt_client(),
            data_source_ids=['ds-1'],
            number_of_results=5,
        )
        request = client.agentic_retrieve_stream.call_args[1]
        overrides = request['retrievers'][0]['configuration']['knowledgeBase'][
            'retrievalOverrides'
        ]
        assert overrides['maxNumberOfResults'] == 5
        assert overrides['filter'] == {
            'in': {'key': MANAGED_DATA_SOURCE_ID_KEY, 'value': ['ds-1']}
        }

    @pytest.mark.asyncio
    async def test_multiple_knowledge_bases_become_multiple_retrievers(self):
        """Each knowledge base id becomes its own retriever."""
        client = runtime_client([result_event()])
        await agentic_retrieve_knowledge_bases(
            query='q',
            knowledge_base_ids=['kb-managed-1', 'kb-managed-2'],
            kb_agent_client=client,
            kb_agent_mgmt_client=mgmt_client(),
        )
        retrievers = client.agentic_retrieve_stream.call_args[1]['retrievers']
        assert [r['configuration']['knowledgeBase']['knowledgeBaseId'] for r in retrievers] == [
            'kb-managed-1',
            'kb-managed-2',
        ]

    @pytest.mark.asyncio
    async def test_max_agent_iterations_passed_through(self):
        """The agent iteration cap is forwarded when supplied."""
        client = runtime_client([result_event()])
        await agentic_retrieve_knowledge_bases(
            query='q',
            knowledge_base_ids=['kb-managed-1'],
            kb_agent_client=client,
            kb_agent_mgmt_client=mgmt_client(),
            max_agent_iterations=3,
        )
        config = client.agentic_retrieve_stream.call_args[1]['agenticRetrieveConfiguration']
        assert config['maxAgentIteration'] == 3

    @pytest.mark.asyncio
    async def test_warnings_and_failures_surfaced(self):
        """Trace warnings and failures are collected even without include_trace."""
        stream = [
            trace_event(
                warnings=[{'message': {'message': 'a warning'}}],
                failures=[{'message': 'a failure'}],
            ),
            result_event(),
        ]
        payload = json.loads(
            await agentic_retrieve_knowledge_bases(
                query='q',
                knowledge_base_ids=['kb-managed-1'],
                kb_agent_client=runtime_client(stream),
                kb_agent_mgmt_client=mgmt_client(),
            )
        )
        assert payload['warnings'] == ['a warning']
        assert payload['failures'] == ['a failure']


class TestAgenticGuards:
    """Tests for input validation and error handling."""

    @pytest.mark.asyncio
    async def test_rejects_vector_knowledge_base(self):
        """A non-managed knowledge base is rejected with an actionable message."""
        with pytest.raises(ValueError, match='not a managed knowledge base'):
            await agentic_retrieve_knowledge_bases(
                query='q',
                knowledge_base_ids=['kb-vector-1'],
                kb_agent_client=runtime_client([result_event()]),
                kb_agent_mgmt_client=mgmt_client('VECTOR'),
            )

    @pytest.mark.asyncio
    async def test_proceeds_when_type_unknown(self):
        """An unknown type does not block the call; the service still validates."""
        payload = json.loads(
            await agentic_retrieve_knowledge_bases(
                query='q',
                knowledge_base_ids=['kb-managed-1'],
                kb_agent_client=runtime_client([result_event()]),
                kb_agent_mgmt_client=None,
            )
        )
        assert len(payload['results']) == 2

    @pytest.mark.asyncio
    async def test_requires_at_least_one_knowledge_base(self):
        """An empty knowledge base list is rejected."""
        with pytest.raises(ValueError, match='At least one knowledge base'):
            await agentic_retrieve_knowledge_bases(
                query='q',
                knowledge_base_ids=[],
                kb_agent_client=runtime_client([]),
                kb_agent_mgmt_client=mgmt_client(),
            )

    @pytest.mark.asyncio
    async def test_error_event_in_stream_raises(self):
        """A modelled error event in the stream is raised, not silently dropped."""
        stream = [{'validationException': {'message': 'bad input'}}]
        with pytest.raises(AgenticRetrievalError, match='validationException: bad input'):
            await agentic_retrieve_knowledge_bases(
                query='q',
                knowledge_base_ids=['kb-managed-1'],
                kb_agent_client=runtime_client(stream),
                kb_agent_mgmt_client=mgmt_client(),
            )

    @pytest.mark.asyncio
    async def test_binary_content_flagged_not_embedded(self):
        """Binary content is flagged rather than embedded, since Blobs are not JSON safe."""
        stream = [
            {
                'result': {
                    'results': [
                        {
                            'content': {
                                'text': 'caption',
                                'mimeType': 'image/png',
                                'byteContent': b'\x89PNG',
                            },
                            'sourceRetriever': {'identifier': 'kb-managed-1'},
                        }
                    ]
                }
            }
        ]
        payload = json.loads(
            await agentic_retrieve_knowledge_bases(
                query='q',
                knowledge_base_ids=['kb-managed-1'],
                kb_agent_client=runtime_client(stream),
                kb_agent_mgmt_client=mgmt_client(),
                generate_response=False,
            )
        )
        assert payload['results'][0]['binaryContentOmitted'] is True
        assert 'byteContent' not in payload['results'][0]


class TestAgenticUserContext:
    """Tests for end-user identity propagation in agentic retrieval."""

    @pytest.mark.asyncio
    async def test_user_id_sent_as_user_context(self):
        """A user id is sent as userContext so ACL-aware data sources are reachable."""
        client = runtime_client([result_event()])
        await agentic_retrieve_knowledge_bases(
            query='q',
            knowledge_base_ids=['kb-managed-1'],
            kb_agent_client=client,
            kb_agent_mgmt_client=mgmt_client(),
            user_id='user@example.com',
        )
        request = client.agentic_retrieve_stream.call_args[1]
        assert request['userContext'] == {'userId': 'user@example.com'}

    @pytest.mark.asyncio
    async def test_user_context_omitted_when_no_user_id(self):
        """No userContext key is sent when no user id is supplied."""
        client = runtime_client([result_event()])
        await agentic_retrieve_knowledge_bases(
            query='q',
            knowledge_base_ids=['kb-managed-1'],
            kb_agent_client=client,
            kb_agent_mgmt_client=mgmt_client(),
        )
        assert 'userContext' not in client.agentic_retrieve_stream.call_args[1]

    @pytest.mark.asyncio
    async def test_next_token_forwarded_for_pagination(self):
        """A continuation token is forwarded so a surfaced nextToken is usable."""
        client = runtime_client([result_event()])
        await agentic_retrieve_knowledge_bases(
            query='q',
            knowledge_base_ids=['kb-managed-1'],
            kb_agent_client=client,
            kb_agent_mgmt_client=mgmt_client(),
            next_token='tok-abc',
        )
        assert client.agentic_retrieve_stream.call_args[1]['nextToken'] == 'tok-abc'

    @pytest.mark.asyncio
    async def test_next_token_omitted_when_absent(self):
        """No nextToken key is sent when none is supplied."""
        client = runtime_client([result_event()])
        await agentic_retrieve_knowledge_bases(
            query='q',
            knowledge_base_ids=['kb-managed-1'],
            kb_agent_client=client,
            kb_agent_mgmt_client=mgmt_client(),
        )
        assert 'nextToken' not in client.agentic_retrieve_stream.call_args[1]
