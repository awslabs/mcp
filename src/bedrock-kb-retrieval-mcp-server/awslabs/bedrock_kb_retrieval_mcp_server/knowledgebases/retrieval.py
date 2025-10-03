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
    rerank_model_arn: str | None = None,
    data_source_ids: list[str] | None = None,
) -> str:
    """# Amazon Bedrock Knowledge Base query tool.

    Args:
        query (str): The query to search the knowledge base with.
        knowledge_base_id (str): The knowledge base ID to query.
        kb_agent_client (AgentsforBedrockRuntimeClient): The Bedrock agent client.
        number_of_results (int): The number of results to return.
        rerank_model_arn (str | None): The full ARN of the reranking model to use. If provided, reranking will be enabled. Can be globally configured using the RERANK_MODEL_ARN environment variable.
        data_source_ids (list[str] | None): The data source IDs to filter the knowledge base by.

    ## Warning: You must use the `ListKnowledgeBases` tool to get the knowledge base ID and optionally a data source ID first.

    ## Returns:
    - A string containing the results of the query.
    """

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

    if rerank_model_arn:
        retrieve_request['vectorSearchConfiguration']['rerankingConfiguration'] = {
            'type': 'BEDROCK_RERANKING_MODEL',
            'bedrockRerankingConfiguration': {
                'modelConfiguration': {
                    'modelArn': rerank_model_arn
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
