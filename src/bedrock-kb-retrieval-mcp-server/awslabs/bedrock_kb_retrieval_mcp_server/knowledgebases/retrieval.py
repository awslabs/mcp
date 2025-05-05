# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
import json
from loguru import logger
from typing import TYPE_CHECKING, Literal


if TYPE_CHECKING:
    from mypy_boto3_bedrock_agent_runtime.client import AgentsforBedrockRuntimeClient
    from mypy_boto3_bedrock_agent_runtime.type_defs import (
        KnowledgeBaseRetrievalConfigurationTypeDef,
    )
else:
    AgentsforBedrockRuntimeClient = object
    KnowledgeBaseRetrievalConfigurationTypeDef = object


async def query_knowledge_base(
    query: str,
    knowledge_base_id: str,
    kb_agent_client: AgentsforBedrockRuntimeClient,
    number_of_results: int = 20,
    reranking: bool = False,
    reranking_model_name: Literal['COHERE', 'AMAZON'] = 'AMAZON',
    data_source_ids: list[str] | None = None,
) -> str:
    """# Amazon Bedrock Knowledge Base query tool.

    Args:
        query (str): The query to search the knowledge base with.
        knowledge_base_id (str): The knowledge base ID to query.
        kb_agent_client (AgentsforBedrockRuntimeClient): The Bedrock agent client.
        number_of_results (int): The number of results to return.
        reranking (bool): Whether to rerank the results. Can be globally configured using the BEDROCK_KB_RERANKING_ENABLED environment variable.
        reranking_model_name (Literal['COHERE', 'AMAZON']): The name of the reranking model to use.
        data_source_ids (list[str] | None): The data source IDs to filter the knowledge base by.

    ## Warning: You must use the `resource://knowledgebases` tool to get the knowledge base ID and optionally a data source ID first.

    ## Returns:
    - A string containing the results of the query.
    """
    if reranking and kb_agent_client.meta.region_name not in [
        'us-west-2',
        'us-east-1',
        'ap-northeast-1',
        'ca-central-1',
    ]:
        raise ValueError(
            f'Reranking is not supported in region {kb_agent_client.meta.region_name}'
        )

    retrieve_request: KnowledgeBaseRetrievalConfigurationTypeDef = {
        'vectorSearchConfiguration': {
            'numberOfResults': number_of_results,
        }
    }

    if data_source_ids:
        retrieve_request['vectorSearchConfiguration']['filter'] = {  # type: ignore
            'in': {
                'key': 'x-amz-bedrock-kb-data-source-id',
                'value': data_source_ids,  # type: ignore
            }
        }

    if reranking:
        model_name_mapping = {
            'COHERE': 'cohere.rerank-v3-5:0',
            'AMAZON': 'amazon.rerank-v1:0',
        }
        retrieve_request['vectorSearchConfiguration']['rerankingConfiguration'] = {
            'type': 'BEDROCK_RERANKING_MODEL',
            'bedrockRerankingConfiguration': {
                'modelConfiguration': {
                    'modelArn': f'arn:aws:bedrock:{kb_agent_client.meta.region_name}::foundation-model/{model_name_mapping[reranking_model_name]}'
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
            documents.append({
                'content': result['content'],
                'location': result.get('location', ''),
                'score': result.get('score', ''),
            })

    return '\n\n'.join([json.dumps(document) for document in documents])
