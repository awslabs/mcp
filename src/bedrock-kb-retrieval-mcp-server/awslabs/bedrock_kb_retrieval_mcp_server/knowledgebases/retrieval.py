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
    reranking: bool = False,
    reranking_model_name: Literal['COHERE', 'AMAZON'] = 'AMAZON',
    data_source_ids: list[str] | None = None,
    metadata_filter: dict | None = None,
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
        metadata_filter (dict | None): A Bedrock RetrievalFilter object to filter results by document metadata attributes. Passed through unchanged. Raises ValueError if empty, since the API rejects an empty filter. When combined with data_source_ids: a top-level 'andAll' filter has the data-source condition merged into its list (preserving depth); otherwise both are wrapped in a new 'andAll'. Raises ValueError if the filter is a top-level 'orAll' containing embedded filter groups, since no composition fits Bedrock's one-level embedding limit.

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

    retrieve_request: KnowledgeBaseRetrievalConfigurationTypeDef = {
        'vectorSearchConfiguration': {
            'numberOfResults': number_of_results,
        }
    }

    if metadata_filter is not None and not metadata_filter:
        raise ValueError(
            'metadata_filter must not be empty; omit the parameter to query without '
            'a metadata filter.'
        )

    ds_filter: dict | None = None
    if data_source_ids:
        ds_filter = {
            'in': {
                'key': 'x-amz-bedrock-kb-data-source-id',
                'value': data_source_ids,
            }
        }

    combined_filter: dict | None = None
    if ds_filter is not None and metadata_filter is not None:
        # The Retrieve API allows only one level of embedded filter groups, so the
        # data-source condition must compose without deepening the user's filter.
        if set(metadata_filter) == {'andAll'} and isinstance(metadata_filter['andAll'], list):
            # AND is associative: merging preserves both semantics and depth. The API
            # requires andAll to have at least 2 members, so a merged list of one
            # (from a vacuous {'andAll': []}) is emitted as a bare condition.
            members = [*metadata_filter['andAll'], ds_filter]
            combined_filter = {'andAll': members} if len(members) >= 2 else members[0]
        elif (
            set(metadata_filter) == {'orAll'}
            and isinstance(metadata_filter['orAll'], list)
            and any(
                isinstance(member, dict) and ('andAll' in member or 'orAll' in member)
                for member in metadata_filter['orAll']
            )
        ):
            raise ValueError(
                'Cannot combine data_source_ids with this metadata_filter within '
                "Bedrock's one-level filter embedding limit; fold the data-source "
                'condition into metadata_filter using key '
                "'x-amz-bedrock-kb-data-source-id', or omit data_source_ids."
            )
        else:
            combined_filter = {'andAll': [metadata_filter, ds_filter]}
    elif metadata_filter is not None:
        combined_filter = metadata_filter
    elif ds_filter is not None:
        combined_filter = ds_filter

    if combined_filter is not None:
        retrieve_request['vectorSearchConfiguration']['filter'] = combined_filter  # type: ignore

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
            documents.append(
                {
                    'content': result['content'],
                    'location': result.get('location', ''),
                    'score': result.get('score', ''),
                    'metadata': result.get('metadata', {}),
                }
            )

    return '\n\n'.join([json.dumps(document) for document in documents])
