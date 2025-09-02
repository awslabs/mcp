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

"""Test module for memory functionality."""

import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.memory import (
    get_memory_health_next_steps,
    get_memory_health_recommendations,
    register_memory_tools,
)
from unittest.mock import Mock, mock_open, patch


class TestMemoryConversationTools:
    """Test memory conversation management tools."""

    def setup_method(self):
        """Set up test environment."""
        self.test_memory_id = 'mem-test-12345'
        self.test_actor_id = 'user-123'
        self.test_session_id = 'session-456'
        self.test_user_input = 'Hello, how are you?'
        self.test_agent_response = 'I am doing well, thank you for asking!'

    def _create_mock_mcp(self):
        """Create a mock MCP server for testing."""
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP('Test Memory Server')
        register_memory_tools(mcp)
        return mcp

    def _extract_result(self, mcp_result):
        """Extract result string from MCP call_tool return value."""
        if isinstance(mcp_result, tuple) and len(mcp_result) >= 2:
            result_content = mcp_result[1]
            if isinstance(result_content, dict):
                return result_content.get('result', str(mcp_result))
            elif hasattr(result_content, 'content'):
                return str(result_content.content)
            return str(result_content)
        elif hasattr(mcp_result, 'content') and not isinstance(mcp_result, tuple):
            return str(mcp_result.content)
        return str(mcp_result)

    @pytest.mark.asyncio
    async def test_memory_save_conversation_sdk_not_available(self):
        """Test behavior when SDK is not available."""
        mcp = self._create_mock_mcp()

        with patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', False):
            result_tuple = await mcp.call_tool(
                'memory_save_conversation',
                {
                    'memory_id': self.test_memory_id,
                    'actor_id': self.test_actor_id,
                    'session_id': self.test_session_id,
                    'user_input': self.test_user_input,
                    'agent_response': self.test_agent_response,
                },
            )
            result = self._extract_result(result_tuple)

            assert 'AgentCore SDK not available' in result

    @pytest.mark.asyncio
    async def test_memory_save_conversation_success(self):
        """Test successful conversation save."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryClient') as mock_memory_client,
        ):
            mock_client_instance = Mock()
            mock_memory_client.return_value = mock_client_instance

            mock_save_result = {'eventId': 'event-123', 'eventTimestamp': '2024-01-01T12:00:00Z'}
            mock_client_instance.save_turn.return_value = mock_save_result

            result_tuple = await mcp.call_tool(
                'memory_save_conversation',
                {
                    'memory_id': self.test_memory_id,
                    'actor_id': self.test_actor_id,
                    'session_id': self.test_session_id,
                    'user_input': self.test_user_input,
                    'agent_response': self.test_agent_response,
                },
            )
            result = self._extract_result(result_tuple)

            assert 'Conversation Saved' in result
            assert self.test_memory_id in result
            assert self.test_actor_id in result
            assert self.test_session_id in result
            assert 'event-123' in result
            assert self.test_user_input in result
            assert self.test_agent_response in result

            mock_client_instance.save_turn.assert_called_once_with(
                memory_id=self.test_memory_id,
                actor_id=self.test_actor_id,
                session_id=self.test_session_id,
                user_input=self.test_user_input,
                agent_response=self.test_agent_response,
            )

    @pytest.mark.asyncio
    async def test_memory_save_conversation_error(self):
        """Test error handling in conversation save."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryClient') as mock_memory_client,
        ):
            mock_client_instance = Mock()
            mock_memory_client.return_value = mock_client_instance
            mock_client_instance.save_turn.side_effect = Exception('Memory service error')

            result_tuple = await mcp.call_tool(
                'memory_save_conversation',
                {
                    'memory_id': self.test_memory_id,
                    'actor_id': self.test_actor_id,
                    'session_id': self.test_session_id,
                    'user_input': self.test_user_input,
                    'agent_response': self.test_agent_response,
                },
            )
            result = self._extract_result(result_tuple)

            assert 'Error saving conversation' in result
            assert 'Memory service error' in result
            assert self.test_memory_id in result

    @pytest.mark.asyncio
    async def test_memory_retrieve_success(self):
        """Test successful memory retrieval."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryClient') as mock_memory_client,
        ):
            mock_client_instance = Mock()
            mock_memory_client.return_value = mock_client_instance

            mock_memories = [
                {
                    'score': 0.95,
                    'content': 'Previous conversation about weather',
                    'type': 'conversation',
                },
                {
                    'score': 0.87,
                    'content': 'User preference for morning notifications',
                    'type': 'preference',
                },
            ]
            mock_client_instance.retrieve_memories.return_value = mock_memories

            result_tuple = await mcp.call_tool(
                'memory_retrieve',
                {
                    'memory_id': self.test_memory_id,
                    'namespace': 'default',
                    'query': 'weather conversation',
                    'actor_id': self.test_actor_id,
                    'top_k': 3,
                },
            )
            result = self._extract_result(result_tuple)

            assert 'Retrieved Memories (2 found)' in result
            assert 'weather conversation' in result
            assert '0.95' in result
            assert '0.87' in result
            assert 'Previous conversation about weather' in result
            assert 'User preference for morning notifications' in result

            mock_client_instance.retrieve_memories.assert_called_once_with(
                memory_id=self.test_memory_id,
                namespace='default',
                query='weather conversation',
                actor_id=self.test_actor_id,
                top_k=3,
            )

    @pytest.mark.asyncio
    async def test_memory_retrieve_no_actor_id(self):
        """Test memory retrieval without actor_id."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryClient') as mock_memory_client,
        ):
            mock_client_instance = Mock()
            mock_memory_client.return_value = mock_client_instance
            mock_client_instance.retrieve_memories.return_value = []

            result_tuple = await mcp.call_tool(
                'memory_retrieve',
                {
                    'memory_id': self.test_memory_id,
                    'namespace': 'default',
                    'query': 'test query',
                    'top_k': 3,
                },
            )
            result = self._extract_result(result_tuple)

            assert 'No Memories Found' in result

            # Should call without actor_id
            mock_client_instance.retrieve_memories.assert_called_once_with(
                memory_id=self.test_memory_id, namespace='default', query='test query', top_k=3
            )

    @pytest.mark.asyncio
    async def test_memory_retrieve_no_memories(self):
        """Test memory retrieval when no memories found."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryClient') as mock_memory_client,
        ):
            mock_client_instance = Mock()
            mock_memory_client.return_value = mock_client_instance
            mock_client_instance.retrieve_memories.return_value = []

            result_tuple = await mcp.call_tool(
                'memory_retrieve',
                {
                    'memory_id': self.test_memory_id,
                    'namespace': 'default',
                    'query': 'non-existent query',
                },
            )
            result = self._extract_result(result_tuple)

            assert 'No Memories Found' in result
            assert 'non-existent query' in result

    @pytest.mark.asyncio
    async def test_memory_retrieve_error(self):
        """Test error handling in memory retrieval."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryClient') as mock_memory_client,
        ):
            mock_client_instance = Mock()
            mock_memory_client.return_value = mock_client_instance
            mock_client_instance.retrieve_memories.side_effect = Exception('Retrieval failed')

            result_tuple = await mcp.call_tool(
                'memory_retrieve',
                {'memory_id': self.test_memory_id, 'namespace': 'default', 'query': 'test query'},
            )
            result = self._extract_result(result_tuple)

            assert 'Error retrieving memories' in result
            assert 'Retrieval failed' in result

    @pytest.mark.asyncio
    async def test_memory_get_conversation_success(self):
        """Test successful conversation history retrieval."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryClient') as mock_memory_client,
        ):
            mock_client_instance = Mock()
            mock_memory_client.return_value = mock_client_instance

            mock_conversation_turns = [
                [
                    {'role': 'user', 'content': 'Hello'},
                    {'role': 'assistant', 'content': 'Hi there!'},
                ],
                [
                    {'role': 'user', 'content': 'How are you?'},
                    {'role': 'assistant', 'content': 'I am doing well'},
                ],
            ]
            mock_client_instance.get_last_k_turns.return_value = mock_conversation_turns

            result_tuple = await mcp.call_tool(
                'memory_get_conversation',
                {
                    'memory_id': self.test_memory_id,
                    'actor_id': self.test_actor_id,
                    'session_id': self.test_session_id,
                    'k': 5,
                },
            )
            result = self._extract_result(result_tuple)

            assert 'Conversation History (2 turns)' in result
            assert 'Hello' in result
            assert 'Hi there!' in result
            assert 'How are you?' in result
            assert 'I am doing well' in result

            mock_client_instance.get_last_k_turns.assert_called_once_with(
                memory_id=self.test_memory_id,
                actor_id=self.test_actor_id,
                session_id=self.test_session_id,
                k=5,
            )

    @pytest.mark.asyncio
    async def test_memory_get_conversation_no_history(self):
        """Test conversation retrieval when no history exists."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryClient') as mock_memory_client,
        ):
            mock_client_instance = Mock()
            mock_memory_client.return_value = mock_client_instance
            mock_client_instance.get_last_k_turns.return_value = []

            result_tuple = await mcp.call_tool(
                'memory_get_conversation',
                {
                    'memory_id': self.test_memory_id,
                    'actor_id': self.test_actor_id,
                    'session_id': self.test_session_id,
                },
            )
            result = self._extract_result(result_tuple)

            assert 'No Conversation History' in result
            assert self.test_memory_id in result

    @pytest.mark.asyncio
    async def test_memory_process_turn_success(self):
        """Test successful turn processing with retrieval and storage."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryClient') as mock_memory_client,
        ):
            mock_client_instance = Mock()
            mock_memory_client.return_value = mock_client_instance

            mock_retrieved_memories = [{'score': 0.9, 'content': 'Previous weather discussion'}]
            mock_turn_result = {'eventId': 'event-456'}

            mock_client_instance.process_turn.return_value = (
                mock_retrieved_memories,
                mock_turn_result,
            )

            result_tuple = await mcp.call_tool(
                'memory_process_turn',
                {
                    'memory_id': self.test_memory_id,
                    'actor_id': self.test_actor_id,
                    'session_id': self.test_session_id,
                    'user_input': self.test_user_input,
                    'agent_response': self.test_agent_response,
                    'retrieval_namespace': 'custom',
                    'retrieval_query': 'weather',
                    'top_k': 2,
                },
            )
            result = self._extract_result(result_tuple)

            assert 'Turn Processed' in result
            assert 'Retrieved Memories (1)' in result
            assert 'Previous weather discussion' in result
            assert 'event-456' in result
            assert self.test_user_input in result
            assert self.test_agent_response in result

            mock_client_instance.process_turn.assert_called_once_with(
                memory_id=self.test_memory_id,
                actor_id=self.test_actor_id,
                session_id=self.test_session_id,
                user_input=self.test_user_input,
                agent_response=self.test_agent_response,
                top_k=2,
                retrieval_namespace='custom',
                retrieval_query='weather',
            )

    @pytest.mark.asyncio
    async def test_memory_process_turn_no_optional_params(self):
        """Test turn processing without optional parameters."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryClient') as mock_memory_client,
        ):
            mock_client_instance = Mock()
            mock_memory_client.return_value = mock_client_instance
            mock_client_instance.process_turn.return_value = ([], {'eventId': 'event-789'})

            result_tuple = await mcp.call_tool(
                'memory_process_turn',
                {
                    'memory_id': self.test_memory_id,
                    'actor_id': self.test_actor_id,
                    'session_id': self.test_session_id,
                    'user_input': self.test_user_input,
                    'agent_response': self.test_agent_response,
                },
            )
            result = self._extract_result(result_tuple)

            assert 'Turn Processed' in result
            assert 'event-789' in result

            # Should not include optional parameters
            mock_client_instance.process_turn.assert_called_once_with(
                memory_id=self.test_memory_id,
                actor_id=self.test_actor_id,
                session_id=self.test_session_id,
                user_input=self.test_user_input,
                agent_response=self.test_agent_response,
                top_k=3,
            )

    @pytest.mark.asyncio
    async def test_memory_list_events_success(self):
        """Test successful event listing."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryClient') as mock_memory_client,
        ):
            mock_client_instance = Mock()
            mock_memory_client.return_value = mock_client_instance

            mock_events = [
                {
                    'eventId': 'event-1',
                    'eventType': 'conversation',
                    'eventTimestamp': '2024-01-01T12:00:00Z',
                    'payload': {'user': 'Hello', 'assistant': 'Hi'},
                },
                {
                    'eventId': 'event-2',
                    'eventType': 'preference',
                    'eventTimestamp': '2024-01-01T12:05:00Z',
                },
            ]
            mock_client_instance.list_events.return_value = mock_events

            result_tuple = await mcp.call_tool(
                'memory_list_events',
                {
                    'memory_id': self.test_memory_id,
                    'actor_id': self.test_actor_id,
                    'session_id': self.test_session_id,
                    'max_results': 50,
                },
            )
            result = self._extract_result(result_tuple)

            assert 'Memory Events (2 found)' in result
            assert 'event-1' in result
            assert 'event-2' in result
            assert 'conversation' in result
            assert 'preference' in result

            mock_client_instance.list_events.assert_called_once_with(
                memory_id=self.test_memory_id,
                actor_id=self.test_actor_id,
                session_id=self.test_session_id,
                max_results=50,
            )

    @pytest.mark.asyncio
    async def test_memory_list_events_no_events(self):
        """Test event listing when no events exist."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryClient') as mock_memory_client,
        ):
            mock_client_instance = Mock()
            mock_memory_client.return_value = mock_client_instance
            mock_client_instance.list_events.return_value = []

            result_tuple = await mcp.call_tool(
                'memory_list_events',
                {
                    'memory_id': self.test_memory_id,
                    'actor_id': self.test_actor_id,
                    'session_id': self.test_session_id,
                },
            )
            result = self._extract_result(result_tuple)

            assert 'No Events Found' in result
            assert self.test_memory_id in result

    @pytest.mark.asyncio
    async def test_memory_create_event_success(self):
        """Test successful event creation."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryClient') as mock_memory_client,
        ):
            mock_client_instance = Mock()
            mock_memory_client.return_value = mock_client_instance

            mock_create_result = {
                'eventId': 'event-created-123',
                'eventTimestamp': '2024-01-01T12:30:00Z',
            }
            mock_client_instance.create_event.return_value = mock_create_result

            result_tuple = await mcp.call_tool(
                'memory_create_event',
                {
                    'memory_id': self.test_memory_id,
                    'actor_id': self.test_actor_id,
                    'session_id': self.test_session_id,
                    'messages': ['user:Hello there', 'assistant:Hi, how can I help?'],
                },
            )
            result = self._extract_result(result_tuple)

            assert 'Event Created' in result
            assert 'event-created-123' in result
            assert 'Hello there' in result
            assert 'Hi, how can I help?' in result

            mock_client_instance.create_event.assert_called_once_with(
                memory_id=self.test_memory_id,
                actor_id=self.test_actor_id,
                session_id=self.test_session_id,
                messages=[('user', 'Hello there'), ('assistant', 'Hi, how can I help?')],
            )

    @pytest.mark.asyncio
    async def test_memory_create_event_invalid_format(self):
        """Test event creation with invalid message format."""
        mcp = self._create_mock_mcp()

        with patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True):
            result_tuple = await mcp.call_tool(
                'memory_create_event',
                {
                    'memory_id': self.test_memory_id,
                    'actor_id': self.test_actor_id,
                    'session_id': self.test_session_id,
                    'messages': ['invalid message format'],
                },
            )
            result = self._extract_result(result_tuple)

            assert 'Invalid message format' in result
            assert "Use 'role:content' format" in result


class TestAgentMemoryTool:
    """Test the main agent_memory tool with comprehensive coverage."""

    def setup_method(self):
        """Set up test environment."""
        self.test_region = 'us-east-1'
        self.test_agent_name = 'test-agent'
        self.test_memory_id = 'mem-12345'
        self.test_agent_file = 'test_agent.py'

    def _create_mock_mcp(self):
        """Create a mock MCP server for testing."""
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP('Test Memory Server')
        register_memory_tools(mcp)
        return mcp

    def _extract_result(self, mcp_result):
        """Extract result string from MCP call_tool return value."""
        if isinstance(mcp_result, tuple) and len(mcp_result) >= 2:
            result_content = mcp_result[1]
            if isinstance(result_content, dict):
                return result_content.get('result', str(mcp_result))
            elif hasattr(result_content, 'content'):
                return str(result_content.content)
            return str(result_content)
        elif hasattr(mcp_result, 'content') and not isinstance(mcp_result, tuple):
            return str(mcp_result.content)
        return str(mcp_result)

    @pytest.mark.asyncio
    async def test_agent_memory_sdk_not_available(self):
        """Test behavior when SDK is not available."""
        mcp = self._create_mock_mcp()

        with patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', False):
            result_tuple = await mcp.call_tool('agent_memory', {'action': 'list'})
            result = self._extract_result(result_tuple)

            assert 'AgentCore SDK Not Available' in result
            assert 'uv add bedrock-agentcore' in result

    @pytest.mark.asyncio
    async def test_agent_memory_list_action_no_memories(self):
        """Test list action when no memories exist."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryControlPlaneClient') as mock_control_client,
        ):
            mock_client_instance = Mock()
            mock_control_client.return_value = mock_client_instance
            mock_client_instance.list_memories.return_value = {'memories': []}

            result_tuple = await mcp.call_tool('agent_memory', {'action': 'list'})
            result = self._extract_result(result_tuple)

            assert 'No Memory Resources Found' in result
            assert 'Getting Started' in result

    @pytest.mark.asyncio
    async def test_agent_memory_list_action_with_memories(self):
        """Test list action with existing memories."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryControlPlaneClient') as mock_control_client,
        ):
            mock_client_instance = Mock()
            mock_control_client.return_value = mock_client_instance

            mock_memories = [
                {
                    'id': 'mem-123',
                    'arn': 'arn:aws:bedrock:us-east-1:123456789012:memory/active-memory',
                    'status': 'ACTIVE',
                    'createdAt': '2024-01-01T00:00:00Z',
                },
                {
                    'id': 'mem-456',
                    'arn': 'arn:aws:bedrock:us-east-1:123456789012:memory/creating-memory',
                    'status': 'CREATING',
                    'createdAt': '2024-01-02T00:00:00Z',
                },
            ]
            mock_client_instance.list_memories.return_value = mock_memories

            result_tuple = await mcp.call_tool('agent_memory', {'action': 'list'})
            result = self._extract_result(result_tuple)

            assert 'Memory Resources (2 found)' in result
            assert 'Active Memories (1)' in result
            assert 'Initializing (1)' in result
            assert 'active-memory' in result
            assert 'creating-memory' in result

    @pytest.mark.asyncio
    async def test_agent_memory_list_action_error(self):
        """Test list action with error from AWS service."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryControlPlaneClient') as mock_control_client,
        ):
            mock_client_instance = Mock()
            mock_control_client.return_value = mock_client_instance
            mock_client_instance.list_memories.side_effect = Exception('AWS service error')

            result_tuple = await mcp.call_tool('agent_memory', {'action': 'list'})
            result = self._extract_result(result_tuple)

            assert 'Memory List Error' in result
            assert 'AWS service error' in result

    @pytest.mark.asyncio
    async def test_agent_memory_create_action_missing_agent_name(self):
        """Test create action without agent name."""
        mcp = self._create_mock_mcp()

        with patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True):
            result_tuple = await mcp.call_tool('agent_memory', {'action': 'create'})
            result = self._extract_result(result_tuple)

            assert 'agent_name is required' in result

    @pytest.mark.asyncio
    async def test_agent_memory_create_action_success(self):
        """Test successful memory creation."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryControlPlaneClient') as mock_control_client,
            patch('time.time') as mock_time,
            patch('time.sleep'),
        ):
            mock_time.return_value = 1000000

            mock_client_instance = Mock()
            mock_control_client.return_value = mock_client_instance

            # Mock memory creation and status check
            mock_client_instance.create_memory.return_value = {'memoryId': self.test_memory_id}
            mock_client_instance.get_memory.return_value = {'status': 'ACTIVE'}

            result_tuple = await mcp.call_tool(
                'agent_memory',
                {
                    'action': 'create',
                    'agent_name': self.test_agent_name,
                    'strategy_types': ['semantic', 'summary'],
                },
            )
            result = self._extract_result(result_tuple)

            assert 'Memory Created Successfully' in result
            assert self.test_memory_id in result
            assert self.test_agent_name in result
            assert 'MemoryClient' in result

            mock_client_instance.create_memory.assert_called_once()
            mock_client_instance.get_memory.assert_called_with(memory_id=self.test_memory_id)

    @pytest.mark.asyncio
    async def test_agent_memory_create_action_with_agent_file(self):
        """Test memory creation with agent file integration."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryControlPlaneClient') as mock_control_client,
            patch(
                'awslabs.amazon_bedrock_agentcore_mcp_server.memory.resolve_app_file_path'
            ) as mock_resolve,
            patch(
                'builtins.open',
                mock_open(
                    read_data='from bedrock_agentcore import BedrockAgentCoreApp\napp = BedrockAgentCoreApp()\n'
                ),
            ),
            patch('time.sleep'),
        ):
            mock_client_instance = Mock()
            mock_control_client.return_value = mock_client_instance
            mock_client_instance.create_memory.return_value = {'memoryId': self.test_memory_id}
            mock_client_instance.get_memory.return_value = {'status': 'ACTIVE'}

            mock_resolve.return_value = '/path/to/test_agent.py'

            result_tuple = await mcp.call_tool(
                'agent_memory',
                {
                    'action': 'create',
                    'agent_name': self.test_agent_name,
                    'agent_file': self.test_agent_file,
                },
            )
            result = self._extract_result(result_tuple)

            assert 'Memory Created Successfully' in result
            assert 'Agent Integration Complete' in result
            assert 'Backup Created' in result

    @pytest.mark.asyncio
    async def test_agent_memory_create_action_agent_file_not_found(self):
        """Test memory creation when agent file is not found."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryControlPlaneClient') as mock_control_client,
            patch(
                'awslabs.amazon_bedrock_agentcore_mcp_server.memory.resolve_app_file_path'
            ) as mock_resolve,
            patch('time.sleep'),
        ):
            mock_client_instance = Mock()
            mock_control_client.return_value = mock_client_instance
            mock_client_instance.create_memory.return_value = {'memoryId': self.test_memory_id}
            mock_client_instance.get_memory.return_value = {'status': 'ACTIVE'}

            mock_resolve.return_value = None  # File not found

            result_tuple = await mcp.call_tool(
                'agent_memory',
                {
                    'action': 'create',
                    'agent_name': self.test_agent_name,
                    'agent_file': self.test_agent_file,
                },
            )
            result = self._extract_result(result_tuple)

            assert 'Memory Created Successfully' in result
            assert 'integration skipped - file not found' in result

    @pytest.mark.asyncio
    async def test_agent_memory_create_action_error(self):
        """Test create action with error from AWS service."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryControlPlaneClient') as mock_control_client,
        ):
            mock_client_instance = Mock()
            mock_control_client.return_value = mock_client_instance
            mock_client_instance.create_memory.side_effect = Exception('Memory creation failed')

            result_tuple = await mcp.call_tool(
                'agent_memory', {'action': 'create', 'agent_name': self.test_agent_name}
            )
            result = self._extract_result(result_tuple)

            assert 'Memory Creation Error' in result
            assert 'Memory creation failed' in result

    @pytest.mark.asyncio
    async def test_agent_memory_health_action_missing_memory_id(self):
        """Test health action without memory ID."""
        mcp = self._create_mock_mcp()

        with patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True):
            result_tuple = await mcp.call_tool('agent_memory', {'action': 'health'})
            result = self._extract_result(result_tuple)

            assert 'memory_id is required' in result

    @pytest.mark.asyncio
    async def test_agent_memory_health_action_success(self):
        """Test successful health check."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryControlPlaneClient') as mock_control_client,
            patch('bedrock_agentcore.memory.MemoryClient') as mock_memory_client,
        ):
            mock_control_instance = Mock()
            mock_control_client.return_value = mock_control_instance

            mock_memory_details = {
                'status': 'ACTIVE',
                'name': 'test-memory',
                'createdAt': '2024-01-01T00:00:00Z',
                'strategies': [{'strategyType': 'semantic'}],
            }
            mock_control_instance.get_memory.return_value = mock_memory_details

            # Mock memory client for connectivity test
            mock_client_instance = Mock()
            mock_memory_client.return_value = mock_client_instance

            result_tuple = await mcp.call_tool(
                'agent_memory', {'action': 'health', 'memory_id': self.test_memory_id}
            )
            result = self._extract_result(result_tuple)

            assert 'Memory Health Check' in result
            assert 'HEALTHY' in result
            assert 'ACTIVE' in result
            assert 'test-memory' in result

    @pytest.mark.asyncio
    async def test_agent_memory_health_action_unhealthy(self):
        """Test health check for unhealthy memory."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryControlPlaneClient') as mock_control_client,
        ):
            mock_control_instance = Mock()
            mock_control_client.return_value = mock_control_instance

            mock_memory_details = {
                'status': 'CREATE_FAILED',
                'name': 'failed-memory',
                'createdAt': '2024-01-01T00:00:00Z',
                'strategies': [],
            }
            mock_control_instance.get_memory.return_value = mock_memory_details

            result_tuple = await mcp.call_tool(
                'agent_memory', {'action': 'health', 'memory_id': self.test_memory_id}
            )
            result = self._extract_result(result_tuple)

            assert 'UNHEALTHY' in result
            assert 'CREATE_FAILED' in result
            assert 'failed-memory' in result

    @pytest.mark.asyncio
    async def test_agent_memory_delete_action_missing_memory_id(self):
        """Test delete action without memory ID."""
        mcp = self._create_mock_mcp()

        with patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True):
            result_tuple = await mcp.call_tool('agent_memory', {'action': 'delete'})
            result = self._extract_result(result_tuple)

            assert 'memory_id is required' in result

    @pytest.mark.asyncio
    async def test_agent_memory_delete_action_success(self):
        """Test successful memory deletion."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryControlPlaneClient') as mock_control_client,
        ):
            mock_control_instance = Mock()
            mock_control_client.return_value = mock_control_instance

            mock_memory_details = {'name': 'test-memory-to-delete'}
            mock_control_instance.get_memory.return_value = mock_memory_details
            mock_control_instance.delete_memory.return_value = {'status': 'DELETED'}

            result_tuple = await mcp.call_tool(
                'agent_memory', {'action': 'delete', 'memory_id': self.test_memory_id}
            )
            result = self._extract_result(result_tuple)

            assert 'Memory Deleted Successfully' in result
            assert self.test_memory_id in result
            assert 'test-memory-to-delete' in result
            assert 'permanent' in result

            mock_control_instance.delete_memory.assert_called_once_with(
                memory_id=self.test_memory_id
            )

    @pytest.mark.asyncio
    async def test_agent_memory_delete_action_error(self):
        """Test delete action with error from AWS service."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryControlPlaneClient') as mock_control_client,
        ):
            mock_control_instance = Mock()
            mock_control_client.return_value = mock_control_instance
            mock_control_instance.get_memory.side_effect = Exception('Memory not found')

            result_tuple = await mcp.call_tool(
                'agent_memory', {'action': 'delete', 'memory_id': self.test_memory_id}
            )
            result = self._extract_result(result_tuple)

            assert 'Memory Deletion Error' in result
            assert 'Memory not found' in result

    @pytest.mark.asyncio
    async def test_agent_memory_import_error(self):
        """Test behavior when required modules cannot be imported."""
        mcp = self._create_mock_mcp()

        with patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True):
            with patch(
                'bedrock_agentcore.memory.MemoryControlPlaneClient',
                side_effect=ImportError('Module not found'),
            ):
                result_tuple = await mcp.call_tool('agent_memory', {'action': 'list'})
                result = self._extract_result(result_tuple)

                assert 'Memory List Error' in result or 'Module not found' in result

    @pytest.mark.asyncio
    async def test_agent_memory_general_exception(self):
        """Test general exception handling."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryControlPlaneClient') as mock_control_client,
        ):
            mock_control_client.side_effect = Exception('Unexpected error')

            result_tuple = await mcp.call_tool('agent_memory', {'action': 'list'})
            result = self._extract_result(result_tuple)

            assert 'Memory List Error' in result and 'Unexpected error' in result


class TestMemoryHelperFunctions:
    """Test memory helper functions."""

    def test_get_memory_health_recommendations_active_passed(self):
        """Test health recommendations for active memory with passed client test."""
        health_info = {'client_test': 'PASSED'}
        result = get_memory_health_recommendations('ACTIVE', health_info)

        assert 'fully operational' in result
        assert 'No action required' in result

    def test_get_memory_health_recommendations_active_failed(self):
        """Test health recommendations for active memory with failed client test."""
        health_info = {'client_test': 'FAILED'}
        result = get_memory_health_recommendations('ACTIVE', health_info)

        assert 'client connectivity has issues' in result
        assert 'Check network connectivity' in result

    def test_get_memory_health_recommendations_creating(self):
        """Test health recommendations for creating memory."""
        result = get_memory_health_recommendations('CREATING', {})

        assert 'still initializing' in result
        assert 'Wait for memory to become ACTIVE' in result

    def test_get_memory_health_recommendations_failed(self):
        """Test health recommendations for failed memory."""
        result = get_memory_health_recommendations('CREATE_FAILED', {})

        assert 'has failed and needs attention' in result
        assert 'Delete and recreate memory' in result

    def test_get_memory_health_recommendations_unknown(self):
        """Test health recommendations for unknown status."""
        result = get_memory_health_recommendations('UNKNOWN_STATUS', {})

        assert 'Unknown status' in result
        assert 'Check AWS Console' in result

    def test_get_memory_health_next_steps_healthy(self):
        """Test next steps for healthy memory."""
        result = get_memory_health_next_steps(True, 'mem-123')

        assert 'Use Memory' in result
        assert 'Integrate with agent code' in result
        assert 'Monitor' in result

    def test_get_memory_health_next_steps_unhealthy(self):
        """Test next steps for unhealthy memory."""
        result = get_memory_health_next_steps(False, 'mem-123')

        assert 'Troubleshoot' in result
        assert 'Recreate' in result
        assert 'Support' in result


class TestToolRegistration:
    """Test memory tool registration."""

    def test_register_memory_tools(self):
        """Test that memory tools are properly registered."""
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP('Test Memory Server')

        # Get initial tool count
        import asyncio

        initial_tools = asyncio.run(mcp.list_tools())
        initial_count = len(initial_tools)

        # Register memory tools
        register_memory_tools(mcp)

        # Verify tools were added
        final_tools = asyncio.run(mcp.list_tools())
        final_count = len(final_tools)

        # Should have more tools after registration
        assert final_count > initial_count

    @pytest.mark.asyncio
    async def test_memory_tools_available_in_tools_list(self):
        """Test that memory tools appear in tools list."""
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP('Test Memory Server')
        register_memory_tools(mcp)

        tools = await mcp.list_tools()
        tool_names = [tool.name for tool in tools]

        expected_tools = [
            'memory_save_conversation',
            'memory_retrieve',
            'memory_get_conversation',
            'memory_process_turn',
            'memory_list_events',
            'memory_create_event',
            'agent_memory',
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names


if __name__ == '__main__':
    import asyncio

    async def run_basic_tests():
        """Run basic tests to verify functionality."""
        print('Testing memory tool registration...')

        # Test memory tools registration
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP('Test Server')
        register_memory_tools(mcp)
        tools = await mcp.list_tools()
        print(f'✓ Memory tools registered: {len(tools)} tools')

        # Test helper functions
        health_rec = get_memory_health_recommendations('ACTIVE', {'client_test': 'PASSED'})
        print(f'✓ Health recommendations working: {len(health_rec)} chars')

        next_steps = get_memory_health_next_steps(True, 'mem-123')
        print(f'✓ Next steps working: {len(next_steps)} chars')

        print('All basic memory tests passed!')

    asyncio.run(run_basic_tests())
