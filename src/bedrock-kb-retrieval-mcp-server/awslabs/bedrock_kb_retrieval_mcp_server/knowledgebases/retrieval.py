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
from .kb_types import (
    MANAGED_KB_TYPE,
    VECTOR_KB_TYPE,
    cache_knowledge_base_type,
    data_source_id_metadata_key,
    is_managed_knowledge_base,
    search_configuration_key,
)
from loguru import logger
from typing import TYPE_CHECKING, Literal, Optional


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


# Model id for each reranking model name this server accepts.
RERANKING_MODEL_IDS = {
    'COHERE': 'cohere.rerank-v3-5:0',
    'AMAZON': 'amazon.rerank-v1:0',
}

# Regions each reranking model is actually offered in. Availability differs per model:
# Amazon's reranking model is not offered in us-east-1, even though that region otherwise
# supports Bedrock reranking, so a single flat region allowlist lets a request through that
# then fails at the API with an opaque error.
RERANKING_MODEL_REGIONS = {
    'COHERE': {'us-west-2', 'us-east-1', 'ap-northeast-1', 'ca-central-1', 'eu-central-1'},
    'AMAZON': {'us-west-2', 'ap-northeast-1', 'ca-central-1', 'eu-central-1'},
}


def _is_search_configuration_mismatch(exc: Exception) -> bool:
    """Whether the error indicates the wrong search configuration shape was sent.

    The API rejects a mismatch with a ValidationException naming the configuration it
    expected, for example: "vectorSearchConfiguration is not supported for managed
    knowledge bases. Use managedSearchConfiguration instead."
    """
    message = str(exc)
    if 'ValidationException' not in type(exc).__name__ and 'ValidationException' not in message:
        return False
    return 'managedSearchConfiguration' in message or 'vectorSearchConfiguration' in message


def _build_retrieval_configuration(
    managed: bool,
    number_of_results: int,
    region_name: str,
    reranking: bool,
    reranking_model_name: Literal['COHERE', 'AMAZON'],
    data_source_ids: Optional[list[str]],
) -> 'KnowledgeBaseRetrievalConfigurationTypeDef':
    """Build a ``retrievalConfiguration`` for the knowledge base type."""
    config_key = search_configuration_key(managed)
    search_configuration: dict = {'numberOfResults': number_of_results}

    if data_source_ids:
        search_configuration['filter'] = {
            'in': {
                'key': data_source_id_metadata_key(managed),
                'value': data_source_ids,
            }
        }

    if reranking:
        search_configuration['rerankingConfiguration'] = {
            'type': 'BEDROCK_RERANKING_MODEL',
            'bedrockRerankingConfiguration': {
                'modelConfiguration': {
                    'modelArn': f'arn:aws:bedrock:{region_name}::foundation-model/{RERANKING_MODEL_IDS[reranking_model_name]}'
                },
            },
        }

    return {config_key: search_configuration}  # type: ignore[return-value]


async def query_knowledge_base(
    query: str,
    knowledge_base_id: str,
    kb_agent_client: AgentsforBedrockRuntimeClient,
    number_of_results: int = 20,
    reranking: bool = False,
    reranking_model_name: Literal['COHERE', 'AMAZON'] = 'AMAZON',
    data_source_ids: list[str] | None = None,
    kb_agent_mgmt_client: Optional[AgentsforBedrockClient] = None,
    user_id: str | None = None,
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
        user_id (str | None): End-user identity for access-control filtering. Required to
            reach content in ACL-aware data sources (for example SharePoint, OneDrive or
            Confluence with per-document ACLs); such content is otherwise inaccessible.
        kb_agent_mgmt_client (AgentsforBedrockClient | None): Management client used to
            determine whether the knowledge base is managed. Optional -- when omitted,
            the type is taken from the discovery cache, and an incorrect guess is
            recovered from by retrying with the other configuration shape.

    ## Warning: You must use the `ListKnowledgeBases` tool to get the knowledge base ID and optionally a data source ID first.

    ## Returns:
    - A string containing the results of the query.
    """
    region_name = kb_agent_client.meta.region_name

    if reranking:
        supported = RERANKING_MODEL_REGIONS.get(reranking_model_name, set())
        if region_name not in supported:
            raise ValueError(
                f"The '{reranking_model_name}' reranking model is not available in region "
                f'{region_name}. Supported regions: {sorted(supported)}'
            )
    managed = is_managed_knowledge_base(knowledge_base_id, kb_agent_mgmt_client)

    # An unknown type defaults to the vector shape, matching prior behaviour. If that
    # guess is wrong the API says so explicitly, and the retry below corrects it.
    attempt_managed = bool(managed)
    retrieve_request = _build_retrieval_configuration(
        managed=attempt_managed,
        number_of_results=number_of_results,
        region_name=region_name,
        reranking=reranking,
        reranking_model_name=reranking_model_name,
        data_source_ids=data_source_ids,
    )

    extra_args: dict = {}
    if user_id:
        extra_args['userContext'] = {'userId': user_id}

    try:
        response = kb_agent_client.retrieve(
            knowledgeBaseId=knowledge_base_id,
            retrievalQuery={'text': query},
            retrievalConfiguration=retrieve_request,
            **extra_args,
        )
    except Exception as exc:  # noqa: BLE001 - inspect message to recover from a type mismatch
        if managed is not None or not _is_search_configuration_mismatch(exc):
            raise
        logger.info(
            f'Knowledge base {knowledge_base_id} rejected the '
            f'{search_configuration_key(attempt_managed)} shape; retrying as '
            f'{"vector" if attempt_managed else "managed"}.'
        )
        retrieve_request = _build_retrieval_configuration(
            managed=not attempt_managed,
            number_of_results=number_of_results,
            region_name=region_name,
            reranking=reranking,
            reranking_model_name=reranking_model_name,
            data_source_ids=data_source_ids,
        )
        response = kb_agent_client.retrieve(
            knowledgeBaseId=knowledge_base_id,
            retrievalQuery={'text': query},
            retrievalConfiguration=retrieve_request,
            **extra_args,
        )
        # The retry succeeded, so the type is now known. Record it: otherwise every
        # subsequent call would pay the same failed attempt before recovering.
        cache_knowledge_base_type(
            knowledge_base_id, VECTOR_KB_TYPE if attempt_managed else MANAGED_KB_TYPE
        )

    results = response['retrievalResults']
    documents: list[dict] = []
    for result in results:
        if (result.get('content') or {}).get('type') == 'IMAGE':
            logger.warning('Images are not supported at this time. Skipping...')
            continue
        else:
            documents.append(
                {
                    'content': result.get('content', {}),
                    'location': result.get('location', ''),
                    'score': result.get('score', ''),
                }
            )

    return '\n\n'.join([json.dumps(document) for document in documents])
