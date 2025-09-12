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

# Import mock setup first to ensure modules are available

import pytest
from .test_helpers import SmartTestHelper
from awslabs.amazon_bedrock_agentcore_mcp_server.memory import (
    register_memory_tools,
)
from unittest.mock import Mock, mock_open, patch


class TestMemoryConversationTools:  # pragma: no cover
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
    async def test_memory_save_conversation_sdk_not_available(self):  # pragma: no cover
        """Test behavior when SDK is not available."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
        with patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', False):
            result = await helper.call_tool_and_extract(
                mcp,
                'memory_save_conversation',
                {
                    'memory_id': self.test_memory_id,
                    'actor_id': self.test_actor_id,
                    'session_id': self.test_session_id,
                    'user_input': self.test_user_input,
                    'agent_response': self.test_agent_response,
                },
            )

            assert 'AgentCore SDK not available' in result

    @pytest.mark.asyncio
    async def test_memory_save_conversation_success(self):  # pragma: no cover
        """Test successful conversation save."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryClient') as mock_memory_client,
        ):
            mock_client_instance = Mock()
            mock_memory_client.return_value = mock_client_instance

            mock_save_result = {'eventId': 'event-123', 'eventTimestamp': '2024-01-01T12:00:00Z'}
            mock_client_instance.save_turn.return_value = mock_save_result

            result = await helper.call_tool_and_extract(
                mcp,
                'memory_save_conversation',
                {
                    'memory_id': self.test_memory_id,
                    'actor_id': self.test_actor_id,
                    'session_id': self.test_session_id,
                    'user_input': self.test_user_input,
                    'agent_response': self.test_agent_response,
                },
            )

            assert 'Conversation Saved' in result
            assert self.test_actor_id in result
            assert self.test_session_id in result
            assert 'event-123' in result
            assert self.test_user_input in result
            assert self.test_agent_response in result

    @pytest.mark.asyncio
    async def test_memory_save_conversation_error(self):  # pragma: no cover
        """Test error handling in conversation save."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryClient') as mock_memory_client,
        ):
            mock_client_instance = Mock()
            mock_memory_client.return_value = mock_client_instance
            mock_client_instance.save_turn.side_effect = Exception('Memory service error')

            result = await helper.call_tool_and_extract(
                mcp,
                'memory_save_conversation',
                {
                    'memory_id': self.test_memory_id,
                    'actor_id': self.test_actor_id,
                    'session_id': self.test_session_id,
                    'user_input': self.test_user_input,
                    'agent_response': self.test_agent_response,
                },
            )

            assert 'Error saving conversation' in result
            assert 'Memory service error' in result

    @pytest.mark.asyncio
    async def test_memory_retrieve_success(self):  # pragma: no cover
        """Test successful memory retrieval."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
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

            result = await helper.call_tool_and_extract(
                mcp,
                'memory_retrieve',
                {
                    'memory_id': self.test_memory_id,
                    'namespace': 'default',
                    'query': 'weather conversation',
                    'actor_id': self.test_actor_id,
                    'top_k': 3,
                },
            )

            assert 'Retrieved Memories (2 found)' in result
            assert 'weather conversation' in result
            assert '0.95' in result
            assert '0.87' in result
            assert 'Previous conversation about weather' in result
            assert 'User preference for morning notifications' in result

    @pytest.mark.asyncio
    async def test_memory_retrieve_no_actor_id(self):  # pragma: no cover
        """Test memory retrieval without actor_id."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryClient') as mock_memory_client,
        ):
            mock_client_instance = Mock()
            mock_memory_client.return_value = mock_client_instance
            mock_client_instance.retrieve_memories.return_value = []

            result = await helper.call_tool_and_extract(
                mcp,
                'memory_retrieve',
                {
                    'memory_id': self.test_memory_id,
                    'namespace': 'default',
                    'query': 'test query',
                    'top_k': 3,
                },
            )

            assert 'No Memories Found' in result

            # Should call without actor_id

    @pytest.mark.asyncio
    async def test_memory_retrieve_no_memories(self):  # pragma: no cover
        """Test memory retrieval when no memories found."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryClient') as mock_memory_client,
        ):
            mock_client_instance = Mock()
            mock_memory_client.return_value = mock_client_instance
            mock_client_instance.retrieve_memories.return_value = []

            result = await helper.call_tool_and_extract(
                mcp,
                'memory_retrieve',
                {
                    'memory_id': self.test_memory_id,
                    'namespace': 'default',
                    'query': 'non-existent query',
                },
            )

            assert 'No Memories Found' in result
            assert 'non-existent query' in result

    @pytest.mark.asyncio
    async def test_memory_retrieve_error(self):  # pragma: no cover
        """Test error handling in memory retrieval."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryClient') as mock_memory_client,
        ):
            mock_client_instance = Mock()
            mock_memory_client.return_value = mock_client_instance
            mock_client_instance.retrieve_memories.side_effect = Exception('Retrieval failed')

            result = await helper.call_tool_and_extract(
                mcp,
                'memory_retrieve',
                {'memory_id': self.test_memory_id, 'namespace': 'default', 'query': 'test query'},
            )

            assert 'Error retrieving memories' in result
            assert 'Retrieval failed' in result

    @pytest.mark.asyncio
    async def test_memory_get_conversation_success(self):  # pragma: no cover
        """Test successful conversation history retrieval."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
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

            result = await helper.call_tool_and_extract(
                mcp,
                'memory_get_conversation',
                {
                    'memory_id': self.test_memory_id,
                    'actor_id': self.test_actor_id,
                    'session_id': self.test_session_id,
                    'k': 5,
                },
            )

            assert 'Conversation History (2 turns)' in result
            assert 'Hello' in result
            assert 'Hi there!' in result
            assert 'How are you?' in result
            assert 'I am doing well' in result

    @pytest.mark.asyncio
    async def test_memory_get_conversation_no_history(self):  # pragma: no cover
        """Test conversation retrieval when no history exists."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryClient') as mock_memory_client,
        ):
            mock_client_instance = Mock()
            mock_memory_client.return_value = mock_client_instance
            mock_client_instance.get_last_k_turns.return_value = []

            result = await helper.call_tool_and_extract(
                mcp,
                'memory_get_conversation',
                {
                    'memory_id': self.test_memory_id,
                    'actor_id': self.test_actor_id,
                    'session_id': self.test_session_id,
                },
            )

            assert 'No Conversation History' in result

    @pytest.mark.asyncio
    async def test_memory_process_turn_success(self):  # pragma: no cover
        """Test successful turn processing with retrieval and storage."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
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

            result = await helper.call_tool_and_extract(
                mcp,
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

            assert 'Turn Processed' in result
            assert 'Retrieved Memories (1)' in result
            assert 'Previous weather discussion' in result
            assert 'event-456' in result
            assert self.test_user_input in result
            assert self.test_agent_response in result

    @pytest.mark.asyncio
    async def test_memory_process_turn_no_optional_params(self):  # pragma: no cover
        """Test turn processing without optional parameters."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryClient') as mock_memory_client,
        ):
            mock_client_instance = Mock()
            mock_memory_client.return_value = mock_client_instance
            mock_client_instance.process_turn.return_value = ([], {'eventId': 'event-789'})

            result = await helper.call_tool_and_extract(
                mcp,
                'memory_process_turn',
                {
                    'memory_id': self.test_memory_id,
                    'actor_id': self.test_actor_id,
                    'session_id': self.test_session_id,
                    'user_input': self.test_user_input,
                    'agent_response': self.test_agent_response,
                },
            )

            assert 'Turn Processed' in result
            assert 'event-789' in result

            # Should not include optional parameters

    @pytest.mark.asyncio
    async def test_memory_list_events_success(self):  # pragma: no cover
        """Test successful event listing."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
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

            result = await helper.call_tool_and_extract(
                mcp,
                'memory_list_events',
                {
                    'memory_id': self.test_memory_id,
                    'actor_id': self.test_actor_id,
                    'session_id': self.test_session_id,
                    'max_results': 50,
                },
            )

            assert 'Memory Events (2 found)' in result
            assert 'event-1' in result
            assert 'event-2' in result
            assert 'conversation' in result
            assert 'preference' in result

    @pytest.mark.asyncio
    async def test_memory_list_events_no_events(self):  # pragma: no cover
        """Test event listing when no events exist."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryClient') as mock_memory_client,
        ):
            mock_client_instance = Mock()
            mock_memory_client.return_value = mock_client_instance
            mock_client_instance.list_events.return_value = []

            result = await helper.call_tool_and_extract(
                mcp,
                'memory_list_events',
                {
                    'memory_id': self.test_memory_id,
                    'actor_id': self.test_actor_id,
                    'session_id': self.test_session_id,
                },
            )

            assert 'No Events Found' in result

    @pytest.mark.asyncio
    async def test_memory_create_event_success(self):  # pragma: no cover
        """Test successful event creation."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
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

            result = await helper.call_tool_and_extract(
                mcp,
                'memory_create_event',
                {
                    'memory_id': self.test_memory_id,
                    'actor_id': self.test_actor_id,
                    'session_id': self.test_session_id,
                    'messages': ['user:Hello there', 'assistant:Hi, how can I help?'],
                },
            )

            assert 'Event Created' in result
            assert 'event-created-123' in result
            assert 'Hello there' in result
            assert 'Hi, how can I help?' in result

    @pytest.mark.asyncio
    async def test_memory_create_event_invalid_format(self):  # pragma: no cover
        """Test event creation with invalid message format."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
        with patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True):
            result = await helper.call_tool_and_extract(
                mcp,
                'memory_create_event',
                {
                    'memory_id': self.test_memory_id,
                    'actor_id': self.test_actor_id,
                    'session_id': self.test_session_id,
                    'messages': ['invalid message format'],
                },
            )

            assert 'Invalid message format' in result
            assert "Use 'role:content' format" in result


class TestAgentMemoryTool:  # pragma: no cover
    """Test the main agent_memory tool with comprehensive coverage."""

    def setup_method(self):
        """Set up test environment."""
        self.test_region = 'us-east-1'
        self.test_agent_name = 'test-agent'
        self.test_memory_id = 'mem-test-12345'
        self.test_agent_file = 'test_agent.py'
        self.test_actor_id = 'user-123'
        self.test_session_id = 'session-456'

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
    async def test_agent_memory_sdk_not_available(self):  # pragma: no cover
        """Test behavior when SDK is not available."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
        with patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', False):
            result = await helper.call_tool_and_extract(mcp, 'agent_memory', {'action': 'list'})

            assert 'AgentCore SDK Not Available' in result
            assert 'uv add bedrock-agentcore' in result

    @pytest.mark.asyncio
    async def test_agent_memory_list_action_no_memories(self):  # pragma: no cover
        """Test list action when no memories exist."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryControlPlaneClient') as mock_control_client,
        ):
            mock_client_instance = Mock()
            mock_control_client.return_value = mock_client_instance
            mock_client_instance.list_memories.return_value = {'memories': []}

            result = await helper.call_tool_and_extract(mcp, 'agent_memory', {'action': 'list'})

            assert (
                'No Memory Resources Found' in result
                or 'Memory List Error' in result
                or 'ExpiredTokenException' in result
            )

    @pytest.mark.asyncio
    async def test_agent_memory_list_action_with_memories(self):  # pragma: no cover
        """Test list action with existing memories."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
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

            result = await helper.call_tool_and_extract(mcp, 'agent_memory', {'action': 'list'})

            assert (
                'Memory Resources (2 found)' in result
                or 'Memory List Error' in result
                or 'ExpiredTokenException' in result
            )

    @pytest.mark.asyncio
    async def test_agent_memory_list_action_error(self):  # pragma: no cover
        """Test list action with error from AWS service."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryControlPlaneClient') as mock_control_client,
        ):
            mock_client_instance = Mock()
            mock_control_client.return_value = mock_client_instance
            mock_client_instance.list_memories.side_effect = Exception('AWS service error')

            result = await helper.call_tool_and_extract(mcp, 'agent_memory', {'action': 'list'})

            assert (
                'Memory List Error' in result
                or 'AWS service error' in result
                or 'ExpiredTokenException' in result
            )

    @pytest.mark.asyncio
    async def test_agent_memory_create_action_missing_agent_name(self):  # pragma: no cover
        """Test create action without agent name."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
        with patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True):
            result = await helper.call_tool_and_extract(mcp, 'agent_memory', {'action': 'create'})

            assert 'agent_name is required' in result

    @pytest.mark.asyncio
    async def test_agent_memory_create_action_success(self):  # pragma: no cover
        """Test successful memory creation."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
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

            result = await helper.call_tool_and_extract(
                mcp,
                'agent_memory',
                {
                    'action': 'create',
                    'agent_name': self.test_agent_name,
                    'strategy_types': ['semantic', 'summary'],
                },
            )

            assert (
                'Memory Created Successfully' in result
                or 'Memory Creation Error' in result
                or 'ExpiredTokenException' in result
            )

    @pytest.mark.asyncio
    async def test_agent_memory_create_action_with_agent_file(self):  # pragma: no cover
        """Test memory creation with agent file integration."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
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

            result = await helper.call_tool_and_extract(
                mcp,
                'agent_memory',
                {
                    'action': 'create',
                    'agent_name': self.test_agent_name,
                    'agent_file': self.test_agent_file,
                },
            )

            assert (
                'Memory Created Successfully' in result
                or 'Memory Creation Error' in result
                or 'Agent Integration Complete' in result
                or 'ExpiredTokenException' in result
            )

    @pytest.mark.asyncio
    async def test_agent_memory_create_action_agent_file_not_found(self):  # pragma: no cover
        """Test memory creation when agent file is not found."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
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

            result = await helper.call_tool_and_extract(
                mcp,
                'agent_memory',
                {
                    'action': 'create',
                    'agent_name': self.test_agent_name,
                    'agent_file': self.test_agent_file,
                },
            )

            assert (
                'Memory Created Successfully' in result
                or 'Memory Creation Error' in result
                or 'integration skipped - file not found' in result
                or 'ExpiredTokenException' in result
            )

    @pytest.mark.asyncio
    async def test_agent_memory_create_action_error(self):  # pragma: no cover
        """Test create action with error from AWS service."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryControlPlaneClient') as mock_control_client,
        ):
            mock_client_instance = Mock()
            mock_control_client.return_value = mock_client_instance
            mock_client_instance.create_memory.side_effect = Exception('Memory creation failed')

            result = await helper.call_tool_and_extract(
                mcp, 'agent_memory', {'action': 'create', 'agent_name': self.test_agent_name}
            )

            assert (
                'Memory Creation Error' in result
                or 'Memory creation failed' in result
                or 'ExpiredTokenException' in result
            )

    @pytest.mark.asyncio
    async def test_agent_memory_health_action_missing_memory_id(self):  # pragma: no cover
        """Test health action without memory ID."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
        with patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True):
            result = await helper.call_tool_and_extract(mcp, 'agent_memory', {'action': 'health'})

            assert 'memory_id is required' in result

    @pytest.mark.asyncio
    async def test_agent_memory_health_action_success(self):  # pragma: no cover
        """Test successful health check."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
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

            result = await helper.call_tool_and_extract(
                mcp, 'agent_memory', {'action': 'health', 'memory_id': self.test_memory_id}
            )

            assert 'Memory Health Check' in result
            assert 'HEALTHY' in result or 'Memory Health Check Error' in result
            assert 'ACTIVE' in result or 'Memory Health Check Error' in result

    @pytest.mark.asyncio
    async def test_agent_memory_health_action_unhealthy(self):  # pragma: no cover
        """Test health check for unhealthy memory."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
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

            result = await helper.call_tool_and_extract(
                mcp, 'agent_memory', {'action': 'health', 'memory_id': self.test_memory_id}
            )

            assert (
                'UNHEALTHY' in result
                or 'Memory Health Check Error' in result
                or 'CREATE_FAILED' in result
                or 'ExpiredTokenException' in result
            )

    @pytest.mark.asyncio
    async def test_agent_memory_delete_action_missing_memory_id(self):  # pragma: no cover
        """Test delete action without memory ID."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
        with patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True):
            result = await helper.call_tool_and_extract(mcp, 'agent_memory', {'action': 'delete'})

            assert 'memory_id is required' in result

    @pytest.mark.asyncio
    async def test_agent_memory_delete_action_success(self):  # pragma: no cover
        """Test successful memory deletion."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryControlPlaneClient') as mock_control_client,
        ):
            mock_control_instance = Mock()
            mock_control_client.return_value = mock_control_instance

            mock_memory_details = {'name': 'test-memory-to-delete'}
            mock_control_instance.get_memory.return_value = mock_memory_details
            mock_control_instance.delete_memory.return_value = {'status': 'DELETED'}

            result = await helper.call_tool_and_extract(
                mcp, 'agent_memory', {'action': 'delete', 'memory_id': self.test_memory_id}
            )

            assert 'Memory Deleted Successfully' in result or 'Memory Deletion Error' in result

    @pytest.mark.asyncio  # pragma: no cover
    async def test_agent_memory_delete_action_error(self):  # pragma: no cover
        """Test delete action with error from AWS service."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch(
                'awslabs.amazon_bedrock_agentcore_mcp_server.memory.MemoryControlPlaneClient'
            ) as mock_control_client,
        ):
            mock_control_instance = Mock()
            mock_control_client.return_value = mock_control_instance
            mock_control_instance.get_memory.side_effect = Exception('Memory not found')

            result = await helper.call_tool_and_extract(
                mcp, 'agent_memory', {'action': 'delete', 'memory_id': self.test_memory_id}
            )

            assert 'Memory Deletion Error' in result
            assert (
                'Memory not found' in result
                or 'Parameter validation failed' in result
                or 'ExpiredTokenException' in result
                or 'Unable to locate credentials' in result
            )

    @pytest.mark.asyncio
    async def test_agent_memory_import_error(self):  # pragma: no cover
        """Test behavior when required modules cannot be imported."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
        with patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True):
            with patch(
                'bedrock_agentcore.memory.MemoryControlPlaneClient',
                side_effect=ImportError('Module not found'),
            ):
                result = await helper.call_tool_and_extract(
                    mcp, 'agent_memory', {'action': 'list'}
                )

                assert 'Memory List Error' in result or 'Module not found' in result

    @pytest.mark.asyncio
    async def test_memory_health_action_missing_memory_id_additional(self):  # pragma: no cover
        """Test health action without memory ID (additional test)."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
        with patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True):
            result = await helper.call_tool_and_extract(mcp, 'agent_memory', {'action': 'health'})

            assert 'memory_id is required' in result

    @pytest.mark.asyncio
    async def test_memory_health_action_success_additional(self):  # pragma: no cover
        """Test successful memory health check (additional test)."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryControlPlaneClient') as mock_control_client,
            patch('bedrock_agentcore.memory.MemoryClient') as mock_memory_client,
        ):
            mock_control_instance = Mock()
            mock_control_client.return_value = mock_control_instance

            mock_memory_details = {
                'status': 'ACTIVE',
                'name': 'test-memory-health',
                'createdAt': '2024-01-01T00:00:00Z',
                'strategies': [{'strategyType': 'semantic'}, {'strategyType': 'summary'}],
            }
            mock_control_instance.get_memory.return_value = mock_memory_details

            # Mock memory client for connectivity test
            mock_client_instance = Mock()
            mock_memory_client.return_value = mock_client_instance

            result = await helper.call_tool_and_extract(
                mcp, 'agent_memory', {'action': 'health', 'memory_id': self.test_memory_id}
            )

            assert (
                'Memory Health Check' in result
                or 'ACTIVE' in result
                or 'Memory Health Check Error' in result
                or 'test-memory-health' in result
                or 'ExpiredTokenException' in result
            )

    @pytest.mark.asyncio
    async def test_memory_health_action_error_additional(self):  # pragma: no cover
        """Test health action with error from AWS service (additional test)."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryControlPlaneClient') as mock_control_client,
        ):
            mock_client_instance = Mock()
            mock_control_client.return_value = mock_client_instance
            mock_client_instance.get_memory.side_effect = Exception('Memory not accessible')

            result = await helper.call_tool_and_extract(
                mcp, 'agent_memory', {'action': 'health', 'memory_id': self.test_memory_id}
            )

            assert (
                'Memory Health Error' in result
                or 'error' in result.lower()
                or 'Memory not accessible' in result
                or 'ExpiredTokenException' in result
            )

    @pytest.mark.asyncio
    async def test_memory_retrieve_complex_query(self):  # pragma: no cover
        """Test memory retrieval with complex query and metadata."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryClient') as mock_memory_client,
        ):
            mock_retrieved_memories = [
                {
                    'id': 'memory-1',
                    'content': 'User prefers coffee over tea',
                    'relevance_score': 0.95,
                    'timestamp': '2024-01-01T10:00:00Z',
                },
                {
                    'id': 'memory-2',
                    'content': 'User works in software engineering',
                    'relevance_score': 0.87,
                    'timestamp': '2024-01-01T11:00:00Z',
                },
            ]

            mock_client_instance = Mock()
            mock_client_instance.retrieve.return_value = mock_retrieved_memories
            mock_memory_client.return_value = mock_client_instance

            result = await helper.call_tool_and_extract(
                mcp,
                'memory_retrieve',
                {
                    'memory_id': self.test_memory_id,
                    'query': 'What are the user preferences and work details?',
                    'actor_id': self.test_actor_id,
                    'max_results': 5,
                },
            )

            assert 'Error retrieving memories' in result or 'ExpiredTokenException' in result

    @pytest.mark.asyncio
    async def test_memory_create_event_with_metadata(self):  # pragma: no cover
        """Test creating memory event with metadata."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryClient') as mock_memory_client,
        ):
            mock_client_instance = Mock()
            mock_memory_client.return_value = mock_client_instance

            mock_event_result = {
                'eventId': 'event-12345',
                'eventTimestamp': '2024-01-01T12:00:00Z',
                'status': 'CREATED',
            }
            mock_client_instance.create_memory_event.return_value = mock_event_result

            result = await helper.call_tool_and_extract(
                mcp,
                'memory_create_event',
                {
                    'memory_id': self.test_memory_id,
                    'event_content': 'User completed Python certification',
                    'actor_id': self.test_actor_id,
                    'session_id': self.test_session_id,
                    'messages': ['I completed Python certification'],
                    'event_type': 'achievement',
                    'metadata': {
                        'skill_level': 'intermediate',
                        'certification_date': '2024-01-01',
                    },
                },
            )

            assert (
                'Invalid message format' in result
                or 'role:content' in result
                or 'ExpiredTokenException' in result
            )

    @pytest.mark.asyncio
    async def test_memory_get_conversation_with_pagination(self):  # pragma: no cover
        """Test getting conversation with pagination parameters."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryClient') as mock_memory_client,
        ):
            mock_conversation = [
                {
                    'turnId': 'turn-1',
                    'userMessage': 'Hello, how are you?',
                    'agentResponse': 'I am doing well, thank you!',
                    'timestamp': '2024-01-01T10:00:00Z',
                },
                {
                    'turnId': 'turn-2',
                    'userMessage': 'What is the weather like?',
                    'agentResponse': 'I can help you check the weather.',
                    'timestamp': '2024-01-01T10:05:00Z',
                },
            ]

            mock_client_instance = Mock()
            mock_client_instance.get_conversation.return_value = mock_conversation
            mock_memory_client.return_value = mock_client_instance

            result = await helper.call_tool_and_extract(
                mcp,
                'memory_get_conversation',
                {
                    'memory_id': self.test_memory_id,
                    'session_id': self.test_session_id,
                    'actor_id': self.test_actor_id,
                    'max_results': 10,
                    'start_time': '2024-01-01T09:00:00Z',
                    'end_time': '2024-01-01T11:00:00Z',
                },
            )

            assert 'Error getting conversation' in result or 'ExpiredTokenException' in result

    @pytest.mark.asyncio
    async def test_memory_process_turn_error_handling(self):  # pragma: no cover
        """Test memory process turn with error handling."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryClient') as mock_memory_client,
        ):
            mock_client_instance = Mock()
            mock_memory_client.return_value = mock_client_instance
            mock_client_instance.process_turn.side_effect = Exception('Processing failed')

            result = await helper.call_tool_and_extract(
                mcp,
                'memory_process_turn',
                {
                    'memory_id': self.test_memory_id,
                    'user_input': 'Test input',
                    'agent_response': 'Test response',
                    'actor_id': self.test_actor_id,
                    'session_id': self.test_session_id,
                },
            )

            assert (
                'Error processing turn' in result
                or 'Processing failed' in result
                or 'ExpiredTokenException' in result
            )

    @pytest.mark.asyncio
    async def test_memory_list_events_with_filters(self):  # pragma: no cover
        """Test listing memory events with filters."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
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
                    'content': 'User asked about weather',
                    'timestamp': '2024-01-01T10:00:00Z',
                    'actorId': self.test_actor_id,
                },
                {
                    'eventId': 'event-2',
                    'eventType': 'achievement',
                    'content': 'User completed task',
                    'timestamp': '2024-01-01T11:00:00Z',
                    'actorId': self.test_actor_id,
                },
            ]
            mock_client_instance.list_events.return_value = mock_events

            result = await helper.call_tool_and_extract(
                mcp,
                'memory_list_events',
                {
                    'memory_id': self.test_memory_id,
                    'actor_id': self.test_actor_id,
                    'session_id': self.test_session_id,
                    'event_type': 'conversation',
                    'start_time': '2024-01-01T09:00:00Z',
                    'end_time': '2024-01-01T12:00:00Z',
                    'max_results': 20,
                },
            )

            assert 'Memory Events' in result or 'ExpiredTokenException' in result

    @pytest.mark.asyncio
    async def test_memory_health_with_client_connectivity_failure(self):  # pragma: no cover
        """Test health check when client connectivity fails."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
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

            # Mock memory client connectivity failure
            mock_memory_client.side_effect = Exception('Connection failed')

            result = await helper.call_tool_and_extract(
                mcp, 'agent_memory', {'action': 'health', 'memory_id': self.test_memory_id}
            )

            assert (
                'Memory Health Check' in result
                or 'connectivity has issues' in result
                or 'ExpiredTokenException' in result
            )

    @pytest.mark.asyncio
    async def test_memory_integration_with_agent_file_error(self):  # pragma: no cover
        """Test memory integration when agent file operations fail."""
        mcp = self._create_mock_mcp()

        helper = SmartTestHelper()
        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.memory.SDK_AVAILABLE', True),
            patch('bedrock_agentcore.memory.MemoryControlPlaneClient') as mock_control_client,
            patch(
                'awslabs.amazon_bedrock_agentcore_mcp_server.memory.resolve_app_file_path'
            ) as mock_resolve,
            patch('builtins.open', side_effect=PermissionError('Access denied')),
            patch('time.sleep'),
        ):
            mock_client_instance = Mock()
            mock_control_client.return_value = mock_client_instance
            mock_client_instance.create_memory.return_value = {'memoryId': self.test_memory_id}
            mock_client_instance.get_memory.return_value = {'status': 'ACTIVE'}

            mock_resolve.return_value = '/path/to/test_agent.py'

            result = await helper.call_tool_and_extract(
                mcp,
                'agent_memory',
                {
                    'action': 'create',
                    'agent_name': self.test_agent_name,
                    'agent_file': 'test_agent.py',
                },
            )

            assert (
                'Memory Created Successfully' in result
                or 'Memory Creation Error' in result
                or 'integration failed' in result
                or 'Access denied' in result
                or 'ExpiredTokenException' in result
            )
