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

"""Unit tests for base generator abstract class."""

from abc import ABC

import pytest

from awslabs.etl_replatforming_mcp_server.generators.base_generator import BaseGenerator
from awslabs.etl_replatforming_mcp_server.models.flex_workflow import (
    FlexWorkflow,
    TaskGroup,
)
from awslabs.etl_replatforming_mcp_server.models.llm_config import LLMConfig


class TestBaseGeneratorAbstract:
    """Test cases for BaseGenerator abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that BaseGenerator cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseGenerator()  # type: ignore

    def test_is_abstract_base_class(self):
        """Test that BaseGenerator is properly defined as ABC."""
        assert issubclass(BaseGenerator, ABC)
        assert hasattr(BaseGenerator, '__abstractmethods__')

    def test_has_required_abstract_methods(self):
        """Test that all required abstract methods are defined."""
        required_methods = {
            'generate',
            'get_supported_task_types',
            'supports_feature',
            'generate_metadata',
            'generate_schedule',
            'generate_task',
            'generate_dependencies',
            'generate_error_handling',
            'generate_conditional_logic',
            'generate_loop_logic',
            'generate_parallel_execution',
            'format_output',
            'validate_generated_output',
        }

        abstract_methods = BaseGenerator.__abstractmethods__
        assert required_methods.issubset(abstract_methods)

    def test_concrete_implementation_works(self):
        """Test that a concrete implementation can be instantiated."""

        class ConcreteGenerator(BaseGenerator):
            def generate(self, workflow, context_document=None, llm_config=None):
                return {'content': 'generated', 'framework': 'test'}

            def get_supported_task_types(self):
                return ['bash', 'python']

            def supports_feature(self, feature):
                return feature in ['error_handling']

            def generate_metadata(self, workflow):
                return {'name': workflow.name}

            def generate_schedule(self, schedule):
                return {'cron': '0 0 * * *'}

            def generate_task(self, task, workflow):
                return {'id': task.id, 'type': task.type}

            def generate_dependencies(self, tasks):
                return []

            def generate_error_handling(self, error_handling):
                return {'retry': 3}

            def generate_conditional_logic(self, task, workflow):
                return None

            def generate_loop_logic(self, task, workflow):
                return None

            def generate_parallel_execution(self, tasks, workflow):
                return None

            def format_output(self, generated_content, workflow):
                return {'content': generated_content, 'framework': 'test'}

            def validate_generated_output(self, output):
                return 'content' in output

        # Should not raise any errors
        generator = ConcreteGenerator()
        assert isinstance(generator, BaseGenerator)

        # Test main method works
        workflow = FlexWorkflow(name='test', tasks=[])
        result = generator.generate(workflow)
        assert result['content'] == 'generated'

        # Test all methods to ensure coverage
        from awslabs.etl_replatforming_mcp_server.models.flex_workflow import Task

        test_task = Task(id='test_task', name='Test Task', type='bash')

        assert generator.get_supported_task_types() == ['bash', 'python']
        assert generator.supports_feature('error_handling') is True
        assert generator.supports_feature('other') is False
        assert generator.generate_metadata(workflow) == {'name': 'test'}
        assert generator.generate_schedule(None) == {'cron': '0 0 * * *'}
        assert generator.generate_task(test_task, workflow) == {'id': 'test_task', 'type': 'bash'}
        assert generator.generate_dependencies([]) == []
        assert generator.generate_error_handling(None) == {'retry': 3}
        assert generator.generate_conditional_logic(None, workflow) is None
        assert generator.generate_loop_logic(None, workflow) is None
        assert generator.generate_parallel_execution([], workflow) is None
        assert generator.format_output('test', workflow) == {
            'content': 'test',
            'framework': 'test',
        }
        assert generator.validate_generated_output({'content': 'test'}) is True

    def test_concrete_implementation_with_llm_config(self):
        """Test concrete implementation with LLM config."""

        class ConcreteGenerator(BaseGenerator):
            def generate(self, workflow, context_document=None, llm_config=None):
                return {'content': 'generated', 'framework': 'test'}

            def get_supported_task_types(self):
                return ['bash']

            def supports_feature(self, feature):
                return False

            def generate_metadata(self, workflow):
                return {}

            def generate_schedule(self, schedule):
                return None

            def generate_task(self, task, workflow):
                return {}

            def generate_dependencies(self, tasks):
                return []

            def generate_error_handling(self, error_handling):
                return None

            def generate_conditional_logic(self, task, workflow):
                return None

            def generate_loop_logic(self, task, workflow):
                return None

            def generate_parallel_execution(self, tasks, workflow):
                return None

            def format_output(self, generated_content, workflow):
                return {'content': generated_content}

            def validate_generated_output(self, output):
                return True

        llm_config = LLMConfig(region='us-east-1')
        generator = ConcreteGenerator(llm_config)
        assert generator.llm_config == llm_config

        # Test all methods to ensure coverage
        from awslabs.etl_replatforming_mcp_server.models.flex_workflow import Task

        test_task = Task(id='test_task', name='Test Task', type='bash')
        workflow = FlexWorkflow(name='test', tasks=[])

        assert generator.generate(workflow) == {'content': 'generated', 'framework': 'test'}
        assert generator.get_supported_task_types() == ['bash']
        assert generator.supports_feature('test') is False
        assert generator.generate_metadata(workflow) == {}
        assert generator.generate_schedule(None) is None
        assert generator.generate_task(test_task, workflow) == {}
        assert generator.generate_dependencies([]) == []
        assert generator.generate_error_handling(None) is None
        assert generator.generate_conditional_logic(None, workflow) is None
        assert generator.generate_loop_logic(None, workflow) is None
        assert generator.generate_parallel_execution([], workflow) is None
        assert generator.format_output('test', workflow) == {'content': 'test'}
        assert generator.validate_generated_output({}) is True

    def test_optional_methods_have_default_implementations(self):
        """Test that optional methods have default implementations."""

        class MinimalGenerator(BaseGenerator):
            def generate(self, workflow, context_document=None, llm_config=None):
                return {}

            def get_supported_task_types(self):
                return []

            def supports_feature(self, feature):
                return False

            def generate_metadata(self, workflow):
                return {}

            def generate_schedule(self, schedule):
                return None

            def generate_task(self, task, workflow):
                return {}

            def generate_dependencies(self, tasks):
                return []

            def generate_error_handling(self, error_handling):
                return None

            def generate_conditional_logic(self, task, workflow):
                return None

            def generate_loop_logic(self, task, workflow):
                return None

            def generate_parallel_execution(self, tasks, workflow):
                return None

            def format_output(self, generated_content, workflow):
                return {}

            def validate_generated_output(self, output):
                return True

        generator = MinimalGenerator()
        workflow = FlexWorkflow(name='test', tasks=[])

        # Test all methods to ensure coverage
        from awslabs.etl_replatforming_mcp_server.models.flex_workflow import Task

        test_task = Task(id='test_task', name='Test Task', type='bash')

        assert generator.generate(workflow) == {}
        assert generator.get_supported_task_types() == []
        assert generator.supports_feature('test') is False
        assert generator.generate_metadata(workflow) == {}
        assert generator.generate_schedule(None) is None
        assert generator.generate_task(test_task, workflow) == {}
        assert generator.generate_dependencies([]) == []
        assert generator.generate_error_handling(None) is None
        assert generator.generate_conditional_logic(None, workflow) is None
        assert generator.generate_loop_logic(None, workflow) is None
        assert generator.generate_parallel_execution([], workflow) is None
        assert generator.format_output('test', workflow) == {}
        assert generator.validate_generated_output({}) is True

        # Test optional methods return None by default
        assert generator.generate_task_groups(workflow) is None
        assert generator.generate_connections(workflow) is None
        assert generator.generate_enhanced_schedule(workflow) is None
        assert generator.generate_monitoring_config(workflow) is None

    def test_use_enhanced_features_detection(self):
        """Test use_enhanced_features method detects enhanced features."""

        class TestGenerator(BaseGenerator):
            def generate(self, workflow, context_document=None, llm_config=None):
                return {}

            def get_supported_task_types(self):
                return []

            def supports_feature(self, feature):
                return False

            def generate_metadata(self, workflow):
                return {}

            def generate_schedule(self, schedule):
                return None

            def generate_task(self, task, workflow):
                return {}

            def generate_dependencies(self, tasks):
                return []

            def generate_error_handling(self, error_handling):
                return None

            def generate_conditional_logic(self, task, workflow):
                return None

            def generate_loop_logic(self, task, workflow):
                return None

            def generate_parallel_execution(self, tasks, workflow):
                return None

            def format_output(self, generated_content, workflow):
                return {}

            def validate_generated_output(self, output):
                return True

        generator = TestGenerator()

        # Test all methods to ensure coverage
        from awslabs.etl_replatforming_mcp_server.models.flex_workflow import Task

        test_task = Task(id='test_task', name='Test Task', type='bash')
        workflow = FlexWorkflow(name='test', tasks=[])

        assert generator.generate(workflow) == {}
        assert generator.get_supported_task_types() == []
        assert generator.supports_feature('test') is False
        assert generator.generate_metadata(workflow) == {}
        assert generator.generate_schedule(None) is None
        assert generator.generate_task(test_task, workflow) == {}
        assert generator.generate_dependencies([]) == []
        assert generator.generate_error_handling(None) is None
        assert generator.generate_conditional_logic(None, workflow) is None
        assert generator.generate_loop_logic(None, workflow) is None
        assert generator.generate_parallel_execution([], workflow) is None
        assert generator.format_output('test', workflow) == {}
        assert generator.validate_generated_output({}) is True

        # Basic workflow - no enhanced features
        basic_workflow = FlexWorkflow(name='basic', tasks=[])
        assert generator.use_enhanced_features(basic_workflow) is False

        # Workflow with task groups
        workflow_with_groups = FlexWorkflow(
            name='enhanced', tasks=[], task_groups=[TaskGroup(group_id='group1')]
        )
        assert generator.use_enhanced_features(workflow_with_groups) is True

        # Workflow with connections
        workflow_with_connections = FlexWorkflow(
            name='enhanced', tasks=[], connections={'db': 'postgres'}
        )
        assert generator.use_enhanced_features(workflow_with_connections) is True

    def test_incomplete_implementation_fails(self):
        """Test that incomplete implementation cannot be instantiated."""

        class IncompleteGenerator(BaseGenerator):
            def generate(self, workflow, context_document=None, llm_config=None):
                return {}

            # Missing other required methods

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteGenerator()  # type: ignore
