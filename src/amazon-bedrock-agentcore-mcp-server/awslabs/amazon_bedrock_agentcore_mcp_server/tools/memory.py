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

"""AgentCore Memory Tool - Manage memory resources and operations.

Comprehensive memory resource management and lifecycle operations.
"""

from typing import Any, Dict


def manage_agentcore_memory() -> Dict[str, Any]:
    """Provides comprehensive information on how to manage AgentCore Memory resources.

    This tool returns detailed documentation about:
    - Memory resource creation and configuration
    - Complete CLI command reference

    Use this tool to understand the complete process of working with AgentCore Memory.
    """
    memory_guide = """
AGENTCORE MEMORY CLI GUIDE
===========================

OVERVIEW:
AgentCore Memory provides persistent knowledge storage with:
- Short-term memory (STM): Conversation events with automatic expiry
- Long-term memory (LTM): Semantic memory strategies for facts and knowledge

MEMORY CONCEPTS:

1. Memory Resource:
   - Container for all memory data
   - Has unique ID and name
   - Configurable event retention (default: 90 days)
   - Supports multiple memory strategies

2. Memory Strategies:
   - Semantic Memory: Store and retrieve facts using vector search
   - Each strategy has a name and namespace
   - Example: "Facts" strategy for user preferences

CLI COMMAND REFERENCE:

═══════════════════════════════════════════════════════════════════

CREATE MEMORY RESOURCE
Command: agentcore memory create <name> [OPTIONS]

Create a new memory resource with optional LTM strategies.

Arguments:
  name                           Name for the memory resource (required)

Options:
  --region, -r TEXT              AWS region (default: session region)
  --description, -d TEXT         Description for the memory
  --event-expiry-days, -e INT    Event retention in days (default: 90)
  --strategies, -s TEXT          JSON string of memory strategies
  --role-arn TEXT                IAM role ARN for memory execution
  --encryption-key-arn TEXT      KMS key ARN for encryption
  --wait/--no-wait               Wait for memory to become ACTIVE (default: --wait)
  --max-wait INT                 Maximum wait time in seconds (default: 300)

Examples:
  # Create basic memory (STM only)
  agentcore memory create my_agent_memory

  # Create with LTM semantic strategy
  agentcore memory create my_memory --strategies '[{"semanticMemoryStrategy": {"name": "Facts"}}]' --wait

  # Create with custom retention
  agentcore memory create my_memory --event-expiry-days 30 --description "Customer support memory"

Strategy JSON Format:
  [
    {
      "semanticMemoryStrategy": {
        "name": "Facts"
      }
    }
  ]

═══════════════════════════════════════════════════════════════════

GET MEMORY DETAILS
Command: agentcore memory get <memory_id> [OPTIONS]

Retrieve detailed information about a memory resource.

Arguments:
  memory_id                      Memory resource ID (required)

Options:
  --region, -r TEXT              AWS region

Example:
  agentcore memory get my_memory_abc123

Output includes:
  - Memory ID and name
  - Status (CREATING, ACTIVE, DELETING, etc.)
  - Description and event expiry settings
  - Configured strategies

═══════════════════════════════════════════════════════════════════

LIST MEMORY RESOURCES
Command: agentcore memory list [OPTIONS]

List all memory resources in your account.

Options:
  --region, -r TEXT              AWS region
  --max-results, -n INT          Maximum number of results (default: 100)

Example:
  agentcore memory list

Output: Table showing ID, Name, Status, and Strategy count

═══════════════════════════════════════════════════════════════════

DELETE MEMORY RESOURCE
Command: agentcore memory delete <memory_id> [OPTIONS]

Delete a memory resource and all associated data.

Arguments:
  memory_id                      Memory resource ID to delete (required)

Options:
  --region, -r TEXT              AWS region
  --wait                         Wait for deletion to complete
  --max-wait INT                 Maximum wait time in seconds (default: 300)

Example:
  agentcore memory delete my_memory_abc123 --wait

WARNING: This permanently deletes all events and semantic memories.

═══════════════════════════════════════════════════════════════════

CHECK MEMORY STATUS
Command: agentcore memory status <memory_id> [OPTIONS]

Get the current provisioning status of a memory resource.

Arguments:
  memory_id                      Memory resource ID (required)

Options:
  --region, -r TEXT              AWS region

Example:
  agentcore memory status mem_123

Possible Status Values:
  - CREATING: Memory is being provisioned
  - ACTIVE: Memory is ready for use
  - UPDATING: Memory is being modified
  - DELETING: Memory is being deleted
  - FAILED: Memory creation/update failed

═══════════════════════════════════════════════════════════════════

COMMON WORKFLOWS:

1. Basic Memory Setup:
   agentcore memory create my_memory

2. Memory with Semantic Search:
   agentcore memory create my_memory --strategies '[{"semanticMemoryStrategy": {"name": "Facts"}}]' --wait

3. Check Memory Status:
   agentcore memory status my_memory
   agentcore memory get my_memory

KEY POINTS:
- Memory resources must be ACTIVE before use
- Events automatically expire based on retention policy
- Semantic strategies enable vector search capabilities
- Use --wait flag to ensure resources are ready before proceeding
"""

    return {'memory_guide': memory_guide}
