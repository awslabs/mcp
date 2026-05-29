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

"""Memory tools sub-package for the unified AgentCore MCP server.

Provides 21 memory tools via Amazon Bedrock AgentCore Memory APIs.

Tools that create billable resources or incur compute costs:
- memory_create: Provisions Memory infrastructure (AWS charges)
- memory_update: Adding strategies increases processing costs
- memory_create_event: Triggers background extraction (compute charges)
- memory_retrieve_records: Semantic search (embedding charges)
- memory_batch_create_records: Storage and indexing charges
- memory_batch_update_records: Re-indexing charges
- memory_start_extraction_job: Extraction pipeline (compute charges)

Read-only tools (no cost):
- memory_get, memory_list, memory_get_event, memory_list_events,
  memory_list_actors, memory_list_sessions, memory_get_record,
  memory_list_records, memory_list_extraction_jobs, get_memory_guide

Destructive tools (permanent, irreversible):
- memory_delete, memory_delete_event, memory_delete_record,
  memory_batch_delete_records
"""

from .controlplane import ControlPlaneTools
from .events import EventTools
from .extraction import ExtractionTools
from .guide import GuideTools
from .memory_client import get_control_plane_client, get_data_plane_client
from .records import RecordTools
from loguru import logger


def register_memory_tools(mcp):
    """Register all Memory tools with the MCP server.

    Creates cached boto3 clients for control plane and data plane,
    then registers tool groups.
    """
    groups = [
        ('controlplane', ControlPlaneTools, get_control_plane_client),
        ('events', EventTools, get_data_plane_client),
        ('records', RecordTools, get_data_plane_client),
        ('extraction', ExtractionTools, get_data_plane_client),
        ('guide', GuideTools, None),
    ]
    for name, cls, client_factory in groups:
        try:
            if client_factory is not None:
                cls(client_factory).register(mcp)
            else:
                cls().register(mcp)
        except Exception as e:
            raise RuntimeError(f'Failed to register memory {name} tools: {e}') from e
    logger.info('All memory tool groups registered successfully')
