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

"""Gateway tools sub-package for the unified AgentCore MCP server.

Provides 15 gateway management tools via Amazon Bedrock AgentCore Gateway
control plane APIs. The gateway data plane (InvokeGateway / tools/call
/ tools/list) is intentionally NOT exposed — invocation uses the MCP
protocol with a JWT bearer token and is designed for agent runtimes,
not interactive management tooling. Use the MCP Inspector for
interactive gateway testing.

Tools that create billable resources or incur compute costs:
- gateway_create: Provisions gateway infrastructure (AWS charges)
- gateway_update: Interceptor changes add Lambda invocation costs
- gateway_target_create: mcpServer targets trigger implicit sync on create
- gateway_target_update: mcpServer targets trigger implicit sync on update
- gateway_target_synchronize: Re-indexes tool catalog (compute charges)
- gateway_resource_policy_put: Misconfigured policies can expose gateway

Read-only tools (no cost):
- gateway_get, gateway_list, gateway_target_get, gateway_target_list,
  gateway_resource_policy_get, get_gateway_guide

Destructive tools (permanent, irreversible):
- gateway_delete, gateway_target_delete, gateway_resource_policy_delete

Excluded operations (not exposed as MCP tools):
- InvokeGateway (data plane) — requires agent-runtime JWT; use MCP
  Inspector for interactive testing.
- TagResource / UntagResource / ListTagsForResource — pass `tags`
  directly to gateway_create instead.
- Credential provider creation — credential material must not flow
  through LLM context. Use `agentcore add credential` or the Identity
  sub-package, then reference the returned providerArn here.
"""

from .gateway_client import get_control_plane_client
from .gateways import GatewayTools
from .guide import GuideTools
from .resource_policy import ResourcePolicyTools
from .targets import GatewayTargetTools
from loguru import logger


def register_gateway_tools(mcp):
    """Register all Gateway tools with the MCP server.

    Creates cached boto3 clients for the control plane, then registers
    tool groups.
    """
    groups = [
        ('gateways', GatewayTools, get_control_plane_client),
        ('targets', GatewayTargetTools, get_control_plane_client),
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
            raise RuntimeError(f'Failed to register gateway {name} tools: {e}') from e
    logger.info('All gateway tool groups registered successfully')
