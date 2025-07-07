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
from ..models import KnowledgeBaseMapping
from loguru import logger
from typing import TYPE_CHECKING, Optional


if TYPE_CHECKING:
    from mypy_boto3_bedrock_agent import AgentsforBedrockClient
else:
    AgentsforBedrockClient = object


DEFAULT_KNOWLEDGE_BASE_TAG_INCLUSION_KEY = 'mcp-multirag-kb'


async def discover_knowledge_bases(
    agent_client: AgentsforBedrockClient,
    tag_key: str = DEFAULT_KNOWLEDGE_BASE_TAG_INCLUSION_KEY,
    kb_id_override: Optional[str] = None,
) -> KnowledgeBaseMapping:
    """Discover knowledge bases.

    Args:
        agent_client (AgentsforBedrockClient): The Bedrock agent client
        tag_key (str): The tag key to filter knowledge bases by
        kb_id_override (str, optional): Override to use a specific knowledge base ID instead of discovery

    Returns:
        KnowledgeBaseMapping: A mapping of knowledge base IDs to knowledge base details
    """
    result: KnowledgeBaseMapping = {}

    # If a specific knowledge base ID is provided, use only that one
    if kb_id_override:
        logger.info(f'Using knowledge base ID override: {kb_id_override}')
        try:
            kb_response = agent_client.get_knowledge_base(knowledgeBaseId=kb_id_override)
            kb_name = kb_response.get('knowledgeBase', {}).get('name', 'Unknown')
            kb_data = [(kb_id_override, kb_name)]
        except Exception as e:
            logger.error(f'Error getting knowledge base {kb_id_override}: {e}')
            return result
    else:
        # Collect all knowledge bases with their ARNs in one pass
        kb_data = []
        kb_paginator = agent_client.get_paginator('list_knowledge_bases')

        # First, collect all knowledge bases that match our tag criteria
        for page in kb_paginator.paginate():
            for kb in page.get('knowledgeBaseSummaries', []):
                logger.debug(f'KB: {kb}')
                kb_id = kb.get('knowledgeBaseId')
                kb_name = kb.get('name')

                kb_arn = (
                    agent_client.get_knowledge_base(knowledgeBaseId=kb_id)
                    .get('knowledgeBase', {})
                    .get('knowledgeBaseArn')
                )

                tags = agent_client.list_tags_for_resource(resourceArn=kb_arn).get('tags', {})
                if tag_key in tags and tags[tag_key] == 'true':
                    logger.debug(f'KB Name: {kb_name}')
                    kb_data.append((kb_id, kb_name))

    # Then, for each matching knowledge base, collect its data sources
    for kb_id, kb_name in kb_data:
        result[kb_id] = {'name': kb_name, 'data_sources': []}

        # Collect data sources for this knowledge base
        data_sources = []
        data_sources_paginator = agent_client.get_paginator('list_data_sources')

        for page in data_sources_paginator.paginate(knowledgeBaseId=kb_id):
            for ds in page.get('dataSourceSummaries', []):
                ds_id = ds.get('dataSourceId')
                ds_name = ds.get('name')
                logger.debug(f'DS: {ds}')
                data_sources.append({'id': ds_id, 'name': ds_name})

        result[kb_id]['data_sources'] = data_sources

    return result
