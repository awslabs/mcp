import pytest

from awslabs.etl_replatforming_mcp_server.generators.step_functions_generator import (
    StepFunctionsGenerator,
)
from awslabs.etl_replatforming_mcp_server.models.flex_workflow import (
    ErrorHandling,
    FlexWorkflow,
    Schedule,
    Task,
    TaskDependency,
)


class TestStepFunctionsGenerator:
    """Tests for awslabs.etl_replatforming_mcp_server.generators.step_functions_generator"""

    def setup_method(self):
        self.generator = StepFunctionsGenerator()
        self.sample_workflow = FlexWorkflow(
            name='test_workflow',
            description='Test workflow',
            schedule=Schedule(type='rate', expression='rate(1 day)', timezone='UTC'),
            tasks=[
                Task(
                    id='task1',
                    name='Task 1',
                    type='sql',
                    command='SELECT * FROM table1',
                ),
                Task(
                    id='task2',
                    name='Task 2',
                    type='python',
                    command='process_data()',
                    depends_on=[TaskDependency(task_id='task1', condition='success')],
                ),
            ],
            error_handling=ErrorHandling(
                on_failure='fail', notification_emails=['test@example.com']
            ),
        )

    def test_generate_basic_workflow(self):
        """Test generating a basic Step Functions state machine"""
        result = self.generator.generate(self.sample_workflow)

        assert 'framework' in result
        assert result['framework'] == 'step_functions'
        assert 'state_machine_definition' in result

        # Check the generated state machine
        state_machine = result['state_machine_definition']
        assert 'Comment' in state_machine
        assert 'StartAt' in state_machine
        assert 'States' in state_machine
        assert len(state_machine['States']) == 2

    def test_generate_workflow_with_context(self):
        """Test generate with context document"""
        context_doc = '# Test Context\nUse AWS Lambda for Python tasks'
        result = self.generator.generate(self.sample_workflow, context_doc)

        assert 'state_machine_definition' in result
        # Context document should not break generation
        state_machine = result['state_machine_definition']
        assert 'Comment' in state_machine
        assert 'StartAt' in state_machine

    def test_generate_workflow_without_context(self):
        """Test generate without context document"""
        result = self.generator.generate(self.sample_workflow)

        assert 'state_machine_definition' in result
        state_machine = result['state_machine_definition']
        assert 'Comment' in state_machine
        assert 'StartAt' in state_machine

    # New required methods tests
    def test_get_supported_task_types(self):
        """Test get_supported_task_types method"""
        result = self.generator.get_supported_task_types()
        # Check that it returns the actual task types from task_types.py
        assert isinstance(result, list)
        assert len(result) > 0
        # Check for some core task types that should be supported
        assert 'sql' in result
        assert 'python' in result
        assert 'bash' in result

    def test_supports_feature(self):
        """Test supports_feature method"""
        assert self.generator.supports_feature('loops') is True
        assert self.generator.supports_feature('conditional_logic') is True
        assert self.generator.supports_feature('parallel_execution') is True
        assert self.generator.supports_feature('error_handling') is True
        assert (
            self.generator.supports_feature('scheduling') is False
        )  # Step Functions doesn't have built-in scheduling
        assert self.generator.supports_feature('unsupported_feature') is False

    def test_generate_metadata(self):
        """Test generate_metadata method"""
        result = self.generator.generate_metadata(self.sample_workflow)
        assert result['state_machine_name'] == 'etl-test_workflow'
        assert result['comment'] == 'Test workflow'  # Uses actual description when available
        assert 'execution-role' in result['execution_role']

    def test_generate_schedule(self):
        """Test generate_schedule method"""
        schedule = Schedule(type='rate', expression='rate(1 day)')
        result = self.generator.generate_schedule(schedule)
        assert result is None  # Step Functions doesn't have built-in scheduling

    def test_generate_task_sql(self):
        """Test generate_task with SQL task"""
        sql_task = Task(id='sql_task', name='SQL Task', type='sql', command='SELECT 1')
        result = self.generator.generate_task(sql_task, self.sample_workflow)

        assert result['Type'] == 'Task'
        assert 'redshiftdata:executeStatement' in result['Resource']
        assert result['Parameters']['Sql'] == 'SELECT 1'

    def test_generate_task_python(self):
        """Test generate_task with Python task"""
        python_task = Task(
            id='py_task', name='Python Task', type='python', command="print('hello')"
        )
        result = self.generator.generate_task(python_task, self.sample_workflow)

        assert result['Type'] == 'Task'
        assert 'glue:startJobRun.sync' in result['Resource']
        assert result['Parameters']['Arguments']['--script'] == "print('hello')"

    def test_generate_task_bash(self):
        """Test generate_task with Bash task"""
        bash_task = Task(id='bash_task', name='Bash Task', type='bash', command='echo hello')
        result = self.generator.generate_task(bash_task, self.sample_workflow)

        assert result['Type'] == 'Task'
        assert 'batch:submitJob.sync' in result['Resource']
        assert result['Parameters']['Parameters']['command'] == 'echo hello'

    def test_generate_dependencies(self):
        """Test generate_dependencies method"""
        tasks = [Task(id='task1', name='Task 1', type='python', command='step1()')]
        result = self.generator.generate_dependencies(tasks)
        assert result is None  # Dependencies handled in state machine structure

    def test_generate_error_handling(self):
        """Test generate_error_handling method"""
        error_handling = ErrorHandling(on_failure='retry', max_retries=3)
        result = self.generator.generate_error_handling(error_handling)
        assert result is None  # Error handling embedded in individual states

    def test_generate_conditional_logic_branch_task(self):
        """Test generate_conditional_logic with branch task"""
        branch_task = Task(
            id='branch_task',
            name='Branch Task',
            type='branch',
            command='evaluate_condition',
            parameters={
                'branches': [{'next_task': 'task_a', 'condition': '$.result == "success"'}]
            },
        )
        result = self.generator.generate_conditional_logic(branch_task, self.sample_workflow)

        assert result['Type'] == 'Choice'
        assert 'Choices' in result
        assert 'Default' in result

    def test_generate_conditional_logic_non_branch_task(self):
        """Test generate_conditional_logic with non-branch task"""
        normal_task = Task(
            id='normal_task', name='Normal Task', type='python', command='process()'
        )
        result = self.generator.generate_conditional_logic(normal_task, self.sample_workflow)
        assert result is None

    def test_generate_loop_logic_for_each_task(self):
        """Test generate_loop_logic with for_each task"""
        loop_task = Task(
            id='loop_task',
            name='Loop Task',
            type='for_each',
            command='process_item',
            parameters={'loop_type': 'range', 'start': 1, 'end': 4},
        )
        result = self.generator.generate_loop_logic(loop_task, self.sample_workflow)

        assert result['Type'] == 'Map'
        assert 'Iterator' in result
        assert 'ItemsPath' in result

    def test_generate_loop_logic_non_loop_task(self):
        """Test generate_loop_logic with non-loop task"""
        normal_task = Task(
            id='normal_task', name='Normal Task', type='python', command='process()'
        )
        result = self.generator.generate_loop_logic(normal_task, self.sample_workflow)
        assert result is None

    def test_generate_parallel_execution(self):
        """Test generate_parallel_execution method"""
        tasks = [Task(id='task1', name='Task 1', type='python', command='step1()')]
        result = self.generator.generate_parallel_execution(tasks, self.sample_workflow)
        assert result is None  # Handled in demand-driven generation

    def test_format_output(self):
        """Test format_output method"""
        state_machine = {
            'Comment': 'Test state machine',
            'StartAt': 'task1',
            'States': {'task1': {'Type': 'Task', 'End': True}},
        }
        result = self.generator.format_output(state_machine, self.sample_workflow)

        assert result['state_machine_definition'] == state_machine
        assert result['state_machine_name'] == 'etl-test_workflow'
        assert 'execution-role' in result['execution_role']
        assert result['framework'] == 'step_functions'

    def test_validate_generated_output_valid(self):
        """Test validate_generated_output with valid output"""
        valid_output = {
            'state_machine_definition': {
                'Comment': 'Test',
                'StartAt': 'task1',
                'States': {'task1': {'Type': 'Task', 'End': True}},
            },
            'state_machine_name': 'test-workflow',
            'framework': 'step_functions',
        }
        assert self.generator.validate_generated_output(valid_output) is True

    def test_validate_generated_output_invalid_missing_keys(self):
        """Test validate_generated_output with missing required keys"""
        invalid_output = {
            'state_machine_definition': {'Comment': 'Test'},
            # Missing state_machine_name and framework
        }
        assert self.generator.validate_generated_output(invalid_output) is False

    def test_validate_generated_output_invalid_definition(self):
        """Test validate_generated_output with invalid state machine definition"""
        invalid_output = {
            'state_machine_definition': {
                'Comment': 'Test'
                # Missing States and StartAt
            },
            'state_machine_name': 'test-workflow',
            'framework': 'step_functions',
        }
        assert self.generator.validate_generated_output(invalid_output) is False

    # Python file handling tests
    def test_generate_with_python_files_in_metadata(self):
        """Test generation includes Python files from FLEX metadata"""
        python_files = {
            'extract_data.py': '#!/usr/bin/env python3\ndef extract_data():\n    return "data"'
        }

        workflow = FlexWorkflow(
            name='test_workflow',
            tasks=[
                Task(
                    id='extract',
                    name='Extract',
                    type='python',
                    command='extract_data',
                    script_file='extract_data.py',
                )
            ],
            metadata={'python_files': python_files},
        )

        result = self.generator.generate(workflow)

        assert 'python_files' in result
        assert result['python_files'] == python_files

    def test_generate_task_state_with_script_file(self):
        """Test task state generation uses script_file when available"""
        task = Task(
            id='python_task',
            name='Python Task',
            type='python',
            command='process_data',
            script_file='process_data.py',
        )

        workflow = FlexWorkflow(name='test_workflow', tasks=[task])
        state = self.generator._generate_task_state(task, workflow)

        assert 'glue:startJobRun.sync' in state['Resource']
        arguments = state['Parameters']['Arguments']
        assert '--script_location' in arguments
        assert 'process_data.py' in arguments['--script_location']

    def test_generate_task_state_without_script_file(self):
        """Test task state generation fallback when script_file is not available"""
        task = Task(
            id='python_task',
            name='Python Task',
            type='python',
            command="print('hello')",
            script_file=None,
        )

        workflow = FlexWorkflow(name='test_workflow', tasks=[task])
        state = self.generator._generate_task_state(task, workflow)

        arguments = state['Parameters']['Arguments']
        assert '--script' in arguments
        assert arguments['--script'] == "print('hello')"
        assert '--script_location' not in arguments

    # Choice state condition extraction fix tests
    def test_extract_condition_value_with_single_quotes(self):
        """Test extracting condition value with single quotes"""
        condition = "$.result == 'processing_complete'"
        result = self.generator._extract_condition_value(condition)
        assert result == 'processing_complete'

    def test_extract_condition_value_with_double_quotes(self):
        """Test extracting condition value with double quotes"""
        condition = '$.result == "quality_passed"'
        result = self.generator._extract_condition_value(condition)
        assert result == 'quality_passed'

    def test_extract_condition_value_with_spaces(self):
        """Test extracting condition value with extra spaces"""
        condition = "$.result  ==  'continue_processing'"
        result = self.generator._extract_condition_value(condition)
        assert result == 'continue_processing'

    def test_generate_choice_state_uses_condition_values(self):
        """Test that choice state generation uses extracted condition values, not task IDs"""
        # Create a branch task with proper FLEX format
        branch_task = Task(
            id='test_choice',
            name='test_choice',
            type='branch',
            command='',
            parameters={
                'branches': [
                    {'next_task': 'success_task', 'condition': "$.result == 'success'"},
                    {'next_task': 'failure_task', 'condition': "$.result == 'failure'"},
                ]
            },
        )

        # Create minimal workflow
        workflow = FlexWorkflow(name='test_workflow', tasks=[branch_task])

        # Generate choice state
        choice_state = self.generator._generate_choice_state(branch_task, workflow)

        # Verify the choice state uses condition values, not task IDs
        assert choice_state['Type'] == 'Choice'
        assert len(choice_state['Choices']) == 2

        # First choice should compare against 'success', not 'success_task'
        first_choice = choice_state['Choices'][0]
        assert first_choice['Variable'] == '$.result'
        assert first_choice['StringEquals'] == 'success'  # ✅ Condition value
        assert first_choice['Next'] == 'success_task'  # ✅ Task ID

        # Second choice should compare against 'failure', not 'failure_task'
        second_choice = choice_state['Choices'][1]
        assert second_choice['Variable'] == '$.result'
        assert second_choice['StringEquals'] == 'failure'  # ✅ Condition value
        assert second_choice['Next'] == 'failure_task'  # ✅ Task ID

    def test_choice_state_regression_prevention(self):
        """Test that prevents the original bug from returning"""
        # This test verifies that condition values are extracted correctly from FLEX conditions
        # The original bug used task IDs as comparison values instead of extracting from conditions

        branch_task = Task(
            id='check_processing_complete_choice',
            name='check_processing_complete_choice',
            type='branch',
            command='',
            parameters={
                'branches': [
                    {
                        'next_task': 'processing_complete',
                        'condition': "$.result == 'processing_complete'",
                    },
                    {
                        'next_task': 'continue_processing',
                        'condition': "$.result == 'continue_processing'",
                    },
                ]
            },
        )

        workflow = FlexWorkflow(name='test', tasks=[branch_task])
        choice_state = self.generator._generate_choice_state(branch_task, workflow)

        choices = choice_state['Choices']

        # Verify correct behavior: condition values are extracted from FLEX conditions
        assert choices[0]['StringEquals'] == 'processing_complete'  # Extracted from condition
        assert choices[0]['Next'] == 'processing_complete'  # Task ID
        assert choices[1]['StringEquals'] == 'continue_processing'  # Extracted from condition
        assert choices[1]['Next'] == 'continue_processing'  # Task ID

        # Verify the fix works: StringEquals values come from condition extraction, not task IDs
        # In this case they happen to match, but the extraction logic is what matters
        for i, branch in enumerate(branch_task.parameters['branches']):
            expected_value = self.generator._extract_condition_value(branch['condition'])
            assert choices[i]['StringEquals'] == expected_value

    def test_create_task_chain_already_created(self):
        """Test _create_task_chain when task already exists in states."""
        workflow = FlexWorkflow(
            name='test',
            tasks=[Task(id='task1', name='Task 1', type='python', command="print('test')")],
        )
        states = {'task1': {'Type': 'Task', 'End': True}}

        # Should not modify existing state
        self.generator._create_task_chain('task1', workflow, states)

        assert states['task1']['End'] is True

    def test_create_task_chain_missing_task(self):
        """Test _create_task_chain with missing task."""
        workflow = FlexWorkflow(name='test', tasks=[])
        states = {}

        # Should not crash or add anything
        self.generator._create_task_chain('nonexistent', workflow, states)

        assert len(states) == 0

    def test_generate_map_state_range_loop(self):
        """Test _generate_map_state for range loop."""
        task = Task(
            id='map_task',
            name='Map Task',
            type='for_each',
            command='process_batch',
            parameters={'loop_type': 'range', 'start': 1, 'end': 5},
            batch_size=2,
        )
        workflow = FlexWorkflow(name='test', tasks=[task])

        state = self.generator._generate_map_state(task, workflow)

        assert state['Type'] == 'Map'
        assert state['ItemsPath'] == '$.range_1_5'
        assert state['MaxConcurrency'] == 2
        assert 'ProcessBatch' in state['Iterator']['States']

    def test_generate_map_state_enumerate_loop(self):
        """Test _generate_map_state for enumerate loop."""
        task = Task(
            id='map_task',
            name='Map Task',
            type='for_each',
            command='process_file',
            parameters={'loop_type': 'enumerate', 'items': ['file1.txt', 'file2.txt']},
        )
        workflow = FlexWorkflow(name='test', tasks=[task])

        state = self.generator._generate_map_state(task, workflow)

        assert state['Type'] == 'Map'
        assert state['ItemsPath'] == '$.file_list'
        assert 'ProcessFile' in state['Iterator']['States']

    def test_generate_dynamic_map_state_static_expanded(self):
        """Test _generate_dynamic_map_state with static expansion."""
        task = Task(
            id='dynamic_task',
            name='Dynamic Task',
            type='for_each',
            command='process_item',
            parameters={
                'dynamic_pattern': True,
                'static_expanded': True,
                'operator_type': 'PythonOperator',
                'loop_variable': 'item',
            },
        )
        workflow = FlexWorkflow(name='test', tasks=[task])

        state = self.generator._generate_dynamic_map_state(task, workflow)

        assert state['Type'] == 'Map'
        assert state['ItemsPath'] == '$.dynamic_items'
        assert 'ProcessItem' in state['Iterator']['States']

    def test_generate_dynamic_map_state_bash_operator(self):
        """Test _generate_dynamic_map_state with BashOperator."""
        task = Task(
            id='dynamic_task',
            name='Dynamic Task',
            type='for_each',
            command='echo $item',
            parameters={
                'dynamic_pattern': True,
                'operator_type': 'BashOperator',
                'loop_variable': 'item',
            },
        )
        workflow = FlexWorkflow(name='test', tasks=[task])

        state = self.generator._generate_dynamic_map_state(task, workflow)

        iterator_state = state['Iterator']['States']['ProcessItem']
        assert 'batch:submitJob.sync' in iterator_state['Resource']

    def test_find_retry_loop_target_retry_task(self):
        """Test _find_retry_loop_target with retry task."""
        workflow = FlexWorkflow(
            name='test',
            tasks=[
                Task(id='process_task', name='Process', type='python', command='process()'),
                Task(
                    id='branch_task',
                    name='Branch',
                    type='branch',
                    depends_on=[TaskDependency(task_id='process_task')],
                    parameters={'branches': [{'next_task': 'retry_task'}]},
                ),
                Task(id='retry_task', name='Retry', type='python', command='retry()'),
            ],
        )

        result = self.generator._find_retry_loop_target('retry_task', workflow)

        assert result == 'process_task'

    def test_find_retry_loop_target_no_retry(self):
        """Test _find_retry_loop_target with non-retry task."""
        workflow = FlexWorkflow(
            name='test',
            tasks=[Task(id='normal_task', name='Normal', type='python', command='normal()')],
        )

        result = self.generator._find_retry_loop_target('normal_task', workflow)

        assert result is None

    def test_add_retry_loop_logic(self):
        """Test _add_retry_loop_logic method."""
        workflow = FlexWorkflow(
            name='test',
            tasks=[
                Task(id='process_task', name='Process', type='python', command='process()'),
                Task(
                    id='branch_task',
                    name='Branch',
                    type='branch',
                    depends_on=[TaskDependency(task_id='process_task')],
                    parameters={'branches': [{'next_task': 'retry_task'}]},
                ),
                Task(id='retry_task', name='Retry', type='python', command='retry()'),
            ],
        )
        states = {'retry_task': {'Type': 'Task', 'End': True}}

        self.generator._add_retry_loop_logic('branch_task', workflow, states)

        assert states['retry_task']['Next'] == 'process_task'

    def test_generate_state_machine_with_description(self):
        """Test _generate_state_machine with workflow description."""
        workflow = FlexWorkflow(
            name='test_workflow',
            description='Custom description',
            tasks=[Task(id='task1', name='Task 1', type='python', command="print('test')")],
        )

        state_machine = self.generator._generate_state_machine(workflow)

        assert state_machine['Comment'] == 'Custom description'
        assert state_machine['StartAt'] == 'task1'
        assert 'task1' in state_machine['States']

    def test_generate_state_machine_without_description(self):
        """Test _generate_state_machine without workflow description."""
        workflow = FlexWorkflow(
            name='test_workflow',
            tasks=[Task(id='task1', name='Task 1', type='python', command="print('test')")],
        )

        state_machine = self.generator._generate_state_machine(workflow)

        assert state_machine['Comment'] == 'Generated from FLEX workflow: test_workflow'

    def test_generate_task_state_unsupported_type(self):
        """Test _generate_task_state with unsupported task type."""
        task = Task(id='unsupported', name='Unsupported', type='unsupported_type', command='test')
        workflow = FlexWorkflow(name='test', tasks=[task])

        state = self.generator._generate_task_state(task, workflow)

        # Should default to Glue job
        assert 'glue:startJobRun.sync' in state['Resource']

    def test_generate_task_state_with_retry(self):
        """Test _generate_task_state with retry configuration."""
        task = Task(
            id='retry_task',
            name='Retry Task',
            type='python',
            command='test()',
            retries=3,
            retry_delay=60,
        )
        workflow = FlexWorkflow(name='test', tasks=[task])

        state = self.generator._generate_task_state(task, workflow)

        assert 'Retry' in state
        assert len(state['Retry']) == 1
        assert state['Retry'][0]['MaxAttempts'] == 3

    def test_generate_task_state_with_timeout(self):
        """Test _generate_task_state with timeout."""
        task = Task(
            id='timeout_task', name='Timeout Task', type='python', command='test()', timeout=300
        )
        workflow = FlexWorkflow(name='test', tasks=[task])

        state = self.generator._generate_task_state(task, workflow)

        assert 'TimeoutSeconds' in state
        assert state['TimeoutSeconds'] == 300

    def test_create_state_machine_structure_single_task(self):
        """Test state machine structure with single task."""
        workflow = FlexWorkflow(
            name='single_task',
            tasks=[Task(id='task1', name='Task 1', type='python', command='test()')],
        )

        result = self.generator.generate(workflow)

        assert 'state_machine_definition' in result
        state_machine = result['state_machine_definition']
        assert 'task1' in state_machine['States']
        assert state_machine['States']['task1']['End'] is True

    def test_create_state_machine_structure_with_dependencies(self):
        """Test state machine structure with task dependencies."""
        from awslabs.etl_replatforming_mcp_server.models.flex_workflow import TaskDependency

        workflow = FlexWorkflow(
            name='dependent_tasks',
            tasks=[
                Task(id='task1', name='Task 1', type='python', command='test1()'),
                Task(
                    id='task2',
                    name='Task 2',
                    type='python',
                    command='test2()',
                    depends_on=[TaskDependency(task_id='task1')],
                ),
            ],
        )

        result = self.generator.generate(workflow)

        assert 'state_machine_definition' in result
        state_machine = result['state_machine_definition']
        assert 'task1' in state_machine['States']
        assert 'task2' in state_machine['States']
        assert state_machine['States']['task1']['Next'] == 'task2'
        assert state_machine['States']['task2']['End'] is True

    def test_extract_condition_value_no_quotes(self):
        """Test _extract_condition_value without quotes."""
        condition = '$.result == success'
        result = self.generator._extract_condition_value(condition)
        assert result == '$.result == success'  # Returns full condition when no quotes found

    def test_extract_condition_value_complex(self):
        """Test _extract_condition_value with complex condition."""
        condition = "$.data.status == 'completed' and $.count > 0"
        result = self.generator._extract_condition_value(condition)
        assert result == 'completed'

    def test_generate_choice_state_with_default(self):
        """Test _generate_choice_state includes default path."""
        branch_task = Task(
            id='choice_task',
            name='Choice Task',
            type='branch',
            command='',
            parameters={
                'branches': [{'next_task': 'success_task', 'condition': "$.result == 'success'"}]
            },
        )
        workflow = FlexWorkflow(name='test', tasks=[branch_task])

        choice_state = self.generator._generate_choice_state(branch_task, workflow)

        assert 'Default' in choice_state
        assert choice_state['Default'] == 'success_task'  # Uses first branch as default

    def test_generate_map_state_with_max_concurrency(self):
        """Test _generate_map_state respects max_concurrency."""
        task = Task(
            id='map_task',
            name='Map Task',
            type='for_each',
            command='process',
            parameters={'loop_type': 'range', 'start': 1, 'end': 10},
            batch_size=5,
        )
        workflow = FlexWorkflow(name='test', tasks=[task])

        state = self.generator._generate_map_state(task, workflow)

        assert state['MaxConcurrency'] == 5

    def test_generate_map_state_default_concurrency(self):
        """Test _generate_map_state with default concurrency."""
        task = Task(
            id='map_task',
            name='Map Task',
            type='for_each',
            command='process',
            parameters={'loop_type': 'range', 'start': 1, 'end': 10},
        )
        workflow = FlexWorkflow(name='test', tasks=[task])

        state = self.generator._generate_map_state(task, workflow)

        assert state['MaxConcurrency'] == 3  # Default from implementation

    def test_generate_dynamic_map_state_without_static_expanded(self):
        """Test _generate_dynamic_map_state without static_expanded flag."""
        task = Task(
            id='dynamic_task',
            name='Dynamic Task',
            type='for_each',
            command='process',
            parameters={'dynamic_pattern': True, 'operator_type': 'PythonOperator'},
        )
        workflow = FlexWorkflow(name='test', tasks=[task])

        state = self.generator._generate_dynamic_map_state(task, workflow)

        assert state['Type'] == 'Map'
        assert 'Iterator' in state

    def test_add_retry_loop_logic_no_retry_target(self):
        """Test _add_retry_loop_logic when no retry target found."""
        workflow = FlexWorkflow(
            name='test',
            tasks=[Task(id='normal_task', name='Normal', type='python', command='test()')],
        )
        states = {'normal_task': {'Type': 'Task', 'End': True}}

        # Should not modify states when no retry target
        self.generator._add_retry_loop_logic('normal_task', workflow, states)

        assert states['normal_task']['End'] is True

    def test_create_fail_state(self):
        """Test fail state creation."""
        # Test that generator can handle error scenarios
        task = Task(
            id='fail_task', name='Fail Task', type='python', command='raise Exception("test")'
        )
        workflow = FlexWorkflow(name='fail_workflow', tasks=[task])

        result = self.generator.generate(workflow)
        assert 'state_machine_definition' in result

    def test_generate_task_state_copy_type(self):
        """Test _generate_task_state with copy task type."""
        task = Task(id='copy_task', name='Copy Task', type='copy', command='copy data')
        workflow = FlexWorkflow(name='test', tasks=[task])

        state = self.generator._generate_task_state(task, workflow)

        # Copy tasks fall through to default Glue implementation
        assert 'glue:startJobRun.sync' in state['Resource']
        assert state['Parameters']['Arguments']['--task_type'] == 'copy'

    def test_generate_task_state_email_type(self):
        """Test _generate_task_state with email task type."""
        task = Task(id='email_task', name='Email Task', type='email', command='send notification')
        workflow = FlexWorkflow(name='test', tasks=[task])

        state = self.generator._generate_task_state(task, workflow)

        # Email tasks fall through to default Glue implementation
        assert 'glue:startJobRun.sync' in state['Resource']
        assert state['Parameters']['Arguments']['--task_type'] == 'email'

    def test_generate_task_state_http_type(self):
        """Test _generate_task_state with http task type."""
        task = Task(id='http_task', name='HTTP Task', type='http', command='call api')
        workflow = FlexWorkflow(name='test', tasks=[task])

        state = self.generator._generate_task_state(task, workflow)

        # HTTP tasks fall through to default Glue implementation
        assert 'glue:startJobRun.sync' in state['Resource']
        assert state['Parameters']['Arguments']['--task_type'] == 'http'

    def test_generate_with_empty_tasks(self):
        """Test generate with workflow containing no tasks."""
        workflow = FlexWorkflow(name='empty_workflow', tasks=[])

        result = self.generator.generate(workflow)

        assert result['framework'] == 'step_functions'
        assert 'state_machine_definition' in result
        # Should have a minimal state machine structure
        state_machine = result['state_machine_definition']
        assert 'States' in state_machine

    def test_generate_with_error_handling(self):
        """Test generate with workflow error handling."""
        from awslabs.etl_replatforming_mcp_server.models.flex_workflow import ErrorHandling

        error_handling = ErrorHandling(
            on_failure='retry', max_retries=2, notification_emails=['admin@example.com']
        )

        workflow = FlexWorkflow(
            name='error_workflow',
            tasks=[Task(id='task1', name='Task 1', type='python', command='test()')],
            error_handling=error_handling,
        )

        result = self.generator.generate(workflow)

        # Error handling should be reflected in the state machine
        assert 'state_machine_definition' in result
        state_machine = result['state_machine_definition']
        assert 'States' in state_machine

    # Additional coverage tests merged from test_step_functions_generator_coverage.py
    def test_create_task_chain_with_branch_children(self):
        """Test _create_task_chain with branch task having multiple children - covers lines 84-88"""
        workflow = FlexWorkflow(
            name='branch_workflow',
            tasks=[
                Task(
                    id='branch_task',
                    name='Branch',
                    type='branch',
                    command='decide()',
                    parameters={
                        'branches': [
                            {'next_task': 'child1', 'condition': "$.result == 'a'"},
                            {'next_task': 'child2', 'condition': "$.result == 'b'"},
                        ]
                    },
                ),
                Task(id='child1', name='Child 1', type='python', command='process_a()'),
                Task(id='child2', name='Child 2', type='python', command='process_b()'),
            ],
        )
        states = {}

        self.generator._create_task_chain('branch_task', workflow, states)

        # Should create branch task and both children
        assert 'branch_task' in states
        assert 'child1' in states
        assert 'child2' in states

    def test_create_task_chain_with_retry_loop_back(self):
        """Test _create_task_chain with retry loop back - covers lines 93-94"""
        workflow = FlexWorkflow(
            name='retry_workflow',
            tasks=[
                Task(id='process_task', name='Process', type='python', command='process()'),
                Task(
                    id='check_task',
                    name='Check',
                    type='branch',
                    command='check()',
                    depends_on=[TaskDependency(task_id='process_task')],
                    parameters={
                        'branches': [
                            {'next_task': 'retry_task', 'condition': "$.result == 'retry'"}
                        ]
                    },
                ),
                Task(
                    id='retry_task',
                    name='Retry',
                    type='python',
                    command='retry()',
                    depends_on=[TaskDependency(task_id='check_task')],
                ),
            ],
        )
        states = {}

        # Create the retry task which should loop back
        self.generator._create_task_chain('retry_task', workflow, states)

        # Should have retry loop logic
        assert 'retry_task' in states

    def test_create_task_chain_with_parallel_convergence(self):
        """Test _create_task_chain with parallel tasks and convergence - covers lines 105-113"""
        workflow = FlexWorkflow(
            name='parallel_workflow',
            tasks=[
                Task(id='start_task', name='Start', type='python', command='start()'),
                Task(
                    id='parallel_a',
                    name='Parallel A',
                    type='python',
                    command='process_a()',
                    depends_on=[TaskDependency(task_id='start_task')],
                ),
                Task(
                    id='parallel_b',
                    name='Parallel B',
                    type='python',
                    command='process_b()',
                    depends_on=[TaskDependency(task_id='start_task')],
                ),
                Task(
                    id='convergence',
                    name='Convergence',
                    type='python',
                    command='merge()',
                    depends_on=[
                        TaskDependency(task_id='parallel_a'),
                        TaskDependency(task_id='parallel_b'),
                    ],
                ),
            ],
        )
        states = {}

        self.generator._create_task_chain('start_task', workflow, states)

        # Should create parallel structure with convergence
        assert 'start_task' in states
        assert len(states) > 1

    def test_find_convergence_point_with_common_child(self):
        """Test _find_convergence_point finding common convergence - covers lines 124-139"""
        workflow = FlexWorkflow(
            name='convergence_workflow',
            tasks=[
                Task(id='task_a', name='Task A', type='python', command='a()'),
                Task(id='task_b', name='Task B', type='python', command='b()'),
                Task(
                    id='common_child',
                    name='Common',
                    type='python',
                    command='common()',
                    depends_on=[
                        TaskDependency(task_id='task_a'),
                        TaskDependency(task_id='task_b'),
                    ],
                ),
            ],
        )

        result = self.generator._find_convergence_point(['task_a', 'task_b'], workflow)
        assert result == 'common_child'

    def test_find_convergence_point_no_convergence(self):
        """Test _find_convergence_point with no convergence - covers lines 124-139"""
        workflow = FlexWorkflow(
            name='no_convergence_workflow',
            tasks=[
                Task(id='task_a', name='Task A', type='python', command='a()'),
                Task(id='task_b', name='Task B', type='python', command='b()'),
                Task(
                    id='separate_a',
                    name='Separate A',
                    type='python',
                    command='sep_a()',
                    depends_on=[TaskDependency(task_id='task_a')],
                ),
                Task(
                    id='separate_b',
                    name='Separate B',
                    type='python',
                    command='sep_b()',
                    depends_on=[TaskDependency(task_id='task_b')],
                ),
            ],
        )

        result = self.generator._find_convergence_point(['task_a', 'task_b'], workflow)
        assert result is None

    def test_create_parallel_with_chains_basic(self):
        """Test _create_parallel_with_chains basic functionality - covers lines 149-175"""
        workflow = FlexWorkflow(
            name='parallel_chains_workflow',
            tasks=[
                Task(id='branch_a', name='Branch A', type='python', command='branch_a()'),
                Task(id='branch_b', name='Branch B', type='python', command='branch_b()'),
            ],
        )
        states = {}

        self.generator._create_parallel_with_chains(
            'parallel_group', ['branch_a', 'branch_b'], None, workflow, states
        )

        assert 'parallel_group' in states
        assert states['parallel_group']['Type'] == 'Parallel'
        assert len(states['parallel_group']['Branches']) == 2

    def test_create_parallel_with_chains_with_convergence(self):
        """Test _create_parallel_with_chains with convergence - covers lines 149-175"""
        workflow = FlexWorkflow(
            name='parallel_convergence_workflow',
            tasks=[
                Task(id='branch_a', name='Branch A', type='python', command='branch_a()'),
                Task(id='branch_b', name='Branch B', type='python', command='branch_b()'),
                Task(id='convergence', name='Convergence', type='python', command='converge()'),
            ],
        )
        states = {}

        self.generator._create_parallel_with_chains(
            'parallel_group', ['branch_a', 'branch_b'], 'convergence', workflow, states
        )

        assert 'parallel_group' in states
        assert states['parallel_group']['Type'] == 'Parallel'
        assert states['parallel_group']['Next'] == 'convergence'

    def test_get_children_tasks_with_dependencies(self):
        """Test _get_children_tasks with complex dependencies - covers lines 182-207"""
        workflow = FlexWorkflow(
            name='children_workflow',
            tasks=[
                Task(id='parent', name='Parent', type='python', command='parent()'),
                Task(
                    id='child1',
                    name='Child 1',
                    type='python',
                    command='child1()',
                    depends_on=[TaskDependency(task_id='parent')],
                ),
                Task(
                    id='child2',
                    name='Child 2',
                    type='python',
                    command='child2()',
                    depends_on=[TaskDependency(task_id='parent')],
                ),
                Task(
                    id='grandchild',
                    name='Grandchild',
                    type='python',
                    command='grandchild()',
                    depends_on=[TaskDependency(task_id='child1')],
                ),
            ],
        )

        children = self.generator._get_children_tasks('parent', workflow)
        assert set(children) == {'child1', 'child2'}

    def test_get_children_tasks_branch_task(self):
        """Test _get_children_tasks with branch task - covers lines 182-207"""
        workflow = FlexWorkflow(
            name='branch_children_workflow',
            tasks=[
                Task(
                    id='branch_task',
                    name='Branch',
                    type='branch',
                    command='decide()',
                    parameters={
                        'branches': [
                            {'next_task': 'option_a', 'condition': "$.result == 'a'"},
                            {'next_task': 'option_b', 'condition': "$.result == 'b'"},
                        ]
                    },
                ),
                Task(id='option_a', name='Option A', type='python', command='option_a()'),
                Task(id='option_b', name='Option B', type='python', command='option_b()'),
            ],
        )

        children = self.generator._get_children_tasks('branch_task', workflow)
        assert set(children) == {'option_a', 'option_b'}

    def test_find_task_in_flex_missing_task(self):
        """Test _find_task_in_flex with missing task - covers lines 211-225"""
        workflow = FlexWorkflow(
            name='missing_task_workflow',
            tasks=[Task(id='existing_task', name='Existing', type='python', command='exist()')],
        )

        result = self.generator._find_task_in_flex('nonexistent_task', workflow)
        assert result is None

    def test_find_task_in_flex_empty_workflow(self):
        """Test _find_task_in_flex with empty workflow - covers lines 211-225"""
        workflow = FlexWorkflow(name='empty_workflow', tasks=[])

        result = self.generator._find_task_in_flex('any_task', workflow)
        assert result is None

    def test_generate_state_machine_empty_workflow(self):
        """Test _generate_state_machine with empty workflow - covers lines 231-243"""
        workflow = FlexWorkflow(name='empty_workflow', tasks=[])

        result = self.generator._generate_state_machine(workflow)

        assert result['Comment'] == 'Generated from FLEX workflow: empty_workflow'
        assert 'StartAt' in result
        assert 'States' in result

    def test_generate_state_machine_single_task_workflow(self):
        """Test _generate_state_machine with single task - covers lines 231-243"""
        workflow = FlexWorkflow(
            name='single_task_workflow',
            tasks=[Task(id='only_task', name='Only Task', type='python', command='only()')],
        )

        result = self.generator._generate_state_machine(workflow)

        assert result['StartAt'] == 'only_task'
        assert 'only_task' in result['States']
        assert result['States']['only_task']['End'] is True

    def test_generate_task_state_with_connection_id(self):
        """Test _generate_task_state with connection_id - covers lines 252-253"""
        task = Task(
            id='sql_with_conn',
            name='SQL with Connection',
            type='sql',
            command='SELECT * FROM table',
            connection_id='my_redshift_cluster',
        )
        workflow = FlexWorkflow(name='test', tasks=[task])

        state = self.generator._generate_task_state(task, workflow)

        assert 'redshiftdata:executeStatement' in state['Resource']
        # Connection ID should be used in cluster identifier
        assert 'my_redshift_cluster' in str(state['Parameters'])

    def test_generate_task_state_sql_without_connection(self):
        """Test _generate_task_state SQL without connection_id - covers lines 272, 279"""
        task = Task(id='sql_no_conn', name='SQL No Connection', type='sql', command='SELECT 1')
        workflow = FlexWorkflow(name='test', tasks=[task])

        state = self.generator._generate_task_state(task, workflow)

        assert 'redshiftdata:executeStatement' in state['Resource']
        # Should use default cluster
        assert 'default-cluster' in str(state['Parameters'])

    def test_generate_task_state_bash_with_parameters(self):
        """Test _generate_task_state bash with parameters - covers lines 283"""
        task = Task(
            id='bash_with_params',
            name='Bash with Params',
            type='bash',
            command='echo $MESSAGE',
            parameters={'MESSAGE': 'hello world'},
        )
        workflow = FlexWorkflow(name='test', tasks=[task])

        state = self.generator._generate_task_state(task, workflow)

        assert 'batch:submitJob.sync' in state['Resource']
        assert 'MESSAGE' in str(state['Parameters'])

    def test_generate_task_state_python_with_enhanced_features(self):
        """Test _generate_task_state python with enhanced features - covers lines 295-298"""
        task = Task(
            id='enhanced_python',
            name='Enhanced Python',
            type='python',
            command='process_data()',
            connection_id='glue_connection',
            batch_size=10,
            monitoring_metrics=['records_processed'],
        )
        workflow = FlexWorkflow(name='test', tasks=[task])

        state = self.generator._generate_task_state(task, workflow)

        assert 'glue:startJobRun.sync' in state['Resource']
        # Enhanced features should be reflected in basic parameters
        params = state['Parameters']['Arguments']
        assert '--task_id' in params
        assert params['--task_id'] == 'enhanced_python'

    def test_generate_choice_state_empty_branches(self):
        """Test _generate_choice_state with empty branches - covers line 344"""
        task = Task(
            id='empty_branch',
            name='Empty Branch',
            type='branch',
            command='decide()',
            parameters={'branches': []},
        )
        workflow = FlexWorkflow(name='test', tasks=[task])

        state = self.generator._generate_choice_state(task, workflow)

        assert state['Type'] == 'Choice'
        assert len(state['Choices']) == 0
        # Should have a default even with empty branches
        assert 'Default' in state

    def test_generate_map_state_no_parameters(self):
        """Test _generate_map_state without parameters - covers line 419"""
        task = Task(
            id='map_no_params', name='Map No Params', type='for_each', command='process_item()'
        )
        workflow = FlexWorkflow(name='test', tasks=[task])

        state = self.generator._generate_map_state(task, workflow)

        assert state['Type'] == 'Map'
        # Should handle missing parameters gracefully
        assert 'Iterator' in state

    def test_generate_dynamic_map_state_no_parameters(self):
        """Test _generate_dynamic_map_state without parameters - covers lines 434-436"""
        task = Task(
            id='dynamic_no_params',
            name='Dynamic No Params',
            type='for_each',
            command='process_dynamic()',
        )
        workflow = FlexWorkflow(name='test', tasks=[task])

        state = self.generator._generate_dynamic_map_state(task, workflow)

        assert state['Type'] == 'Map'
        # Should handle missing parameters gracefully
        assert 'Iterator' in state

    def test_generate_task_state_container_type(self):
        """Test _generate_task_state with container type - covers line 520"""
        task = Task(
            id='container_task', name='Container Task', type='container', command='run_container()'
        )
        workflow = FlexWorkflow(name='test', tasks=[task])

        state = self.generator._generate_task_state(task, workflow)

        # Container tasks fall back to Glue in current implementation
        assert 'glue:startJobRun.sync' in state['Resource']
        assert state['Parameters']['Arguments']['--task_type'] == 'container'

    def test_generate_with_llm_config(self):
        """Test generate method with LLM config - covers line 683"""
        workflow = FlexWorkflow(
            name='llm_workflow',
            tasks=[Task(id='task1', name='Task 1', type='python', command='test()')],
        )

        llm_config = {'model_id': 'test-model', 'temperature': 0.1}

        result = self.generator.generate(workflow, llm_config=llm_config)

        assert 'state_machine_definition' in result
        assert result['framework'] == 'step_functions'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
