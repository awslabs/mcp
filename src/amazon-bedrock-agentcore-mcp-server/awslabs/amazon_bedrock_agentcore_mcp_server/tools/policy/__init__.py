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

"""Policy tools sub-package for the unified AgentCore MCP server.

Provides 15 policy tools via Amazon Bedrock AgentCore Policy APIs.

Tools that create billable resources or incur compute costs:
- policy_engine_create: Provisions a policy engine (AWS infrastructure charges)
- policy_create: Invokes validation pipeline and provisions a policy
- policy_update: Re-invokes validation pipeline
- policy_generation_start: AI-powered generation (foundation model
  invocation; typically the most expensive Policy operation per call)

Read-only tools (no cost):
- policy_engine_get, policy_engine_list,
  policy_get, policy_list,
  policy_generation_get, policy_generation_list,
  policy_generation_list_assets,
  get_policy_guide

Destructive tools (permanent, irreversible):
- policy_engine_delete: Permanently deletes a policy engine
  (requires zero associated policies first)
- policy_delete: Permanently deletes a policy
"""

from .engines import PolicyEngineTools
from .generations import PolicyGenerationTools
from .guide import GuideTools
from .policies import PolicyTools
from .policy_client import get_policy_client
from loguru import logger


def register_policy_tools(mcp):
    """Register all Policy tools with the MCP server.

    Creates a cached boto3 client for the Policy control plane and
    registers all tool groups against it.
    """
    groups = [
        ('engines', PolicyEngineTools, get_policy_client),
        ('policies', PolicyTools, get_policy_client),
        ('generations', PolicyGenerationTools, get_policy_client),
        ('guide', GuideTools, None),
    ]
    for name, cls, client_factory in groups:
        try:
            if client_factory is not None:
                cls(client_factory).register(mcp)
            else:
                cls().register(mcp)
        except Exception as e:
            raise RuntimeError(f'Failed to register policy {name} tools: {e}') from e
    logger.info('All policy tool groups registered successfully')
