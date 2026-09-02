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
"""Agentic retrieval against Amazon Bedrock Managed Knowledge Bases.

``AgenticRetrieveStream`` plans a retrieval strategy, issues one or more searches
across the knowledge bases it is given, and optionally synthesises a cited answer.
It is a **streaming** operation, whereas an MCP tool call returns a single result, so
this module consumes the whole event stream and returns one aggregated payload.

Stream shape (observed against a live managed knowledge base):

* ``traceEvent``    -- a handful of step/status transitions (Planning, Retrieval, ...)
* ``responseEvent`` -- the answer, streamed in many small text chunks (~440 for a
  3 KB answer). Only emitted when ``generateResponse`` is true.
* ``result``        -- a single terminal event carrying the retrieved items and, when
  requested, the complete ``generatedResponse`` (answer plus citations).

Because the terminal ``result`` event already contains the whole answer, the streamed
chunks are only used as a fallback. Forwarding raw events to the model is deliberately
not offered: a single default call emits hundreds of them, which would crowd out the
content the model actually needs.
"""

import json
from .kb_types import is_managed_knowledge_base
from loguru import logger
from typing import TYPE_CHECKING, Any, Optional


if TYPE_CHECKING:
    from mypy_boto3_bedrock_agent.client import AgentsforBedrockClient
    from mypy_boto3_bedrock_agent_runtime.client import AgentsforBedrockRuntimeClient
else:
    AgentsforBedrockClient = object
    AgentsforBedrockRuntimeClient = object


# Managed knowledge bases expose data-source identity under this key. Agentic
# retrieval only supports managed knowledge bases, so the vector reserved key
# (``x-amz-bedrock-kb-data-source-id``) never applies here.
MANAGED_DATA_SOURCE_ID_KEY = '_data_source_id'

# Stream members that carry a modelled service error rather than content.
_ERROR_EVENT_KEYS = (
    'internalServerException',
    'validationException',
    'resourceNotFoundException',
    'serviceQuotaExceededException',
    'throttlingException',
    'accessDeniedException',
    'conflictException',
    'dependencyFailedException',
    'badGatewayException',
)


class AgenticRetrievalError(Exception):
    """An error reported inside the agentic retrieval event stream."""


def _result_item(item: dict, index: int) -> dict:
    """Flatten one result item into something compact and JSON-safe."""
    content = item.get('content', {}) or {}
    flattened: dict[str, Any] = {
        'index': index,
        'text': content.get('text', ''),
        'mimeType': content.get('mimeType', ''),
        'metadata': item.get('metadata', {}) or {},
        'knowledgeBaseId': (item.get('sourceRetriever', {}) or {}).get('identifier', ''),
    }
    # byteContent is a Blob and is not JSON serialisable. Flag its presence rather
    # than dropping it silently, and never attempt to embed it.
    if content.get('byteContent') is not None:
        flattened['binaryContentOmitted'] = True
    return flattened


def _citation(citation: dict) -> dict:
    """Flatten a citation, resolving references down to result indexes."""
    return {
        'startIndex': citation.get('startIndex'),
        'endIndex': citation.get('endIndex'),
        'resultIndexes': [
            reference.get('resultIndex') for reference in citation.get('references', []) or []
        ],
    }


def _build_retrievers(
    knowledge_base_ids: list[str],
    data_source_ids: Optional[list[str]],
    number_of_results: Optional[int],
) -> list[dict]:
    """Build the ``retrievers`` list, applying retrieval overrides when asked for."""
    overrides: dict[str, Any] = {}
    if number_of_results is not None:
        overrides['maxNumberOfResults'] = number_of_results
    if data_source_ids:
        overrides['filter'] = {'in': {'key': MANAGED_DATA_SOURCE_ID_KEY, 'value': data_source_ids}}

    retrievers = []
    for knowledge_base_id in knowledge_base_ids:
        knowledge_base: dict[str, Any] = {'knowledgeBaseId': knowledge_base_id}
        if overrides:
            knowledge_base['retrievalOverrides'] = overrides
        retrievers.append({'configuration': {'knowledgeBase': knowledge_base}})
    return retrievers


def _raise_if_error_event(event: dict) -> None:
    """Convert a modelled error event into an exception."""
    for key in _ERROR_EVENT_KEYS:
        if key in event:
            message = (event[key] or {}).get('message', '')
            raise AgenticRetrievalError(f'{key}: {message}')


