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

"""AgentCore Runtime tools sub-package.

Provides MCP tools for managing and invoking agents hosted in
Amazon Bedrock AgentCore Runtime.

Tool cost classification
------------------------

**Per-use billable (create/use microVM sessions — compute charges):**
- invoke_agent_runtime
  Invokes an agent, spinning up or reusing a microVM session.

**One-time setup (creates infrastructure):**
- create_agent_runtime
  Creates a runtime definition, DEFAULT endpoint, and container deployment.
- create_agent_runtime_endpoint
  Creates a custom endpoint pointing to a runtime version.

**Cost-saving (terminates resources early):**
- stop_runtime_session
  Terminates a microVM session immediately instead of waiting for idle timeout.
- delete_agent_runtime / delete_agent_runtime_endpoint
  Removes infrastructure.

**Read-only (no cost):**
- get_agent_runtime, list_agent_runtimes, list_agent_runtime_versions
- get_agent_runtime_endpoint, list_agent_runtime_endpoints
- update_agent_runtime, update_agent_runtime_endpoint
- get_runtime_guide
"""

from loguru import logger

from .runtime_client import get_control_client, get_data_client
from .endpoints import EndpointTools
from .guide import GuideTools
from .invocation import InvocationTools
from .lifecycle import LifecycleTools


def register_runtime_tools(mcp):
    """Register all AgentCore Runtime tools with the MCP server.

    See module docstring for the full tool list and cost classification.
    """
    groups = [
        ('lifecycle', LifecycleTools, get_control_client),
        ('endpoints', EndpointTools, get_control_client),
        ('invocation', InvocationTools, get_data_client),
        ('guide', GuideTools, None),
    ]
    for name, cls, client_factory in groups:
        try:
            if client_factory is not None:
                cls(client_factory).register(mcp)
            else:
                cls().register(mcp)
        except Exception as e:
            raise RuntimeError(f'Failed to register runtime {name} tools: {e}') from e
    logger.info('All runtime tool groups registered successfully')
