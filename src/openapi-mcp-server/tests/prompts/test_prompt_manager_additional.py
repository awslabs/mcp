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

"""Additional tests for prompt manager to improve patch coverage."""

import pytest
from awslabs.openapi_mcp_server.prompts.prompt_manager import MCPPromptManager


class TestMCPPromptManagerAdditional:
    """Additional test cases for MCP prompt manager to improve coverage."""

    @pytest.fixture
    def prompt_manager(self):
        """Create a prompt manager instance."""
        return MCPPromptManager()

    def test_prompt_manager_initialization(self):
        """Test prompt manager initialization."""
        manager = MCPPromptManager()
        assert hasattr(manager, 'prompts')
        assert isinstance(manager.prompts, list)

    def test_prompt_manager_string_representation(self, prompt_manager):
        """Test string representation of prompt manager."""
        str_repr = str(prompt_manager)
        assert 'MCPPromptManager' in str_repr or 'prompt' in str_repr.lower()

    def test_prompt_manager_prompts_list(self, prompt_manager):
        """Test that prompt manager has a prompts list."""
        assert hasattr(prompt_manager, 'prompts')
        assert isinstance(prompt_manager.prompts, list)
        
        # Test adding to prompts list
        prompt_manager.prompts.append({'name': 'test', 'description': 'Test prompt'})
        assert len(prompt_manager.prompts) == 1

    def test_prompt_manager_attributes(self, prompt_manager):
        """Test prompt manager has expected attributes."""
        assert hasattr(prompt_manager, 'prompts')
        
        # Test that prompts is initially empty
        assert len(prompt_manager.prompts) == 0
        
        # Test that we can modify prompts
        test_prompt = {'name': 'test_prompt', 'description': 'A test prompt'}
        prompt_manager.prompts.append(test_prompt)
        assert test_prompt in prompt_manager.prompts

    def test_prompt_manager_multiple_instances(self):
        """Test that multiple prompt manager instances are independent."""
        manager1 = MCPPromptManager()
        manager2 = MCPPromptManager()
        
        manager1.prompts.append({'name': 'prompt1'})
        manager2.prompts.append({'name': 'prompt2'})
        
        assert len(manager1.prompts) == 1
        assert len(manager2.prompts) == 1
        assert manager1.prompts != manager2.prompts

    def test_prompt_manager_prompts_manipulation(self, prompt_manager):
        """Test various operations on the prompts list."""
        # Test empty state
        assert len(prompt_manager.prompts) == 0
        
        # Test adding multiple prompts
        prompts_to_add = [
            {'name': 'prompt1', 'description': 'First prompt'},
            {'name': 'prompt2', 'description': 'Second prompt'},
            {'name': 'prompt3', 'description': 'Third prompt'}
        ]
        
        for prompt in prompts_to_add:
            prompt_manager.prompts.append(prompt)
        
        assert len(prompt_manager.prompts) == 3
        
        # Test clearing prompts
        prompt_manager.prompts.clear()
        assert len(prompt_manager.prompts) == 0
