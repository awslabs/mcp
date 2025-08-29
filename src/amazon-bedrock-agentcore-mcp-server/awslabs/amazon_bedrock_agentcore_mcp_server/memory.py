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

"""AgentCore MCP Server - Memory Management Module.

Contains memory creation, configuration, integration, and management tools.

MCP TOOLS IMPLEMENTED:
• agent_memory - Memory resource management (create, list, health, delete)
• memory_save_conversation - Save user/agent conversation turns
• memory_retrieve - Semantic search and retrieve stored memories
• memory_get_conversation - Get conversation history from memory
• memory_process_turn - Process turn with retrieval and storage
• memory_list_events - List memory events for a session
• memory_create_event - Create structured memory events
"""

import time
from .utils import SDK_AVAILABLE, resolve_app_file_path
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from typing import Any, Dict, List, Literal


# ============================================================================
# MEMORY MANAGEMENT TOOLS
# ============================================================================


def register_memory_tools(mcp: FastMCP):
    """Register memory management tools."""

    @mcp.tool()
    async def memory_save_conversation(
        memory_id: str = Field(description='Memory ID'),
        actor_id: str = Field(description='Actor/user ID'),
        session_id: str = Field(description='Session ID'),
        user_input: str = Field(description='User message'),
        agent_response: str = Field(description='Agent response'),
    ) -> str:
        """Save a conversation turn to memory using MemoryClient.save_turn().

        Stores user input and agent response as a conversation turn in the specified memory.
        """
        if not SDK_AVAILABLE:
            return 'AgentCore SDK not available'

        try:
            from bedrock_agentcore.memory import MemoryClient

            memory_client = MemoryClient()

            result = memory_client.save_turn(
                memory_id=memory_id,
                actor_id=actor_id,
                session_id=session_id,
                user_input=user_input,
                agent_response=agent_response,
            )

            event_id = result.get('eventId', 'unknown')
            timestamp = result.get('eventTimestamp', 'unknown')

            return f"""# Conversation Saved

**Memory ID**: {memory_id}
**Actor**: {actor_id}
**Session**: {session_id}
**Event ID**: {event_id}
**Timestamp**: {timestamp}

**Saved Turn**:
- **User**: {user_input}
- **Agent**: {agent_response}

Conversation turn successfully stored in memory."""

        except Exception as e:
            return f"""Error saving conversation: {str(e)}

**Parameters**:
- Memory ID: {memory_id}
- Actor ID: {actor_id}
- Session ID: {session_id}"""

    @mcp.tool()
    async def memory_retrieve(
        memory_id: str = Field(description='Memory ID'),
        namespace: str = Field(default='default', description='Memory namespace'),
        query: str = Field(description='Search query'),
        actor_id: str = Field(default='', description='Actor ID (optional)'),
        top_k: int = Field(default=3, description='Number of results to return'),
    ) -> str:
        """Retrieve relevant memories using semantic search.

        Uses MemoryClient.retrieve_memories() to find contextually relevant stored memories.
        """
        if not SDK_AVAILABLE:
            return 'AgentCore SDK not available'

        try:
            from bedrock_agentcore.memory import MemoryClient

            memory_client = MemoryClient()

            # Call with optional actor_id
            if actor_id:
                memories = memory_client.retrieve_memories(
                    memory_id=memory_id,
                    namespace=namespace,
                    query=query,
                    actor_id=actor_id,
                    top_k=top_k,
                )
            else:
                memories = memory_client.retrieve_memories(
                    memory_id=memory_id, namespace=namespace, query=query, top_k=top_k
                )

            if not memories:
                return f"""# No Memories Found

**Query**: {query}
**Namespace**: {namespace}
**Memory ID**: {memory_id}

No relevant memories found for this query."""

            result_parts = [
                f'# Retrieved Memories ({len(memories)} found)',
                f'**Query**: {query}',
                f'**Namespace**: {namespace}',
                f'**Memory ID**: {memory_id}',
                '',
            ]

            for i, memory in enumerate(memories, 1):
                score = memory.get('score', 'N/A')
                content = str(memory.get('content', ''))[:200]
                memory_type = memory.get('type', 'unknown')

                result_parts.append(f'## Memory {i}')
                result_parts.append(f'- **Score**: {score}')
                result_parts.append(f'- **Type**: {memory_type}')
                result_parts.append(
                    f'- **Content**: {content}{"..." if len(str(memory.get("content", ""))) > 200 else ""}'
                )
                result_parts.append('')

            return '\n'.join(result_parts)

        except Exception as e:
            return f"""Error retrieving memories: {str(e)}

**Parameters**:
- Memory ID: {memory_id}
- Query: {query}
- Namespace: {namespace}"""

    @mcp.tool()
    async def memory_get_conversation(
        memory_id: str = Field(description='Memory ID'),
        actor_id: str = Field(description='Actor/user ID'),
        session_id: str = Field(description='Session ID'),
        k: int = Field(default=5, description='Number of recent turns to retrieve'),
    ) -> str:
        """Get recent conversation turns from memory.

        Uses MemoryClient.get_last_k_turns() to retrieve conversation history.
        """
        if not SDK_AVAILABLE:
            return 'AgentCore SDK not available'

        try:
            from bedrock_agentcore.memory import MemoryClient

            memory_client = MemoryClient()

            conversation_turns = memory_client.get_last_k_turns(
                memory_id=memory_id, actor_id=actor_id, session_id=session_id, k=k
            )

            if not conversation_turns:
                return f"""# 📖 No Conversation History

**Memory ID**: {memory_id}
**Actor**: {actor_id}
**Session**: {session_id}

No conversation history found for this session."""

            result_parts = [
                f'# Conversation History ({len(conversation_turns)} turns)',
                f'**Memory ID**: {memory_id}',
                f'**Actor**: {actor_id}',
                f'**Session**: {session_id}',
                '',
            ]

            for i, turn in enumerate(conversation_turns, 1):
                result_parts.append(f'## Turn {i}')
                result_parts.append(f'**Messages**: {len(turn)}')

                for j, message in enumerate(turn):
                    role = message.get('role', 'unknown')
                    content = str(message.get('content', ''))[:150]
                    result_parts.append(
                        f'- **{role.title()}**: {content}{"..." if len(str(message.get("content", ""))) > 150 else ""}'
                    )

                result_parts.append('')

            return '\n'.join(result_parts)

        except Exception as e:
            return f"""Error getting conversation: {str(e)}

**Parameters**:
- Memory ID: {memory_id}
- Actor ID: {actor_id}
- Session ID: {session_id}"""

    @mcp.tool()
    async def memory_process_turn(
        memory_id: str = Field(description='Memory ID'),
        actor_id: str = Field(description='Actor/user ID'),
        session_id: str = Field(description='Session ID'),
        user_input: str = Field(description='User message'),
        agent_response: str = Field(description='Agent response'),
        retrieval_namespace: str = Field(
            default='', description='Namespace for retrieval (optional)'
        ),
        retrieval_query: str = Field(default='', description='Custom retrieval query (optional)'),
        top_k: int = Field(default=3, description='Number of memories to retrieve'),
    ) -> str:
        """Process a conversation turn with memory retrieval and storage.

        Uses MemoryClient.process_turn() to retrieve relevant memories and store the new turn.
        """
        if not SDK_AVAILABLE:
            return 'AgentCore SDK not available'

        try:
            from bedrock_agentcore.memory import MemoryClient

            memory_client = MemoryClient()

            # Build parameters
            process_kwargs = {
                'memory_id': memory_id,
                'actor_id': actor_id,
                'session_id': session_id,
                'user_input': user_input,
                'agent_response': agent_response,
                'top_k': top_k,
            }

            if retrieval_namespace:
                process_kwargs['retrieval_namespace'] = retrieval_namespace
            if retrieval_query:
                process_kwargs['retrieval_query'] = retrieval_query

            retrieved_memories, turn_result = memory_client.process_turn(**process_kwargs)

            result_parts = [
                '# Turn Processed',
                f'**Memory ID**: {memory_id}',
                f'**Actor**: {actor_id}',
                f'**Session**: {session_id}',
                '',
            ]

            # Show retrieved memories
            if retrieved_memories:
                result_parts.append(f'## 🔍 Retrieved Memories ({len(retrieved_memories)})')
                for i, memory in enumerate(retrieved_memories, 1):
                    score = memory.get('score', 'N/A')
                    content = str(memory.get('content', ''))[:100]
                    result_parts.append(f'- **Memory {i}** (Score: {score}): {content}...')
                result_parts.append('')

            # Show turn storage result
            event_id = turn_result.get('eventId', 'unknown')
            result_parts.append('## Stored Turn')
            result_parts.append(f'- **Event ID**: {event_id}')
            result_parts.append(f'- **User**: {user_input}')
            result_parts.append(f'- **Agent**: {agent_response}')

            return '\n'.join(result_parts)

        except Exception as e:
            return f""" Error processing turn: {str(e)}

**Parameters**:
- Memory ID: {memory_id}
- Actor ID: {actor_id}
- Session ID: {session_id}"""

    @mcp.tool()
    async def memory_list_events(
        memory_id: str = Field(description='Memory ID'),
        actor_id: str = Field(description='Actor/user ID'),
        session_id: str = Field(description='Session ID'),
        max_results: int = Field(default=100, description='Maximum results to return'),
    ) -> str:
        """List events from memory using MemoryClient.list_events().

        Shows conversation events for the specified memory, actor, and session.
        """
        if not SDK_AVAILABLE:
            return 'AgentCore SDK not available'

        try:
            from bedrock_agentcore.memory import MemoryClient

            memory_client = MemoryClient()

            events = memory_client.list_events(
                memory_id=memory_id,
                actor_id=actor_id,
                session_id=session_id,
                max_results=max_results,
            )

            if not events:
                return f"""# No Events Found

**Memory ID**: {memory_id}
**Actor**: {actor_id}
**Session**: {session_id}

No events found for this session."""

            result_parts = [
                f'# Memory Events ({len(events)} found)',
                f'**Memory ID**: {memory_id}',
                f'**Actor**: {actor_id}',
                f'**Session**: {session_id}',
                '',
            ]

            for i, event in enumerate(events, 1):
                event_id = event.get('eventId', 'unknown')
                event_type = event.get('eventType', 'unknown')
                timestamp = event.get('eventTimestamp', 'unknown')

                result_parts.append(f'## Event {i}')
                result_parts.append(f'- **ID**: {event_id}')
                result_parts.append(f'- **Type**: {event_type}')
                result_parts.append(f'- **Timestamp**: {timestamp}')

                # Show payload if available
                payload = event.get('payload')
                if payload:
                    content = str(payload)[:150]
                    result_parts.append(
                        f'- **Payload**: {content}{"..." if len(str(payload)) > 150 else ""}'
                    )

                result_parts.append('')

            return '\n'.join(result_parts)

        except Exception as e:
            return f""" Error listing events: {str(e)}

**Parameters**:
- Memory ID: {memory_id}
- Actor ID: {actor_id}
- Session ID: {session_id}"""

    @mcp.tool()
    async def memory_create_event(
        memory_id: str = Field(description='Memory ID'),
        actor_id: str = Field(description='Actor/user ID'),
        session_id: str = Field(description='Session ID'),
        messages: List[str] = Field(
            description="List of messages as ['role:content', 'role:content']"
        ),
    ) -> str:
        """Create an event in memory using MemoryClient.create_event().

        Creates a structured event with messages in the specified memory session.
        Format messages as: ["user:Hello", "assistant:Hi there"]
        """
        if not SDK_AVAILABLE:
            return ' AgentCore SDK not available'

        try:
            from bedrock_agentcore.memory import MemoryClient

            memory_client = MemoryClient()

            # Parse messages from "role:content" format to tuples
            parsed_messages = []
            for msg in messages:
                if ':' in msg:
                    role, content = msg.split(':', 1)
                    parsed_messages.append((role.strip(), content.strip()))
                else:
                    return f" Invalid message format: '{msg}'. Use 'role:content' format."

            result = memory_client.create_event(
                memory_id=memory_id,
                actor_id=actor_id,
                session_id=session_id,
                messages=parsed_messages,
            )

            event_id = result.get('eventId', 'unknown')
            timestamp = result.get('eventTimestamp', 'unknown')

            return f"""# Event Created

**Memory ID**: {memory_id}
**Actor**: {actor_id}
**Session**: {session_id}
**Event ID**: {event_id}
**Timestamp**: {timestamp}

**Messages Created**:
{chr(10).join([f'- **{role.title()}**: {content}' for role, content in parsed_messages])}

Event successfully created in memory."""

        except Exception as e:
            return f""" Error creating event: {str(e)}

**Parameters**:
- Memory ID: {memory_id}
- Actor ID: {actor_id}
- Session ID: {session_id}
- Messages: {messages}"""

    @mcp.tool()
    async def agent_memory(
        action: Literal['create', 'list', 'health', 'delete'] = Field(
            default='create',  # Add missing default
            description='Memory action',
        ),
        agent_file: str = Field(default='', description='Agent file to integrate memory with'),
        agent_name: str = Field(default='', description='Agent name for memory operations'),
        memory_id: str = Field(default='', description='Specific memory ID for operations'),
        strategy_types: List[str] = Field(
            default=['semantic', 'summary'], description='Memory strategy types'
        ),
        region: str = Field(default='us-east-1', description='AWS region'),
    ) -> str:
        """Memory: SIMPLIFIED MEMORY MANAGEMENT.

        Streamlined tool for essential memory operations.

        Actions:
        - create: Create memory resource and optionally integrate with agent file
        - list: List all memory resources
        - health: Memory diagnostics and health checks
        - delete: Delete a memory resource (with confirmation)

        Examples:
        - Create memory only: agent_memory(action="create", agent_name="my-agent")
        - Create + integrate: agent_memory(action="create", agent_name="my-agent", agent_file="agent.py")
        """
        if not SDK_AVAILABLE:
            return """ AgentCore SDK Not Available

To use memory functionality:
1. Install: `uv add bedrock-agentcore bedrock-agentcore-starter-toolkit`
2. Configure AWS credentials: `aws configure`
3. Retry memory operations

Alternative: Use AWS Console for memory management"""

        try:
            # Import memory-related classes
            from bedrock_agentcore.memory import MemoryClient, MemoryControlPlaneClient
            # from bedrock_agentcore.memory.constants import MemoryStatus, StrategyType

            # Action: list - List all memory resources (using tested logic)
            if action == 'list':
                try:
                    memory_control = MemoryControlPlaneClient(region_name=region)

                    # Use exact same logic from working test
                    memories_response = memory_control.list_memories()
                    if isinstance(memories_response, list):
                        memories = memories_response
                    else:
                        memories = memories_response.get('memories', [])

                    if not memories:
                        return f"""# No Memory Resources Found

**Region**: {region}

## Getting Started:
Create your first memory resource:
```python
agent_memory(action="create", agent_name="my-agent")
```

## AWS Console:
[Bedrock AgentCore Console](https://console.aws.amazon.com/bedrock/home?region={region}#/agentcore/memories)"""

                    # Format results
                    result_parts = []
                    result_parts.append(f'# Memory Resources ({len(memories)} found)')
                    result_parts.append(f'**Region**: {region}')
                    result_parts.append('')

                    # Group memories by status
                    active_memories = []
                    creating_memories = []
                    failed_memories = []

                    for memory in memories:
                        # Use exact field names from working test
                        memory_id = memory.get('id', 'unknown')  # Test shows 'id' not 'memoryId'
                        memory_arn = memory.get('arn', '')
                        # Extract name from ARN like in our working list script
                        memory_name = memory_arn.split('/')[-1] if memory_arn else memory_id
                        status = memory.get('status', 'unknown')
                        created_time = memory.get('createdAt', 'unknown')

                        memory_info = {
                            'id': memory_id,
                            'name': memory_name,
                            'status': status,
                            'created': created_time,
                            'memory': memory,
                        }

                        if status == 'ACTIVE':
                            active_memories.append(memory_info)
                        elif status in ['CREATING', 'UPDATING']:
                            creating_memories.append(memory_info)
                        else:
                            failed_memories.append(memory_info)

                    # Display active memories
                    if active_memories:
                        result_parts.append(f'## ✅ Active Memories ({len(active_memories)}):')
                        for mem in active_memories:
                            result_parts.append(f'### {mem["name"]}')
                            result_parts.append(f'- **ID**: `{mem["id"]}`')
                            result_parts.append(f'- **Status**: {mem["status"]}')
                            result_parts.append(f'- **Created**: {mem["created"]}')
                            result_parts.append('')

                    # Display memories being created
                    if creating_memories:
                        result_parts.append(f'## ⏳ Initializing ({len(creating_memories)}):')
                        for mem in creating_memories:
                            result_parts.append(f'### {mem["name"]}')
                            result_parts.append(f'- **ID**: `{mem["id"]}`')
                            result_parts.append(f'- **Status**: {mem["status"]}')
                            result_parts.append('')

                    # Display failed memories
                    if failed_memories:
                        result_parts.append(f'## ❌ Failed ({len(failed_memories)}):')
                        for mem in failed_memories:
                            result_parts.append(f'### {mem["name"]}')
                            result_parts.append(f'- **ID**: `{mem["id"]}`')
                            result_parts.append(f'- **Status**: {mem["status"]}')
                            result_parts.append('')

                    result_parts.append('## 🔧 Operations:')
                    result_parts.append(
                        '- **Create**: `agent_memory(action="create", agent_name="my-agent")`'
                    )
                    result_parts.append(
                        '- **Health Check**: `agent_memory(action="health", memory_id="MEMORY_ID")`'
                    )
                    result_parts.append(
                        '- **Delete**: `agent_memory(action="delete", memory_id="MEMORY_ID")`'
                    )

                    return '\n'.join(result_parts)

                except Exception as e:
                    return f"""❌ Memory List Error: {str(e)}

**Region**: {region}

**Possible Causes**:
- AWS credentials not configured
- Insufficient permissions
- AgentCore Memory service not available in region

**Troubleshooting**:
1. Check credentials: `aws sts get-caller-identity`
2. Verify region: AgentCore available in us-east-1, us-west-2
3. Check permissions: bedrock-agentcore:ListMemories"""

            # Action: create - Create memory resource and optionally integrate with agent
            elif action == 'create':
                if not agent_name:
                    return """❌ Error: agent_name is required for create action

**Examples**:
```python
# Create memory only
agent_memory(action="create", agent_name="my_agent")

# Create memory and integrate with agent file
agent_memory(action="create", agent_name="my_agent", agent_file="my_agent.py")
```"""

                try:
                    memory_control = MemoryControlPlaneClient(region_name=region)

                    create_steps = []

                    # Use EXACT working logic from test
                    # Sanitize agent name: replace hyphens with underscores
                    sanitized_agent_name = agent_name.replace('-', '_')
                    if sanitized_agent_name != agent_name:
                        create_steps.append(
                            f"🔧 Fixed agent name: '{agent_name}' → '{sanitized_agent_name}' (replaced - with _)"
                        )
                        agent_name = sanitized_agent_name

                    create_steps.append(f' Creating memory resource for agent: **{agent_name}**')

                    # Create strategies with EXACT format from working test
                    strategy_mapping = {
                        'semantic': 'semanticMemoryStrategy',
                        'summary': 'summaryMemoryStrategy',
                        'user_preference': 'userPreferenceMemoryStrategy',
                        'custom': 'customMemoryStrategy',
                    }

                    memory_strategies = []
                    for strategy_name in strategy_types:
                        strategy_key = strategy_mapping.get(strategy_name.lower())
                        if strategy_key:
                            # Use EXACT format from working test
                            strategy_dict = {strategy_key: {'name': f'{strategy_name}_strategy'}}
                            memory_strategies.append(strategy_dict)
                            create_steps.append(
                                f'📝 Added {strategy_name} strategy: {strategy_dict}'
                            )

                    if not memory_strategies:
                        # Default to semantic if no valid strategies - same as test
                        memory_strategies = [
                            {'semanticMemoryStrategy': {'name': 'semantic_strategy'}}
                        ]
                        create_steps.append(' Using default semantic strategy')

                    create_steps.append(f' Final strategies: {memory_strategies}')

                    # Create the memory - same as test
                    create_result = memory_control.create_memory(
                        name=f'{sanitized_agent_name}_memory', strategies=memory_strategies
                    )

                    memory_id = create_result.get('memoryId', '')
                    if not memory_id:
                        raise Exception('Failed to get memory ID from create result')
                    create_steps.append(f' Memory created with ID: **{memory_id}**')

                    # Wait for memory to become active
                    create_steps.append(' Waiting for memory to become active...')

                    max_wait_time = 180  # 3 minutes
                    wait_start = time.time()

                    while time.time() - wait_start < max_wait_time:
                        status_result = memory_control.get_memory(memory_id=memory_id)
                        status = status_result.get('status', 'UNKNOWN')

                        create_steps.append(f' Memory status: **{status}**')

                        if status == 'ACTIVE':
                            create_steps.append(' Memory is active and ready!')
                            break
                        elif status in ['CREATE_FAILED', 'DELETE_FAILED']:
                            create_steps.append(f' Memory creation failed: {status}')
                            break

                        time.sleep(10)
                    else:
                        create_steps.append(
                            ' Memory still initializing - may take a few more minutes'
                        )

                    # Optional: Integrate with agent file if provided
                    integration_result = ''
                    if agent_file:
                        create_steps.append(
                            f' Integrating memory with agent file: **{agent_file}**'
                        )

                        # Resolve agent file path
                        resolved_file = resolve_app_file_path(agent_file)
                        if not resolved_file:
                            create_steps.append(f' Agent file not found: {agent_file}')
                            integration_result = f'\n Memory created but integration skipped - file not found: **{agent_file}**'
                        else:
                            try:
                                # Read agent code
                                with open(resolved_file, 'r') as f:
                                    agent_code = f.read()

                                # Check if memory is already integrated
                                if 'MemoryClient' in agent_code and memory_id in agent_code:
                                    create_steps.append(' Memory already integrated')
                                else:
                                    # Perform integration
                                    code_lines = agent_code.split('\n')

                                    # Add import
                                    import_added = False
                                    for i, line in enumerate(code_lines):
                                        if 'from bedrock_agentcore' in line and not import_added:
                                            code_lines.insert(
                                                i + 1,
                                                'from bedrock_agentcore.memory import MemoryClient',
                                            )
                                            import_added = True
                                            break

                                    if not import_added:
                                        code_lines.insert(
                                            0, 'from bedrock_agentcore.memory import MemoryClient'
                                        )

                                    # Add memory client initialization
                                    for i, line in enumerate(code_lines):
                                        if 'BedrockAgentCoreApp()' in line:
                                            code_lines.insert(
                                                i + 1,
                                                f'memory_client = MemoryClient(memory_id="{memory_id}")',
                                            )
                                            break

                                    # Write updated code
                                    updated_code = '\n'.join(code_lines)

                                    # Create backup
                                    backup_file = f'{resolved_file}.backup'
                                    with open(backup_file, 'w') as f:
                                        f.write(agent_code)

                                    with open(resolved_file, 'w') as f:
                                        f.write(updated_code)

                                    create_steps.append(
                                        f' Memory integrated with **{resolved_file}**'
                                    )
                                    create_steps.append(f'💾 Backup created: **{backup_file}**')

                                    integration_result = f"""

## Agent Integration Complete
- **Updated File**: `{resolved_file}`
- **Backup Created**: `{backup_file}`
- **Memory Client**: Ready to use"""

                            except Exception as integration_error:
                                create_steps.append(
                                    f' Integration failed: {str(integration_error)}'
                                )
                                integration_result = f'\n Memory created but integration failed: **{str(integration_error)}**'

                    return f"""# Memory Created Successfully

## Creation Steps:
{chr(10).join(f'- {step}' for step in create_steps)}

## Memory Information:
- **Memory ID**: `{memory_id}`
- **Agent**: `{agent_name}`
- **Strategies**: {strategy_types}
- **Region**: `{region}`
- **Status**: Active (ready to use){integration_result}

## Usage in Your Agent Code:
```python
from bedrock_agentcore.memory import MemoryClient

memory_client = MemoryClient(memory_id="{memory_id}")

# Store context
memory_client.store_memory("conversation", {{
    "user": user_message,
    "response": response
}})

# Retrieve relevant memories
context = memory_client.retrieve_memories(user_message, max_results=5)
```

## Management Commands:
- **Health Check**: `agent_memory(action="health", memory_id="{memory_id}")`
- **Delete Memory**: `agent_memory(action="delete", memory_id="{memory_id}")`

Your agent now has intelligent memory capabilities! """

                except Exception as e:
                    return f""" Memory Creation Error: {str(e)}

**Agent Name**: `{agent_name}`
**Strategies**: {strategy_types}
**Region**: {region}

**Troubleshooting**:
1. Check AWS credentials and permissions
2. Verify AgentCore Memory service is available in region
3. Try with different strategy types
4. Check AWS Console for partial resources"""

            # Action: health - Check memory health and diagnostics
            elif action == 'health':
                if not memory_id:
                    return """ Error: memory_id is required for health action

**Example**:
```python
agent_memory(action="health", memory_id="mem-12345")
```

To find memory IDs: `agent_memory(action="list")`"""

                try:
                    memory_control = MemoryControlPlaneClient(region_name=region)

                    health_steps = []
                    health_info = {}

                    # Get memory details
                    health_steps.append(f' Checking memory: **{memory_id}**')

                    memory_details = memory_control.get_memory(memory_id=memory_id)
                    health_info['details'] = memory_details

                    status = memory_details.get('status', 'UNKNOWN')
                    name = memory_details.get('name', memory_id)
                    created_time = memory_details.get('createdAt', 'unknown')
                    strategies = memory_details.get('strategies', [])

                    health_steps.append(f' Memory found: **{name}**')
                    health_steps.append(f' Status: **{status}**')

                    # Check if memory is healthy
                    is_healthy = status == 'ACTIVE'

                    if is_healthy:
                        health_steps.append(' Memory is healthy and active')

                        # Try to create a memory client to test connectivity
                        try:
                            memory_client = MemoryClient(region_name=region)
                            print(dir(memory_client))  # Debugging line
                            health_steps.append(' Memory client connection successful')
                            health_info['client_test'] = 'PASSED'
                        except Exception as client_error:
                            health_steps.append(f' Memory client test failed: {str(client_error)}')
                            health_info['client_test'] = f'FAILED: {str(client_error)}'

                    else:
                        health_steps.append(f' Memory is not healthy: **{status}**')
                        is_healthy = False

                    # Format strategies
                    strategy_names = (
                        [s.get('strategyType', 'unknown') for s in strategies]
                        if strategies
                        else ['none']
                    )

                    health_status = 'HEALTHY' if is_healthy else 'UNHEALTHY'

                    return f"""#  Memory Health Check

## Health Status: {health_status}

## Diagnostic Steps:
{chr(10).join(f'- {step}' for step in health_steps)}

## Memory Information:
- **Memory ID**: `{memory_id}`
- **Name**: `{name}`
- **Status**: `{status}`
- **Created**: `{created_time}`
- **Strategies**: `{strategy_names}`
- **Region**: `{region}`

## Connectivity Test:
- **Client Test**: `{health_info.get('client_test', 'Not tested')}`

## Recommendations:
{get_memory_health_recommendations(status, health_info)}

## Next Steps:
{get_memory_health_next_steps(is_healthy, memory_id)}

Memory diagnostic complete."""

                except Exception as e:
                    return f""" Memory Health Check Error: {str(e)}

**Memory ID**: `{memory_id}`
**Region**: {region}

**Possible Causes**:
- Memory ID doesn't exist or was deleted
- AWS credentials or permissions issues
- Memory service unavailable
- Network connectivity problems

**Troubleshooting**:
1. Verify memory exists: `agent_memory(action="list")`
2. Check AWS credentials: `aws sts get-caller-identity`
3. Try creating new memory if needed"""

            # Action: delete - Delete memory with confirmation
            elif action == 'delete':
                if not memory_id:
                    return """ Error: memory_id is required for delete action

**Example**:
```python
agent_memory(action="delete", memory_id="mem-12345")
```

To find memory IDs: `agent_memory(action="list")`"""

                try:
                    memory_control = MemoryControlPlaneClient(region_name=region)

                    # Get memory details first for confirmation info
                    memory_details = memory_control.get_memory(memory_id=memory_id)
                    memory_name = memory_details.get('name', memory_id)

                    # Delete the memory
                    delete_result = memory_control.delete_memory(memory_id=memory_id)

                    return f"""#  Memory Deleted Successfully

## Deleted Memory:
- **Memory ID**: `{memory_id}`
- **Name**: `{memory_name}`
- **Region**: `{region}`
- **Status**: Deleted

- **Delete results**: {delete_result}
## Important Notes:
- **Deletion is permanent and cannot be undone**
- All stored memories and context have been permanently removed
- Any agents using this memory will lose memory capabilities
- Memory client references in agent code will fail

## Next Steps:
- Remove memory references from agent code
- Update agent deployments to remove memory integration
- Create new memory if needed: `agent_memory(action="create", agent_name="agent-name")`

## Agent Code Cleanup:
If you have agents using this memory, update them to remove:
```python
# Remove these lines from your agent code:
memory_client = MemoryClient(memory_id="{memory_id}")
# And any memory_client.store_memory() or retrieve_memories() calls
```

Memory **{memory_name}** has been permanently deleted."""

                except Exception as e:
                    return f""" Memory Deletion Error: {str(e)}

**Memory ID**: `{memory_id}`
**Region**: {region}

**Possible Causes**:
- Memory ID doesn't exist or was already deleted
- Memory is still in use by active agents
- Insufficient permissions
- Network connectivity issues

**Troubleshooting**:
1. Verify memory exists: `agent_memory(action="list")`
2. Check if memory is used by agents
3. Try again after a few minutes (propagation delay)
4. Use AWS Console for manual deletion if needed"""

            # Default case
            else:
                return f""" Unknown Action: '{action}'

## Available Actions:
- **create**: Create memory (+ optional integration)
- **list**: List all memories
- **health**: Check memory status
- **delete**: Delete memory

## Examples:
```python
# Create memory only
agent_memory(action="create", agent_name="my_agent")

# Create + integrate with agent file
agent_memory(action="create", agent_name="my_agent", agent_file="agent.py")
```"""

        except ImportError as e:
            return f""" Memory SDK Not Available

**Error**: {str(e)}

To use memory functionality:
1. Install AgentCore SDK: `uv add bedrock-agentcore`
2. Install starter toolkit: `uv add bedrock-agentcore-starter-toolkit`
3. Configure AWS credentials: `aws configure`

Alternative: Use AWS Console for memory management"""

        except Exception as e:
            return f""" Memory Operation Error: {str(e)}

**Action**: {action}
**Agent**: {agent_name or 'Not specified'}
**Memory ID**: {memory_id or 'Not specified'}
**Region**: {region}

**Troubleshooting**:
1. Check AWS credentials: `aws sts get-caller-identity`
2. Verify permissions for bedrock-agentcore memory operations
3. Check memory exists: `agent_memory(action="list")`
4. Try individual actions for debugging"""


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def get_memory_health_recommendations(status: str, health_info: Dict[str, Any]) -> str:
    """Generate health recommendations based on memory status."""
    if status == 'ACTIVE':
        if health_info.get('client_test') == 'PASSED':
            return """ Memory is fully operational
- All systems functioning normally
- Ready for production use
- No action required"""
        else:
            return """ Memory is active but client connectivity has issues
- Check network connectivity
- Verify AWS credentials
- Try recreating memory client"""

    elif status in ['CREATING', 'UPDATING']:
        return """ Memory is still initializing
- Wait for memory to become ACTIVE
- Initialization can take 2-5 minutes
- Check status again in a few minutes"""

    elif 'FAILED' in status:
        return """ Memory has failed and needs attention
- Delete and recreate memory
- Check AWS service health
- Verify permissions and quotas
- Contact AWS support if issues persist"""

    else:
        return f""" Unknown status: {status}
- Check AWS Console for more details
- Try recreating memory if issues persist
- Contact AWS support for assistance"""


def get_memory_health_next_steps(is_healthy: bool, memory_id: str) -> str:
    """Generate next steps based on memory health."""
    if is_healthy:
        return """- **Use Memory**: Integrate with agent code and deploy
- **Monitor**: Set up regular health checks
- **Test**: Verify memory operations work as expected
- **Scale**: Add more memory strategies if needed"""
    else:
        return """- **Troubleshoot**: Address the issues identified above
- **Recreate**: Consider deleting and recreating memory
- **Support**: Contact AWS support if problems persist
- **Alternative**: Use different memory strategies or region"""
