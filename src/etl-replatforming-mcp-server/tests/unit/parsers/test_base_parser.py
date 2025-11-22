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

"""Unit tests for base parser abstract class."""

from abc import ABC

import pytest

from awslabs.etl_replatforming_mcp_server.models.flex_workflow import FlexWorkflow
from awslabs.etl_replatforming_mcp_server.parsers.base_parser import WorkflowParser


class TestWorkflowParserAbstract:
    """Test cases for WorkflowParser abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that WorkflowParser cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            WorkflowParser()  # type: ignore

    def test_is_abstract_base_class(self):
        """Test that WorkflowParser is properly defined as ABC."""
        assert issubclass(WorkflowParser, ABC)
        assert hasattr(WorkflowParser, '__abstractmethods__')

    def test_has_required_abstract_methods(self):
        """Test that all required abstract methods are defined."""
        required_methods = {
            'parse_code',
            'detect_framework',
            'parse_metadata',
            'parse_tasks',
            'parse_schedule',
            'parse_error_handling',
            'parse_dependencies',
            'parse_loops',
            'parse_conditional_logic',
            'parse_parallel_execution',
            'validate_input',
            'get_parsing_completeness',
            'parse_task_groups',
            'parse_connections',
            'parse_trigger_rules',
            'parse_data_triggers',
        }

        abstract_methods = WorkflowParser.__abstractmethods__
        assert required_methods.issubset(abstract_methods)

    def test_concrete_implementation_works(self):
        """Test that a concrete implementation can be instantiated."""

        class ConcreteParser(WorkflowParser):
            def parse_code(self, input_code: str) -> FlexWorkflow:
                return FlexWorkflow(name='test', tasks=[])

            def detect_framework(self, input_code: str) -> bool:
                return True

            def parse_metadata(self, source_data):
                return {'name': 'test'}

            def parse_tasks(self, source_data):
                return []

            def parse_schedule(self, source_data):
                return None

            def parse_error_handling(self, source_data):
                return None

            def parse_dependencies(self, source_data):
                return []

            def parse_loops(self, source_data):
                return {}

            def parse_conditional_logic(self, source_data):
                return []

            def parse_parallel_execution(self, source_data):
                return []

            def validate_input(self, input_code: str) -> bool:
                return True

            def get_parsing_completeness(self, flex_workflow: FlexWorkflow) -> float:
                return 1.0

            def parse_task_groups(self, source_data):
                return []

            def parse_connections(self, source_data):
                return {}

            def parse_trigger_rules(self, source_data):
                return {}

            def parse_data_triggers(self, source_data):
                return []

        # Should not raise any errors
        parser = ConcreteParser()
        assert isinstance(parser, WorkflowParser)

        # Test main method works
        workflow = parser.parse_code('test code')
        assert isinstance(workflow, FlexWorkflow)
        assert workflow.name == 'test'

        # Test all methods to ensure coverage
        assert parser.detect_framework('test') is True
        assert parser.parse_metadata({}) == {'name': 'test'}
        assert parser.parse_tasks({}) == []
        assert parser.parse_schedule({}) is None
        assert parser.parse_error_handling({}) is None
        assert parser.parse_dependencies({}) == []
        assert parser.parse_loops({}) == {}
        assert parser.parse_conditional_logic({}) == []
        assert parser.parse_parallel_execution({}) == []
        assert parser.validate_input('test') is True
        assert parser.get_parsing_completeness(workflow) == 1.0
        assert parser.parse_task_groups({}) == []
        assert parser.parse_connections({}) == {}
        assert parser.parse_trigger_rules({}) == {}
        assert parser.parse_data_triggers({}) == []

    def test_incomplete_implementation_fails(self):
        """Test that incomplete implementation cannot be instantiated."""

        class IncompleteParser(WorkflowParser):
            def parse_code(self, input_code: str) -> FlexWorkflow:
                return FlexWorkflow(name='test', tasks=[])

            # Missing other required methods

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteParser()  # type: ignore