async def agentic_retrieve_knowledge_bases(
    query: str,
    knowledge_base_ids: list[str],
    kb_agent_client: AgentsforBedrockRuntimeClient,
    kb_agent_mgmt_client: Optional[AgentsforBedrockClient] = None,
    generate_response: bool = True,
    number_of_results: Optional[int] = None,
    data_source_ids: Optional[list[str]] = None,
    max_agent_iterations: Optional[int] = None,
    include_trace: bool = False,
) -> str:
    """Run agentic retrieval across one or more managed knowledge bases.

    Args:
        query: The natural language question.
        knowledge_base_ids: Managed knowledge bases to search. More than one may be
            given; the agent decides which to search and may search several.
        kb_agent_client: The Bedrock agent runtime client.
        kb_agent_mgmt_client: Management client, used to reject non-managed knowledge
            bases up front with a clear message. Optional -- when omitted the service
            still rejects them, just less legibly.
        generate_response: Whether to synthesise a cited answer from the results.
        number_of_results: Maximum results per retriever.
        data_source_ids: Restrict retrieval to these data sources.
        max_agent_iterations: Cap on agent planning iterations (minimum 2).
        include_trace: Include a condensed per-step trace of the agent's work.

    Returns:
        A JSON object as a string, with ``results`` always present and ``answer`` /
        ``citations`` present when ``generate_response`` is true.
    """
    if not knowledge_base_ids:
        raise ValueError('At least one knowledge base ID is required.')

    # Agentic retrieval is only supported for managed knowledge bases. Checking up
    # front turns an opaque service ValidationException into an actionable message.
    for knowledge_base_id in knowledge_base_ids:
        managed = is_managed_knowledge_base(knowledge_base_id, kb_agent_mgmt_client)
        if managed is False:
            raise ValueError(
                f'Knowledge base {knowledge_base_id} is not a managed knowledge base. '
                'Agentic retrieval supports managed knowledge bases only -- use the '
                'QueryKnowledgeBases tool for vector knowledge bases.'
            )

    agentic_configuration: dict[str, Any] = {}
    if max_agent_iterations is not None:
        agentic_configuration['maxAgentIteration'] = max_agent_iterations

    request: dict[str, Any] = {
        'messages': [{'role': 'user', 'content': {'text': query}}],
        'retrievers': _build_retrievers(knowledge_base_ids, data_source_ids, number_of_results),
        'agenticRetrieveConfiguration': agentic_configuration,
        'generateResponse': generate_response,
    }

    response = kb_agent_client.agentic_retrieve_stream(**request)

    results: list[dict] = []
    citations: list[dict] = []
    answer = ''
    streamed_chunks: list[str] = []
    trace: list[dict] = []
    warnings: list[str] = []
    failures: list[str] = []
    next_token = None

    for event in response['stream']:
        _raise_if_error_event(event)

        if 'result' in event:
            result_event = event['result']
            for item in result_event.get('results', []) or []:
                results.append(_result_item(item, len(results)))
            generated = result_event.get('generatedResponse') or {}
            if generated.get('answer'):
                answer = generated['answer']
            citations = [_citation(c) for c in generated.get('citations', []) or []]
            next_token = result_event.get('nextToken') or next_token

        elif 'responseEvent' in event:
            # Streamed answer chunks. The terminal result event normally carries the
            # complete answer, so these are only a fallback.
            streamed_chunks.append(event['responseEvent'].get('text', ''))

        elif 'traceEvent' in event:
            attributes = event['traceEvent'].get('attributes', {}) or {}
            for warning in attributes.get('warnings', []) or []:
                message = (warning.get('message') or {}).get('message')
                guardrail = warning.get('guardrail') or {}
                warnings.append(message or guardrail.get('message') or json.dumps(warning))
            for failure in attributes.get('failures', []) or []:
                failures.append(failure.get('message', ''))
            if include_trace:
                trace.append(
                    {
                        'step': attributes.get('step'),
                        'status': attributes.get('status'),
                        'message': attributes.get('message'),
                    }
                )

    if not answer and streamed_chunks:
        answer = ''.join(streamed_chunks)

    payload: dict[str, Any] = {'knowledgeBaseIds': knowledge_base_ids, 'results': results}
    if generate_response:
        payload['answer'] = answer
        payload['citations'] = citations
    if include_trace:
        payload['trace'] = trace
    if warnings:
        payload['warnings'] = warnings
    if failures:
        payload['failures'] = failures
    if next_token:
        payload['nextToken'] = next_token

    if not results:
        logger.info(
            f'Agentic retrieval returned no results for knowledge bases {knowledge_base_ids}'
        )

    return json.dumps(payload)
