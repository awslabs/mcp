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
"""Knowledge base type detection.

Managed knowledge bases (``type: MANAGED``) and vector knowledge bases take
different ``Retrieve`` configurations, and expose data-source identity under
different metadata keys. Sending the wrong shape either fails outright or --
worse -- silently returns zero results.
"""

from loguru import logger
from typing import TYPE_CHECKING, Optional


if TYPE_CHECKING:
    from mypy_boto3_bedrock_agent.client import AgentsforBedrockClient
else:
    AgentsforBedrockClient = object


MANAGED_KB_TYPE = 'MANAGED'
VECTOR_KB_TYPE = 'VECTOR'

MANAGED_SEARCH_CONFIGURATION = 'managedSearchConfiguration'
VECTOR_SEARCH_CONFIGURATION = 'vectorSearchConfiguration'

# Managed knowledge bases surface data-source identity as ``_data_source_id``.
# Vector knowledge bases use the ``x-amz-bedrock-kb-*`` reserved keys. Filtering a
# managed knowledge base on the vector key is accepted by the API but matches
# nothing, so the caller sees an empty result set rather than an error.
MANAGED_DATA_SOURCE_ID_KEY = '_data_source_id'
VECTOR_DATA_SOURCE_ID_KEY = 'x-amz-bedrock-kb-data-source-id'

# Knowledge base id -> knowledgeBaseConfiguration.type.
# Keyed by id alone, which is safe because a server process talks to one account and
# region, and a knowledge base's type never changes for its lifetime.
_KB_TYPE_CACHE: dict[str, str] = {}


def cache_knowledge_base_type(knowledge_base_id: str, knowledge_base_type: str) -> None:
    """Record a knowledge base's type so ``Retrieve`` calls can skip the lookup."""
    if knowledge_base_id and knowledge_base_type:
        _KB_TYPE_CACHE[knowledge_base_id] = knowledge_base_type


def clear_knowledge_base_type_cache() -> None:
    """Clear the cache. Intended for tests."""
    _KB_TYPE_CACHE.clear()


def get_knowledge_base_type(
    knowledge_base_id: str,
    agent_mgmt_client: Optional[AgentsforBedrockClient] = None,
) -> str:
    """Resolve a knowledge base's type, preferring the discovery-populated cache.

    Returns an empty string when the type cannot be determined -- for example when
    the caller lacks ``bedrock:GetKnowledgeBase``. Callers must treat an empty
    string as "unknown" and fall back rather than assuming a type.
    """
    cached = _KB_TYPE_CACHE.get(knowledge_base_id)
    if cached:
        return cached

    if agent_mgmt_client is None:
        return ''

    try:
        response = agent_mgmt_client.get_knowledge_base(knowledgeBaseId=knowledge_base_id)
    except Exception as exc:  # noqa: BLE001 - lookup is best-effort
        logger.warning(f'Could not determine type of knowledge base {knowledge_base_id}: {exc}')
        return ''

    kb_type = (
        response.get('knowledgeBase', {}).get('knowledgeBaseConfiguration', {}).get('type', '')
    )
    cache_knowledge_base_type(knowledge_base_id, kb_type)
    return kb_type


def is_managed_knowledge_base(
    knowledge_base_id: str,
    agent_mgmt_client: Optional[AgentsforBedrockClient] = None,
) -> Optional[bool]:
    """Return True/False for managed, or None when the type is unknown."""
    kb_type = get_knowledge_base_type(knowledge_base_id, agent_mgmt_client)
    if not kb_type:
        return None
    return kb_type == MANAGED_KB_TYPE


def search_configuration_key(managed: bool) -> str:
    """Return the ``retrievalConfiguration`` key for the knowledge base type."""
    return MANAGED_SEARCH_CONFIGURATION if managed else VECTOR_SEARCH_CONFIGURATION


def data_source_id_metadata_key(managed: bool) -> str:
    """Return the metadata key holding data-source identity for the KB type."""
    return MANAGED_DATA_SOURCE_ID_KEY if managed else VECTOR_DATA_SOURCE_ID_KEY
