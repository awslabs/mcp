"""Tests for awslabs.etl_replatforming_mcp_server.generators.airflow_generator"""

import pytest

from awslabs.etl_replatforming_mcp_server.generators.airflow_generator import (
    AirflowGenerator,
)
from awslabs.etl_replatforming_mcp_server.models.flex_workflow import (
    ErrorHandling,
    FlexWorkflow,
    LoopItems,
    Schedule,
    Task,
    TaskDependency,
    TaskLoop,
)


class TestAirflowGenerator:
    """Tests for awslabs.etl_replatforming_mcp_server.generators.airflow_generator"""

    def setup_method(self):
        self.generator = AirflowGenerator()
        self.sample_workflow = FlexWorkflow(
            name='test_workflow',
            description='Test workflow',
            schedule=Schedule(type='cron', expression='0 9 * * *', timezone='UTC'),
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

    # generate method tests
    def test_generate_workflow_basic(self):
        """Test generate with basic workflow"""
        result = self.generator.generate(self.sample_workflow)

        assert 'framework' in result
        assert result['framework'] == 'airflow'
        assert 'dag_code' in result
        assert 'dag_id' in result
        assert 'filename' in result

        dag_code = result['dag_code']
        assert 'from airflow import DAG' in dag_code
        assert 'etl_test_workflow' in dag_code

    def test_generate_workflow_with_context(self):
        """Test generate with context document"""
        context_doc = '# Test Context\nUse custom naming conventions'
        result = self.generator.generate(self.sample_workflow, context_doc)
        assert 'dag_code' in result
        # Context document should not break generation
        assert 'from airflow import DAG' in result['dag_code']

    def test_generate_workflow_without_context(self):
        """Test generate without context document"""
        result = self.generator.generate(self.sample_workflow)
        assert 'dag_code' in result
        assert 'from airflow import DAG' in result['dag_code']

    # generate_schedule method tests
    def test_generate_schedule_none(self):
        """Test generate_schedule with None"""
        result = self.generator.generate_schedule(None)
        assert result == "'@daily'"

    def test_generate_schedule_rate_daily(self):
        """Test generate_schedule with rate(1 day)"""
        schedule = Schedule(type='rate', expression='rate(1 day)')
        result = self.generator.generate_schedule(schedule)
        assert result == "'@daily'"

    def test_generate_schedule_rate_hourly(self):
        """Test generate_schedule with rate(1 hour)"""
        schedule = Schedule(type='rate', expression='rate(1 hour)')
        result = self.generator.generate_schedule(schedule)
        assert result == "'@hourly'"

    def test_generate_schedule_rate_custom(self):
        """Test generate_schedule with custom rate"""
        schedule = Schedule(type='rate', expression='rate(30 minutes)')
        result = self.generator.generate_schedule(schedule)
        assert result == "'rate(30 minutes)'"

    def test_generate_schedule_cron(self):
        """Test generate_schedule with cron expression"""
        schedule = Schedule(type='cron', expression='0 9 * * *')
        result = self.generator.generate_schedule(schedule)
        assert result == "'0 9 * * *'"

    def test_generate_schedule_manual(self):
        """Test generate_schedule with manual type"""
        schedule = Schedule(type='manual', expression='')
        result = self.generator.generate_schedule(schedule)
        assert result == 'None'

    def test_generate_schedule_event(self):
        """Test generate_schedule with event type"""
        schedule = Schedule(type='event', expression='')
        result = self.generator.generate_schedule(schedule)
        assert result == 'None'

    # generate_task method tests
    def test_generate_task_sql(self):
        """Test generate_task with SQL task"""
        sql_task = Task(id='sql_task', name='SQL Task', type='sql', command='SELECT 1')
        result = self.generator.generate_task(sql_task, self.sample_workflow)

        assert 'RedshiftSQLOperator' in result
        assert 'sql_task' in result
        assert 'SELECT 1' in result

    def test_generate_task_python(self):
        """Test generate_task with Python task"""
        python_task = Task(
            id='py_task', name='Python Task', type='python', command="print('hello')"
        )
        result = self.generator.generate_task(python_task, self.sample_workflow)

        assert 'PythonOperator' in result
        assert 'py_task' in result
        assert "print('hello')" in result

    def test_generate_task_bash(self):
        """Test generate_task with Bash task"""
        bash_task = Task(id='bash_task', name='Bash Task', type='bash', command='echo hello')
        result = self.generator.generate_task(bash_task, self.sample_workflow)

        assert 'BashOperator' in result
        assert 'bash_task' in result
        assert 'echo hello' in result

    def test_generate_task_unknown_type(self):
        """Test generate_task with unknown task type"""
        unknown_task = Task(
            id='unknown_task',
            name='Unknown Task',
            type='custom',
            command='custom_command()',
        )
        result = self.generator.generate_task(unknown_task, self.sample_workflow)

        assert 'PythonOperator' in result  # Default to Python
        assert 'unknown_task' in result
        assert 'custom_command()' in result

    # generate_dependencies method tests
    def test_generate_dependencies_basic(self):
        """Test generate_dependencies with basic dependencies"""
        tasks = [
            Task(id='task1', name='Task 1', type='python', command='step1()'),
            Task(
                id='task2',
                name='Task 2',
                type='python',
                command='step2()',
                depends_on=[TaskDependency(task_id='task1', condition='success')],
            ),
        ]

        result = self.generator.generate_dependencies(tasks)
        assert '[task1] >> task2' in result

    def test_generate_dependencies_no_deps(self):
        """Test generate_dependencies with no dependencies"""
        tasks = [Task(id='task1', name='Task 1', type='python', command='step1()')]
        result = self.generator.generate_dependencies(tasks)
        assert '# No basic dependencies' in result

    # generate_conditional_logic method tests
    def test_generate_conditional_logic(self):
        """Test generate_conditional_logic method"""
        task = Task(
            id='conditional_task',
            name='Conditional Task',
            type='python',
            command='process_data()',
            depends_on=[
                TaskDependency(
                    task_id='check_task',
                    condition='output.count > 100',
                    condition_type='expression',
                )
            ],
        )

        result = self.generator.generate_conditional_logic(task, self.sample_workflow)
        assert 'BranchPythonOperator' in result
        assert 'check_task_branch' in result

    # generate_error_handling method tests
    def test_generate_error_handling_with_emails(self):
        """Test generate_error_handling with email notifications"""
        error_handling = ErrorHandling(
            on_failure='retry',
            notification_emails=['admin@example.com', 'team@example.com'],
            max_retries=3,
        )

        result = self.generator.generate_error_handling(error_handling)
        assert 'default_args' in result
        assert "email_on_failure': True" in result
        assert "retries': 3" in result
        assert 'admin@example.com' in result

    def test_generate_error_handling_no_emails(self):
        """Test generate_error_handling without email notifications"""
        error_handling = ErrorHandling(on_failure='fail', max_retries=1)

        result = self.generator.generate_error_handling(error_handling)
        assert "email_on_failure': False" in result
        assert "retries': 1" in result

    def test_generate_error_handling_none(self):
        """Test generate_error_handling with None"""
        result = self.generator.generate_error_handling(None)
        assert 'default_args' in result
        assert "retries': 2" in result  # Default value

    # generate_loop_logic method tests
    def test_generate_loop_logic_for_each(self):
        """Test generate_loop_logic with for_each loop"""
        task = Task(
            id='loop_task',
            name='Loop Task',
            type='python',
            command='process_item(item)',
            loop=TaskLoop(
                type='for_each',
                items=LoopItems(source='static', values=['a', 'b', 'c']),
                item_variable='item',
            ),
        )

        result = self.generator.generate_loop_logic(task, self.sample_workflow)
        assert 'TaskGroup' in result
        assert 'loop_task_loop_group' in result
        assert 'for i, item in enumerate(items)' in result

    def test_generate_loop_logic_range(self):
        """Test generate_loop_logic with range loop"""
        task = Task(
            id='range_task',
            name='Range Task',
            type='python',
            command='process_batch(batch)',
            loop=TaskLoop(
                type='range',
                items=LoopItems(source='range', start=1, end=10, step=2),
                item_variable='batch',
            ),
        )

        result = self.generator.generate_loop_logic(task, self.sample_workflow)
        assert 'TaskGroup' in result
        assert 'range(1, 10, 2)' in result

    def test_generate_loop_logic_while(self):
        """Test generate_loop_logic with while loop"""
        task = Task(
            id='while_task',
            name='While Task',
            type='python',
            command='improve_quality()',
            loop=TaskLoop(
                type='while',
                condition='output.quality < 0.95',
                item_variable='iteration',
            ),
        )

        result = self.generator.generate_loop_logic(task, self.sample_workflow)
        assert 'while_task_while_sensor' in result
        assert 'PythonSensor' in result

    def test_generate_loop_logic_no_loop(self):
        """Test generate_loop_logic with task that has no loop"""
        task = Task(id='normal_task', name='Normal Task', type='python', command='process()')
        result = self.generator.generate_loop_logic(task, self.sample_workflow)
        assert result == ''

    # Helper method tests

    def test_generate_imports(self):
        """Test _generate_imports method"""
        workflow = FlexWorkflow(
            name='test',
            tasks=[
                Task(id='sql_task', name='SQL Task', type='sql', command='SELECT 1'),
                Task(
                    id='py_task',
                    name='Python Task',
                    type='python',
                    command="print('test')",
                ),
            ],
        )

        result = self.generator._generate_imports(workflow)
        assert 'from airflow import DAG' in result
        assert 'RedshiftSQLOperator' in result
        assert 'PythonOperator' in result

    def test_generate_dag_definition(self):
        """Test _generate_dag_definition method"""
        result = self.generator._generate_dag_definition(self.sample_workflow)
        assert 'dag = DAG(' in result
        assert 'etl_test_workflow' in result
        assert 'Test workflow' in result

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
        assert self.generator.supports_feature('scheduling') is True
        assert self.generator.supports_feature('unsupported_feature') is False

    def test_generate_metadata(self):
        """Test generate_metadata method"""
        result = self.generator.generate_metadata(self.sample_workflow)
        assert result['dag_id'] == 'etl_test_workflow'
        assert result['description'] == 'Test workflow'
        assert 'generated' in result['tags']
        assert 'etl' in result['tags']

    def test_format_output(self):
        """Test format_output method"""
        dag_code = '# Generated DAG code'
        result = self.generator.format_output(dag_code, self.sample_workflow)

        assert result['dag_code'] == dag_code
        assert result['dag_id'] == 'etl_test_workflow'
        assert result['filename'] == 'etl_test_workflow.py'
        assert result['framework'] == 'airflow'

    def test_validate_generated_output_valid(self):
        """Test validate_generated_output with valid output"""
        valid_output = {
            'dag_code': 'from airflow import DAG\ndag = DAG("test")',
            'dag_id': 'test_dag',
            'filename': 'test_dag.py',
            'framework': 'airflow',
        }
        assert self.generator.validate_generated_output(valid_output) is True

    def test_validate_generated_output_invalid(self):
        """Test validate_generated_output with invalid output"""
        invalid_output = {
            'dag_code': 'invalid code without DAG',
            'dag_id': 'test_dag',
            # Missing required keys
        }
        assert self.generator.validate_generated_output(invalid_output) is False

    # Branch handling fix tests
    def test_extract_condition_value_for_airflow_with_single_quotes(self):
        """Test extracting condition value with single quotes"""
        condition = "$.result == 'processing_complete'"
        result = self.generator._extract_condition_value_for_airflow(condition, 'fallback')
        assert result == 'processing_complete'

    def test_extract_condition_value_for_airflow_with_double_quotes(self):
        """Test extracting condition value with double quotes"""
        condition = '$.result == "quality_passed"'
        result = self.generator._extract_condition_value_for_airflow(condition, 'fallback')
        assert result == 'quality_passed'

    def test_extract_condition_value_for_airflow_fallback(self):
        """Test fallback when no condition value can be extracted"""
        condition = 'some_complex_condition'
        result = self.generator._extract_condition_value_for_airflow(condition, 'fallback_task')
        assert result == 'fallback_task'

    def test_generate_branch_task_with_empty_branches(self):
        """Test that empty branches list doesn't cause list index out of range error"""
        # Create a branch task with no branches
        branch_task = Task(
            id='empty_branch',
            name='empty_branch',
            type='branch',
            command='check_condition',
            parameters={'branches': []},
        )

        # Create minimal workflow
        workflow = FlexWorkflow(name='test_workflow', tasks=[branch_task])

        # Generate branch task - should not crash
        result = self.generator._generate_branch_task(branch_task, workflow)

        # Should generate a PythonOperator instead of BranchPythonOperator
        assert 'PythonOperator' in result
        assert 'No branches defined' in result

    def test_generate_branch_task_with_single_branch(self):
        """Test that single branch doesn't cause list index out of range error"""
        # Create a branch task with only one branch
        branch_task = Task(
            id='single_branch',
            name='single_branch',
            type='branch',
            command='check_condition',
            parameters={
                'branches': [{'next_task': 'success_task', 'condition': "$.result == 'success'"}]
            },
        )

        workflow = FlexWorkflow(name='test', tasks=[branch_task])

        # Generate branch task - should not crash
        result = self.generator._generate_branch_task(branch_task, workflow)

        # Should generate BranchPythonOperator with proper logic
        assert 'BranchPythonOperator' in result
        assert "if result == 'success':" in result
        assert "return 'success_task'" in result
        assert 'else:' in result  # Default case

    def test_generate_branch_task_with_multiple_branches(self):
        """Test that multiple branches work correctly"""
        # Create a branch task with multiple branches
        branch_task = Task(
            id='multi_branch',
            name='multi_branch',
            type='branch',
            command='check_condition',
            parameters={
                'branches': [
                    {'next_task': 'success_task', 'condition': "$.result == 'success'"},
                    {'next_task': 'failure_task', 'condition': "$.result == 'failure'"},
                    {'next_task': 'retry_task', 'condition': "$.result == 'retry'"},
                ]
            },
        )

        workflow = FlexWorkflow(name='test', tasks=[branch_task])

        # Generate branch task
        result = self.generator._generate_branch_task(branch_task, workflow)

        # Should generate BranchPythonOperator with all conditions
        assert 'BranchPythonOperator' in result
        assert "if result == 'success':" in result
        assert "elif result == 'failure':" in result
        assert "elif result == 'retry':" in result
        assert "return 'success_task'" in result
        assert "return 'failure_task'" in result
        assert "return 'retry_task'" in result

    def test_regression_prevention_list_index_out_of_range(self):
        """Test that prevents the original list index out of range error"""
        # This test specifically prevents the original bug where accessing branches[1]
        # without checking list length caused IndexError

        # Create branch task that would have caused the original error
        branch_task = Task(
            id='problematic_branch',
            name='problematic_branch',
            type='branch',
            command='check_status',
            parameters={
                'branches': [
                    {'next_task': 'only_task', 'condition': "$.result == 'complete'"}
                    # Only one branch - accessing branches[1] would fail
                ]
            },
        )

        workflow = FlexWorkflow(name='test', tasks=[branch_task])

        # This should NOT raise IndexError: list index out of range
        try:
            result = self.generator._generate_branch_task(branch_task, workflow)
            # If we get here, the fix worked
            assert 'BranchPythonOperator' in result
            assert "if result == 'complete':" in result
            assert "return 'only_task'" in result
        except IndexError as e:
            if 'list index out of range' in str(e):
                pytest.fail('Original list index out of range bug has regressed!')
            else:
                raise  # Re-raise if it's a different IndexError

    def test_find_task_in_flex_missing_task_handling(self):
        """Test that missing task references are handled gracefully"""
        # Create workflow with limited tasks
        workflow = FlexWorkflow(
            name='test_workflow',
            tasks=[Task(id='existing_task', name='existing', type='python', command='pass')],
        )

        # Try to find a non-existent task - should return None, not crash
        result = self.generator._find_task_in_flex('missing_task', workflow)
        assert result is None

        # Try to find existing task - should work normally
        result = self.generator._find_task_in_flex('existing_task', workflow)
        assert result is not None
        assert result.id == 'existing_task'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
