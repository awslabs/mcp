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
from ..models import KnowledgeBaseMapping
from loguru import logger
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from mypy_boto3_bedrock_agent import AgentsforBedrockClient
else:
    AgentsforBedrockClient = object


DEFAULT_KNOWLEDGE_BASE_TAG_INCLUSION_KEY = 'mcp-multirag-kb'


async def discover_knowledge_bases(
    agent_client: AgentsforBedrockClient,
    tag_key: str = DEFAULT_KNOWLEDGE_BASE_TAG_INCLUSION_KEY,
) -> KnowledgeBaseMapping:
    """Discover knowledge bases.

    Args:
        agent_client (AgentsforBedrockClient): The Bedrock agent client
        tag_key (str): The tag key to filter knowledge bases by

    Returns:
        KnowledgeBaseMapping: A mapping of knowledge base IDs to knowledge base details
    """
    result: KnowledgeBaseMapping = {}

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
