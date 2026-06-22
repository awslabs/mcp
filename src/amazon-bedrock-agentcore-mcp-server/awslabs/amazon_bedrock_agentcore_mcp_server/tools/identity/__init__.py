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

"""Identity tools sub-package for the unified AgentCore MCP server.

Provides 21 identity tools via Amazon Bedrock AgentCore Identity control
plane APIs. Data plane token-retrieval operations are intentionally NOT
exposed — they return live credential material (OAuth tokens, API keys,
workload access tokens) that should not flow through LLM context. Agents
should use the bedrock-agentcore SDK decorators (@requires_access_token,
@requires_api_key, @requires_iam_access_token) for runtime token
retrieval.

Tools that create/modify resources or incur charges:
- identity_create_workload_identity: Creates a workload identity
- identity_update_workload_identity: Updates allowed OAuth2 return URLs
- identity_create_api_key_provider: Creates a Secrets Manager secret (charges)
- identity_update_api_key_provider: Rotates the stored API key
- identity_create_oauth2_provider: Creates a Secrets Manager secret (charges)
- identity_update_oauth2_provider: Rotates the stored client secret
- identity_set_token_vault_cmk: Switches KMS key — adds KMS charges
- identity_put_resource_policy: Modifies resource-level access controls

Read-only tools (no cost):
- identity_get_workload_identity, identity_list_workload_identities
- identity_get_api_key_provider, identity_list_api_key_providers
- identity_get_oauth2_provider, identity_list_oauth2_providers
- identity_get_token_vault
- identity_get_resource_policy
- get_identity_guide

Destructive tools (permanent, irreversible):
- identity_delete_workload_identity
- identity_delete_api_key_provider
- identity_delete_oauth2_provider
- identity_delete_resource_policy
"""

from .api_key_providers import ApiKeyProviderTools
from .guide import GuideTools
from .identity_client import get_control_plane_client
from .oauth2_providers import Oauth2ProviderTools
from .resource_policy import ResourcePolicyTools
from .token_vault import TokenVaultTools
from .workload_identity import WorkloadIdentityTools
from loguru import logger


def register_identity_tools(mcp):
    """Register all Identity tools with the MCP server.

    Creates a cached boto3 control plane client, then registers tool
    groups. Each group is instantiated with the shared client factory
    so that all tools share a single cached client per region.
    """
    groups = [
        ('workload_identity', WorkloadIdentityTools, get_control_plane_client),
        ('api_key_providers', ApiKeyProviderTools, get_control_plane_client),
        ('oauth2_providers', Oauth2ProviderTools, get_control_plane_client),
        ('token_vault', TokenVaultTools, get_control_plane_client),
        ('resource_policy', ResourcePolicyTools, get_control_plane_client),
        ('guide', GuideTools, None),
    ]
    for name, cls, client_factory in groups:
        try:
            if client_factory is not None:
                cls(client_factory).register(mcp)
            else:
                cls().register(mcp)
        except Exception as e:
            raise RuntimeError(f'Failed to register identity {name} tools: {e}') from e
    logger.info('All identity tool groups registered successfully')
