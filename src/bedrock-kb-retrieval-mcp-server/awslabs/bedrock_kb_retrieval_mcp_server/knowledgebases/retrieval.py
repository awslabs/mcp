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
import json
from loguru import logger
from typing import TYPE_CHECKING, Literal


if TYPE_CHECKING:
    from mypy_boto3_bedrock_agent.client import AgentsforBedrockClient
    from mypy_boto3_bedrock_agent_runtime.client import AgentsforBedrockRuntimeClient
    from mypy_boto3_bedrock_agent_runtime.type_defs import (
        KnowledgeBaseRetrievalConfigurationTypeDef,
    )
else:
    AgentsforBedrockClient = object
    AgentsforBedrockRuntimeClient = object
    KnowledgeBaseRetrievalConfigurationTypeDef = object


# Reranking models available per AWS region. Amazon's reranking model is not offered in every
# region a knowledge base can live in (e.g. not in us-east-1), unlike Cohere's.
RERANKING_MODEL_NAME_MAPPING = {
    'COHERE': 'cohere.rerank-v3-5:0',
    'AMAZON': 'amazon.rerank-v1:0',
}


async def _is_managed_knowledge_base(
    kb_agent_mgmt_client: AgentsforBedrockClient, knowledge_base_id: str
) -> bool:
    """Determine whether a knowledge base is an Amazon Bedrock Managed Knowledge Base.

    Managed Knowledge Bases (AgentCore's native-connector KB type, e.g. backed by Confluence,
    SharePoint, Salesforce, etc.) use a different `Retrieve` request shape
    (`managedSearchConfiguration`) than a self-managed knowledge base with a customer-owned
    vector store (`vectorSearchConfiguration`) - the two are not interchangeable, and Bedrock
    rejects the wrong one with a `ValidationException`.
    """
    kb = kb_agent_mgmt_client.get_knowledge_base(knowledgeBaseId=knowledge_base_id)[
        'knowledgeBase'
    ]
    return kb.get('knowledgeBaseConfiguration', {}).get('type') == 'MANAGED'


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
    if reranking and kb_agent_client.meta.region_name not in [
        'us-west-2',
        'us-east-1',
        'ap-northeast-1',
        'ca-central-1',
        'eu-central-1',
    ]:
        raise ValueError(
            f'Reranking is not supported in region {kb_agent_client.meta.region_name}'
        )

    is_managed_kb = await _is_managed_knowledge_base(kb_agent_mgmt_client, knowledge_base_id)
    search_configuration_key = (
        'managedSearchConfiguration' if is_managed_kb else 'vectorSearchConfiguration'
    )

    retrieve_request: KnowledgeBaseRetrievalConfigurationTypeDef = {
        search_configuration_key: {
            'numberOfResults': number_of_results,
        }
    }

    if data_source_ids:
        retrieve_request[search_configuration_key]['filter'] = {  # type: ignore
            'in': {
                'key': 'x-amz-bedrock-kb-data-source-id',
                'value': data_source_ids,  # type: ignore
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
