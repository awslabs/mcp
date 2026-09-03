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
import asyncio
import json
from loguru import logger
from typing import TYPE_CHECKING, Any, Literal


if TYPE_CHECKING:
    from mypy_boto3_bedrock_agent.client import AgentsforBedrockClient
    from mypy_boto3_bedrock_agent_runtime.client import AgentsforBedrockRuntimeClient
else:
    AgentsforBedrockClient = object
    AgentsforBedrockRuntimeClient = object


# Model ID for each reranking model name this server accepts.
RERANKING_MODEL_NAME_MAPPING = {
    'COHERE': 'cohere.rerank-v3-5:0',
    'AMAZON': 'amazon.rerank-v1:0',
}

# Regions each reranking model is actually offered in. Not every model is available in every
# region a knowledge base can live in - e.g. Amazon's reranking model is not offered in
# us-east-1, even though that region otherwise supports Bedrock reranking.
RERANKING_MODEL_SUPPORTED_REGIONS = {
    'COHERE': {'us-west-2', 'us-east-1', 'ap-northeast-1', 'ca-central-1', 'eu-central-1'},
    'AMAZON': {'us-west-2', 'ap-northeast-1', 'ca-central-1', 'eu-central-1'},
}

# Cache of knowledge_base_id -> is-Managed-Knowledge-Base, since GetKnowledgeBase is an extra
# network round-trip on every query and a KB's type never changes for the lifetime of the KB.
_managed_kb_cache: dict[str, bool] = {}


def _is_managed_knowledge_base(
    kb_agent_mgmt_client: AgentsforBedrockClient, knowledge_base_id: str
) -> bool:
    """Determine whether a knowledge base is an Amazon Bedrock Managed Knowledge Base.

    Managed Knowledge Bases (AgentCore's native-connector KB type, e.g. backed by Confluence,
    SharePoint, Salesforce, etc.) use a different `Retrieve` request shape
    (`managedSearchConfiguration`) than a self-managed knowledge base with a customer-owned
    vector store (`vectorSearchConfiguration`) - the two are not interchangeable, and Bedrock
    rejects the wrong one with a `ValidationException`.

    Synchronous (this is a blocking boto3 call) - callers running in an event loop should run
    it via `asyncio.to_thread`. Result is cached per `knowledge_base_id`.
    """
    if knowledge_base_id in _managed_kb_cache:
        return _managed_kb_cache[knowledge_base_id]

    kb = kb_agent_mgmt_client.get_knowledge_base(knowledgeBaseId=knowledge_base_id)[
        'knowledgeBase'
    ]
    is_managed = kb.get('knowledgeBaseConfiguration', {}).get('type') == 'MANAGED'
    _managed_kb_cache[knowledge_base_id] = is_managed
    return is_managed


async def query_knowledge_base(
    query: str,
    knowledge_base_id: str,
    kb_agent_client: AgentsforBedrockRuntimeClient,
    kb_agent_mgmt_client: AgentsforBedrockClient,
    number_of_results: int = 20,
    reranking: bool = False,
    reranking_model_name: Literal['COHERE', 'AMAZON'] = 'COHERE',
    data_source_ids: list[str] | None = None,
) -> str:
    """# Amazon Bedrock Knowledge Base query tool.

    Args:
        query (str): The query to search the knowledge base with.
        knowledge_base_id (str): The knowledge base ID to query.
        kb_agent_client (AgentsforBedrockRuntimeClient): The Bedrock agent runtime client.
        kb_agent_mgmt_client (AgentsforBedrockClient): The Bedrock agent management client, used to detect whether the knowledge base is a Managed Knowledge Base.
        number_of_results (int): The number of results to return.
        reranking (bool): Whether to rerank the results. Can be globally configured using the BEDROCK_KB_RERANKING_ENABLED environment variable.
        reranking_model_name (Literal['COHERE', 'AMAZON']): The name of the reranking model to use. Not every reranking model is available in every region - if this fails, try 'COHERE'.
        data_source_ids (list[str] | None): The data source IDs to filter the knowledge base by.

    ## Warning: You must use the `ListKnowledgeBases` tool to get the knowledge base ID and optionally a data source ID first.

    ## Returns:
    - A string containing the results of the query.
    """
    if reranking:
        region = kb_agent_client.meta.region_name
        if region not in RERANKING_MODEL_SUPPORTED_REGIONS[reranking_model_name]:
            raise ValueError(
                f"The '{reranking_model_name}' reranking model is not available in region "
                f'{region}. Supported regions: '
                f'{sorted(RERANKING_MODEL_SUPPORTED_REGIONS[reranking_model_name])}'
            )

    is_managed_kb = await asyncio.to_thread(
        _is_managed_knowledge_base, kb_agent_mgmt_client, knowledge_base_id
    )
    search_configuration_key = (
        'managedSearchConfiguration' if is_managed_kb else 'vectorSearchConfiguration'
    )

    retrieve_request: dict[str, Any] = {
        search_configuration_key: {
            'numberOfResults': number_of_results,
        }
    }

    if data_source_ids:
        retrieve_request[search_configuration_key]['filter'] = {
            'in': {
                'key': 'x-amz-bedrock-kb-data-source-id',
                'value': data_source_ids,
            }
        }

    if reranking:
        retrieve_request[search_configuration_key]['rerankingConfiguration'] = {
            'type': 'BEDROCK_RERANKING_MODEL',
            'bedrockRerankingConfiguration': {
                'modelConfiguration': {
                    'modelArn': f'arn:aws:bedrock:{kb_agent_client.meta.region_name}::foundation-model/{RERANKING_MODEL_NAME_MAPPING[reranking_model_name]}'
                },
            },
        }

    response = kb_agent_client.retrieve(
        knowledgeBaseId=knowledge_base_id,
        retrievalQuery={'text': query},
        retrievalConfiguration=retrieve_request,
    )
    results = response['retrievalResults']
    documents: list[dict] = []
    for result in results:
        if result['content'].get('type') == 'IMAGE':
            logger.warning('Images are not supported at this time. Skipping...')
            continue
        else:
            documents.append(
                {
                    'content': result['content'],
                    'location': result.get('location', ''),
                    'score': result.get('score', ''),
                }
            )

    return '\n\n'.join([json.dumps(document) for document in documents])
