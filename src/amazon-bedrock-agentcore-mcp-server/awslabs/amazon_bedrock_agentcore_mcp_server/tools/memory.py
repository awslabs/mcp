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

Comprehensive memory operations including create, retrieve, events, and lifecycle management.
"""

from typing import Any, Dict


def manage_agentcore_memory() -> Dict[str, Any]:
    """Provides comprehensive information on how to manage AgentCore Memory resources.

    This tool returns detailed documentation about:
    - Memory resource creation and configuration
    - Event management for conversation tracking
    - Semantic memory retrieval
    - Actor and session management
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
- Actor-based organization: Track conversations per user/actor
- Session management: Group related conversations

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

3. Events:
   - Conversational events track dialogue
   - Associated with actor ID and optional session ID
   - Automatically expire based on retention policy

4. Actors & Sessions:
   - Actor: Unique identifier for user/entity
   - Session: Group of related conversations for an actor
   - Namespace format: /users/{actorId}/{strategyName}

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

CREATE MEMORY EVENT
Command: agentcore memory create-event <memory_id> <actor_id> <payload> [OPTIONS]

Create a conversational event for tracking dialogue.

Arguments:
  memory_id                      Memory resource ID (required)
  actor_id                       Actor ID, e.g., user ID (required)
  payload                        Event payload as JSON string (required)

Options:
  --region, -r TEXT              AWS region
  --session-id, -s TEXT          Session ID for grouping conversations

Event Payload Format:
  {
    "conversational": {
      "content": {
        "text": "Your message here"
      },
      "role": "USER"  // or "ASSISTANT"
    }
  }

Examples:
  # User message
  agentcore memory create-event mem_123 user_456 '{"conversational": {"content": {"text": "Hello!"}, "role": "USER"}}'

  # Assistant response with session
  agentcore memory create-event mem_123 user_456 '{"conversational": {"content": {"text": "Hi there!"}, "role": "ASSISTANT"}}' --session-id session_789

  # Multi-turn conversation
  agentcore memory create-event mem_123 user_456 '{"conversational": {"content": {"text": "What is my name?"}, "role": "USER"}}' -s sess_1
  agentcore memory create-event mem_123 user_456 '{"conversational": {"content": {"text": "Your name is John."}, "role": "ASSISTANT"}}' -s sess_1

═══════════════════════════════════════════════════════════════════

RETRIEVE MEMORIES
Command: agentcore memory retrieve <memory_id> <namespace> <query> [OPTIONS]

Search semantic memories using vector similarity.

Arguments:
  memory_id                      Memory resource ID (required)
  namespace                      Namespace to search in (required)
  query                          Search query text (required)

Options:
  --region, -r TEXT              AWS region
  --top-k, -k INT                Number of results to return (default: 5)

Namespace Format:
  /users/{actorId}/{strategyName}

  Example: /users/user_456/Facts

Examples:
  # Search user preferences
  agentcore memory retrieve mem_123 "/users/user_456/Facts" "What are the user preferences?" --top-k 5

  # Find specific information
  agentcore memory retrieve mem_123 "/users/john_doe/Facts" "favorite color" -k 3

Output:
  - Memory record ID
  - Content text
  - Similarity score

═══════════════════════════════════════════════════════════════════

LIST ACTORS
Command: agentcore memory list-actors <memory_id> [OPTIONS]

List all actors (users) who have interacted with the memory.

Arguments:
  memory_id                      Memory resource ID (required)

Options:
  --region, -r TEXT              AWS region
  --max-results, -n INT          Maximum number of results (default: 100)

Example:
  agentcore memory list-actors mem_123

Output: Table showing Actor ID and Last Activity timestamp

═══════════════════════════════════════════════════════════════════

LIST SESSIONS
Command: agentcore memory list-sessions <memory_id> <actor_id> [OPTIONS]

List all sessions for a specific actor.

Arguments:
  memory_id                      Memory resource ID (required)
  actor_id                       Actor ID (required)

Options:
  --region, -r TEXT              AWS region
  --max-results, -n INT          Maximum number of results (default: 100)

Example:
  agentcore memory list-sessions mem_123 user_456

Output: Table showing Session ID and Last Activity timestamp

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

1. Basic Memory Setup (STM only):
   agentcore memory create my_memory
   agentcore memory create-event my_memory user_1 '{"conversational": {"content": {"text": "Hello"}, "role": "USER"}}'

2. Memory with Semantic Search (STM + LTM):
   agentcore memory create my_memory --strategies '[{"semanticMemoryStrategy": {"name": "Facts"}}]' --wait
   agentcore memory retrieve my_memory "/users/user_1/Facts" "user preferences"

3. Session-based Conversations:
   SESSION_ID="session_$(date +%s)"
   agentcore memory create-event mem_123 user_1 '{"conversational": {"content": {"text": "Hi"}, "role": "USER"}}' -s $SESSION_ID
   agentcore memory create-event mem_123 user_1 '{"conversational": {"content": {"text": "Hello!"}, "role": "ASSISTANT"}}' -s $SESSION_ID

4. Multi-user Memory Management:
   agentcore memory list-actors mem_123
   agentcore memory list-sessions mem_123 user_1
   agentcore memory retrieve mem_123 "/users/user_1/Facts" "preferences"

KEY POINTS:
- Memory resources must be ACTIVE before use
- Events automatically expire based on retention policy
- Semantic strategies enable vector search capabilities
- Namespace format is critical for retrieval: /users/{actorId}/{strategyName}
- Session IDs are optional but recommended for conversation grouping
- Actor IDs should be consistent across your application
- Use --wait flag to ensure resources are ready before proceeding
"""

    return {'memory_guide': memory_guide}
