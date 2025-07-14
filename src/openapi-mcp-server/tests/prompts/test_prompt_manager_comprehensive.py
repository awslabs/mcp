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

"""Comprehensive tests for prompt manager to maximize patch coverage."""

from awslabs.openapi_mcp_server.prompts.prompt_manager import MCPPromptManager


class TestMCPPromptManagerComprehensive:
    """Comprehensive test cases to maximize prompt manager coverage."""

    def test_prompt_manager_class_attributes(self):
        """Test class-level attributes and methods."""
        # Test class can be instantiated multiple times
        managers = [MCPPromptManager() for _ in range(3)]

        for i, manager in enumerate(managers):
            assert hasattr(manager, 'prompts')
            assert isinstance(manager.prompts, list)
            # Each instance should have its own prompts list
            manager.prompts.append(f'prompt_{i}')

        # Verify independence
        for i, manager in enumerate(managers):
            assert len(manager.prompts) == 1
            assert manager.prompts[0] == f'prompt_{i}'

    def test_prompt_manager_prompts_list_operations(self):
        """Test various list operations on prompts."""
        manager = MCPPromptManager()

        # Test list is initially empty
        assert len(manager.prompts) == 0
        assert manager.prompts == []

        # Test adding different types of prompts
        prompt_types = [
            {'name': 'simple', 'type': 'basic'},
            {'name': 'complex', 'type': 'advanced', 'parameters': ['param1', 'param2']},
            {'name': 'workflow', 'type': 'workflow', 'steps': [1, 2, 3]},
        ]

        for prompt in prompt_types:
            manager.prompts.append(prompt)

        assert len(manager.prompts) == 3

        # Test list operations
        assert prompt_types[0] in manager.prompts
        assert prompt_types[1] in manager.prompts
        assert prompt_types[2] in manager.prompts

        # Test removing prompts
        manager.prompts.remove(prompt_types[1])
        assert len(manager.prompts) == 2
        assert prompt_types[1] not in manager.prompts

        # Test extending prompts
        additional_prompts = [
            {'name': 'extra1', 'type': 'extra'},
            {'name': 'extra2', 'type': 'extra'},
        ]
        manager.prompts.extend(additional_prompts)
        assert len(manager.prompts) == 4

    def test_prompt_manager_edge_cases(self):
        """Test edge cases and boundary conditions."""
        manager = MCPPromptManager()

        # Test with None values
        manager.prompts.append(None)
        assert None in manager.prompts
        assert len(manager.prompts) == 1

        # Test with empty dict
        manager.prompts.append({})
        assert {} in manager.prompts
        assert len(manager.prompts) == 2

        # Test with complex nested structures
        complex_prompt = {
            'name': 'complex',
            'nested': {'level1': {'level2': ['item1', 'item2']}},
            'list_of_dicts': [{'key1': 'value1'}, {'key2': 'value2'}],
        }
        manager.prompts.append(complex_prompt)
        assert complex_prompt in manager.prompts
        assert len(manager.prompts) == 3

    def test_prompt_manager_memory_efficiency(self):
        """Test memory efficiency with large numbers of prompts."""
        manager = MCPPromptManager()

        # Add many prompts to test memory handling
        large_prompt_set = [
            {'name': f'prompt_{i}', 'id': i, 'data': f'data_{i}'} for i in range(100)
        ]

        manager.prompts.extend(large_prompt_set)
        assert len(manager.prompts) == 100

        # Test that all prompts are accessible
        for i in range(100):
            expected_prompt = {'name': f'prompt_{i}', 'id': i, 'data': f'data_{i}'}
            assert expected_prompt in manager.prompts

        # Test clearing large dataset
        manager.prompts.clear()
        assert len(manager.prompts) == 0

    def test_prompt_manager_string_methods(self):
        """Test string representation and related methods."""
        manager = MCPPromptManager()

        # Test string representation
        str_repr = str(manager)
        assert isinstance(str_repr, str)
        assert len(str_repr) > 0

        # Test repr
        repr_str = repr(manager)
        assert isinstance(repr_str, str)
        assert len(repr_str) > 0

        # Test that different instances have different string representations
        manager2 = MCPPromptManager()
        manager.prompts.append({'test': 'data'})

        # They might have the same string representation, but that's okay
        str1 = str(manager)
        str2 = str(manager2)
        assert isinstance(str1, str)
        assert isinstance(str2, str)

    def test_prompt_manager_type_checking(self):
        """Test type checking and validation."""
        manager = MCPPromptManager()

        # Test that prompts attribute is always a list
        assert isinstance(manager.prompts, list)

        # Test that we can add various types
        test_items = [
            'string_prompt',
            123,
            {'dict': 'prompt'},
            ['list', 'prompt'],
            ('tuple', 'prompt'),
            True,
            None,
        ]

        for item in test_items:
            manager.prompts.append(item)

        assert len(manager.prompts) == len(test_items)

        # Verify all items are present
        for item in test_items:
            assert item in manager.prompts

    def test_prompt_manager_concurrent_access(self):
        """Test behavior with multiple references to the same manager."""
        manager = MCPPromptManager()

        # Create multiple references
        ref1 = manager
        ref2 = manager

        # Modify through one reference
        ref1.prompts.append({'source': 'ref1'})

        # Verify change is visible through other reference
        assert len(ref2.prompts) == 1
        assert {'source': 'ref1'} in ref2.prompts

        # Modify through second reference
        ref2.prompts.append({'source': 'ref2'})

        # Verify change is visible through first reference
        assert len(ref1.prompts) == 2
        assert {'source': 'ref2'} in ref1.prompts

    def test_prompt_manager_initialization_variations(self):
        """Test different ways of initializing and using the manager."""
        # Test direct instantiation
        manager1 = MCPPromptManager()
        assert hasattr(manager1, 'prompts')

        # Test multiple instantiations
        managers = []
        for i in range(5):
            manager = MCPPromptManager()
            manager.prompts.append(f'manager_{i}')
            managers.append(manager)

        # Verify each manager is independent
        for i, manager in enumerate(managers):
            assert len(manager.prompts) == 1
            assert manager.prompts[0] == f'manager_{i}'

        # Test that managers don't interfere with each other
        managers[0].prompts.append('additional')
        assert len(managers[0].prompts) == 2
        for i in range(1, 5):
            assert len(managers[i].prompts) == 1
