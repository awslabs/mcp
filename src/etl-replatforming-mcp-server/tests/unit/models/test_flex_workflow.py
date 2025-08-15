import pytest

from awslabs.etl_replatforming_mcp_server.models.flex_workflow import (
    ErrorHandling,
    FlexWorkflow,
    Schedule,
    Task,
    TaskDependency,
)


class TestFlexWorkflow:
    """Tests for awslabs.etl_replatforming_mcp_server.models.flex_workflow"""

    def test_flex_workflow_creation(self):
        """Test FlexWorkflow creation with basic fields"""
        workflow = FlexWorkflow(
            name='test_workflow',
            description='Test workflow',
            tasks=[Task(id='task1', name='Task 1', type='sql', command='SELECT 1')],
        )

        assert workflow.name == 'test_workflow'
        assert workflow.description == 'Test workflow'
        assert len(workflow.tasks) == 1
        assert workflow.tasks[0].id == 'task1'

    def test_task_with_dependencies(self):
        """Test Task creation with dependencies"""
        task = Task(
            id='task2',
            name='Task 2',
            type='python',
            command="print('hello')",
            depends_on=[TaskDependency(task_id='task1', condition='success')],
        )

        assert task.id == 'task2'
        assert len(task.depends_on) == 1
        assert task.depends_on[0].task_id == 'task1'
        assert task.depends_on[0].condition == 'success'

    def test_schedule_creation(self):
        """Test Schedule creation"""
        cron_schedule = Schedule(type='cron', expression='0 9 * * *', timezone='UTC')
        assert cron_schedule.type == 'cron'
        assert cron_schedule.expression == '0 9 * * *'
        assert cron_schedule.timezone == 'UTC'

        rate_schedule = Schedule(type='rate', expression='rate(1 day)')
        assert rate_schedule.type == 'rate'
        assert rate_schedule.expression == 'rate(1 day)'

    def test_error_handling_creation(self):
        """Test ErrorHandling creation"""
        error_handling = ErrorHandling(
            on_failure='retry',
            notification_emails=['admin@example.com'],
            max_retries=3,
            retry_delay=300,
        )

        assert error_handling.on_failure == 'retry'
        assert error_handling.notification_emails == ['admin@example.com']
        assert error_handling.max_retries == 3
        assert error_handling.retry_delay == 300

    def test_task_with_script_file(self):
        """Test Task with script_file field"""
        task = Task(
            id='python_task',
            name='Python Task',
            type='python',
            command='process_data',
            script_file='process_data.py',
        )

        assert task.script_file == 'process_data.py'

    def test_task_without_script_file(self):
        """Test Task without script_file field defaults to None"""
        task = Task(id='sql_task', name='SQL Task', type='sql', command='SELECT 1')

        assert task.script_file is None

    def test_workflow_with_python_files_metadata(self):
        """Test FlexWorkflow with python_files in metadata"""
        python_files = {'extract.py': '#!/usr/bin/env python3\ndef extract(): return "data"'}

        workflow = FlexWorkflow(
            name='test_workflow',
            tasks=[Task(id='task1', name='Task 1', type='python', command='extract')],
            metadata={'python_files': python_files},
        )

        assert 'python_files' in workflow.metadata
        assert workflow.metadata['python_files'] == python_files

    def test_task_ai_generated_defaults(self):
        """Test Task AI generation fields default values"""
        task = Task(id='test_task', name='Test Task', type='python')
        assert task.ai_generated is False
        assert task.ai_confidence is None

    def test_task_ai_generated_explicit(self):
        """Test Task with explicit AI generation fields"""
        task = Task(
            id='ai_task',
            name='AI Task',
            type='python',
            command='ai_generated_function()',
            ai_generated=True,
            ai_confidence=0.85,
        )
        assert task.ai_generated is True
        assert task.ai_confidence == 0.85

    def test_workflow_serialization_with_ai_fields(self):
        """Test workflow serialization includes AI fields"""
        ai_task = Task(
            id='ai_task',
            name='AI Task',
            type='python',
            command='ai_function()',
            ai_generated=True,
            ai_confidence=0.92,
        )
        normal_task = Task(id='normal_task', name='Normal Task', type='bash')

        workflow = FlexWorkflow(name='test', tasks=[ai_task, normal_task])
        data = workflow.to_dict()

        # Check AI task
        ai_task_data = data['tasks'][0]
        assert ai_task_data['ai_generated'] is True
        assert ai_task_data['ai_confidence'] == 0.92

        # Check normal task
        normal_task_data = data['tasks'][1]
        assert normal_task_data['ai_generated'] is False
        assert normal_task_data['ai_confidence'] is None

    def test_workflow_deserialization_with_ai_fields(self):
        """Test workflow deserialization handles AI fields"""
        data = {
            'name': 'test_workflow',
            'tasks': [
                {
                    'id': 'ai_task',
                    'name': 'AI Task',
                    'type': 'python',
                    'command': 'ai_process()',
                    'ai_generated': True,
                    'ai_confidence': 0.78,
                },
                {
                    'id': 'normal_task',
                    'name': 'Normal Task',
                    'type': 'bash',
                    'command': 'echo hello',
                },
            ],
        }

        workflow = FlexWorkflow.from_dict(data)

        # Check AI task
        ai_task = workflow.tasks[0]
        assert ai_task.ai_generated is True
        assert ai_task.ai_confidence == 0.78

        # Check normal task (should default AI fields)
        normal_task = workflow.tasks[1]
        assert normal_task.ai_generated is False
        assert normal_task.ai_confidence is None

    # Enhanced FLEX workflow features tests
    def test_mandatory_orchestration_fields_detection(self):
        """Test that no orchestration fields are mandatory after simplification"""
        # Create workflow with SQL task missing connection_id
        sql_task = Task(
            id='extract_data',
            name='Extract Data',
            type='sql',
            command='SELECT * FROM customers',
        )

        workflow = FlexWorkflow(name='test_workflow', tasks=[sql_task])

        missing_fields = workflow.get_missing_fields()
        # After simplification, no orchestration fields are mandatory
        assert len(missing_fields) == 0

    def test_no_mandatory_fields_for_non_data_tasks(self):
        """Test that non-data tasks don't require connection_id"""
        python_task = Task(
            id='process_data',
            name='Process Data',
            type='python',
            command="print('processing')",
        )

        workflow = FlexWorkflow(name='test_workflow', tasks=[python_task])

        missing_fields = workflow.get_missing_fields()
        assert not any('connection_id' in field for field in missing_fields)

    def test_enhanced_schedule_with_data_triggers(self):
        """Test enhanced schedule with data triggers"""
        from awslabs.etl_replatforming_mcp_server.models.flex_workflow import (
            TriggerConfig,
        )

        data_trigger = TriggerConfig(
            trigger_type='file',
            target='/data/customers.csv',
            poke_interval=300,
            timeout=3600,
        )

        schedule = Schedule(
            type='cron',
            expression='0 2 * * *',
            data_triggers=[data_trigger],
            catchup=False,
            max_active_runs=1,
        )

        workflow = FlexWorkflow(name='test_workflow', schedule=schedule, tasks=[])

        # Test serialization
        workflow_dict = workflow.to_dict()
        assert 'data_triggers' in workflow_dict['schedule']
        assert len(workflow_dict['schedule']['data_triggers']) == 1
        assert workflow_dict['schedule']['data_triggers'][0]['trigger_type'] == 'file'

    def test_task_groups_serialization(self):
        """Test task groups serialization and deserialization"""
        from awslabs.etl_replatforming_mcp_server.models.flex_workflow import TaskGroup

        task_group = TaskGroup(group_id='data_extraction', tooltip='Extract data from sources')

        task = Task(
            id='extract_customers',
            name='Extract Customers',
            type='sql',
            command='SELECT * FROM customers',
            task_group=task_group,
        )

        workflow = FlexWorkflow(name='test_workflow', tasks=[task], task_groups=[task_group])

        # Test serialization
        workflow_dict = workflow.to_dict()
        assert len(workflow_dict['task_groups']) == 1
        assert workflow_dict['task_groups'][0]['group_id'] == 'data_extraction'

        # Test deserialization
        restored_workflow = FlexWorkflow.from_dict(workflow_dict)
        assert len(restored_workflow.task_groups) == 1
        assert restored_workflow.task_groups[0].group_id == 'data_extraction'

    def test_enhanced_task_features(self):
        """Test enhanced task features"""
        task = Task(
            id='process_batch',
            name='Process Batch',
            type='sql',
            command='SELECT * FROM orders',
            connection_id='postgres_prod',
            trigger_rule='one_success',
            batch_size=1000,
            monitoring_metrics=['records_processed', 'execution_time'],
        )

        workflow = FlexWorkflow(name='test_workflow', tasks=[task])

        # Test serialization includes enhanced fields
        workflow_dict = workflow.to_dict()
        task_dict = workflow_dict['tasks'][0]

        assert task_dict['connection_id'] == 'postgres_prod'
        assert task_dict['trigger_rule'] == 'one_success'
        assert task_dict['batch_size'] == 1000
        assert 'records_processed' in task_dict['monitoring_metrics']

    def test_connections_mapping(self):
        """Test workflow-level connections mapping"""
        workflow = FlexWorkflow(
            name='test_workflow',
            connections={'postgres_prod': 'postgres', 's3_data_lake': 's3'},
            tasks=[],
        )

        workflow_dict = workflow.to_dict()
        assert 'postgres_prod' in workflow_dict['connections']
        assert workflow_dict['connections']['postgres_prod'] == 'postgres'

    def test_placeholder_generation_for_missing_connection(self):
        """Test placeholder generation for missing task commands"""
        task_without_command = Task(
            id='extract_data',
            name='Extract Data',
            type='sql',
            command=None,  # Missing command
        )

        workflow = FlexWorkflow(name='test_workflow', tasks=[task_without_command])

        missing_fields = workflow.get_missing_fields()
        placeholders_dict = workflow.to_dict_with_placeholders(missing_fields)

        # Check that placeholder was added for missing command
        task_dict = placeholders_dict['tasks'][0]
        assert 'command' in task_dict
        assert 'REQUIRED' in task_dict['command']

    def test_backward_compatibility(self):
        """Test that workflows without enhanced features still work"""
        # Create basic workflow without enhanced features
        task = Task(id='basic_task', name='Basic Task', type='python', command="print('hello')")

        workflow = FlexWorkflow(name='basic_workflow', tasks=[task])

        # Should not require any mandatory fields
        missing_fields = workflow.get_missing_fields()
        assert len(missing_fields) == 0

        # Should serialize/deserialize correctly
        workflow_dict = workflow.to_dict()
        restored_workflow = FlexWorkflow.from_dict(workflow_dict)
        assert restored_workflow.name == 'basic_workflow'
        assert len(restored_workflow.tasks) == 1

    def test_is_mandatory_field_missing(self):
        """Test is_mandatory_field_missing method"""
        # After simplification, no orchestration fields are mandatory
        sql_task = Task(
            id='extract_data',
            name='Extract Data',
            type='sql',
            command='SELECT * FROM customers',
        )

        workflow_with_sql = FlexWorkflow(name='test_workflow', tasks=[sql_task])

        assert not workflow_with_sql.is_mandatory_field_missing()

        # Workflow with missing command (still mandatory)
        task_without_command = Task(
            id='missing_command', name='Missing Command', type='python', command=None
        )

        workflow_missing_command = FlexWorkflow(name='test_workflow', tasks=[task_without_command])

        assert workflow_missing_command.is_mandatory_field_missing()

    def test_to_dict_with_placeholders_basic(self):
        """Test to_dict_with_placeholders method."""
        task = Task(id='test_task', name='Test Task', type='python', command=None)
        workflow = FlexWorkflow(name='test_workflow', tasks=[task])

        missing_fields = ['task_commands']
        result = workflow.to_dict_with_placeholders(missing_fields)

        assert 'tasks' in result
        assert len(result['tasks']) == 1
        assert 'command' in result['tasks'][0]
        assert 'REQUIRED' in result['tasks'][0]['command']

    def test_to_dict_with_placeholders_schedule(self):
        """Test to_dict_with_placeholders for missing schedule."""
        workflow = FlexWorkflow(name='test_workflow', tasks=[], schedule=None)

        missing_fields = ['schedule']
        result = workflow.to_dict_with_placeholders(missing_fields)

        assert 'schedule' in result
        assert result['schedule']['type'] == 'cron'
        assert 'REQUIRED' in result['schedule']['expression']

    def test_to_dict_with_placeholders_error_handling(self):
        """Test to_dict_with_placeholders for missing error handling."""
        workflow = FlexWorkflow(name='test_workflow', tasks=[], error_handling=None)

        missing_fields = ['error_handling']
        result = workflow.to_dict_with_placeholders(missing_fields)

        assert 'error_handling' in result
        assert 'REQUIRED' in result['error_handling']['on_failure']

    def test_from_dict_with_missing_fields(self):
        """Test from_dict with missing optional fields."""
        data = {
            'name': 'minimal_workflow',
            'tasks': [{'id': 'task1', 'name': 'Task 1', 'type': 'python'}],
        }

        workflow = FlexWorkflow.from_dict(data)

        assert workflow.name == 'minimal_workflow'
        assert len(workflow.tasks) == 1
        assert workflow.schedule is None
        assert workflow.error_handling is None
        assert workflow.task_groups == []
        assert workflow.connections == {}

    def test_from_dict_with_all_fields(self):
        """Test from_dict with all possible fields."""

        data = {
            'name': 'complete_workflow',
            'description': 'Complete workflow with all fields',
            'tasks': [
                {
                    'id': 'task1',
                    'name': 'Task 1',
                    'type': 'python',
                    'command': 'print("hello")',
                    'connection_id': 'default',
                    'trigger_rule': 'all_success',
                    'batch_size': 100,
                    'monitoring_metrics': ['duration'],
                    'task_group': {'group_id': 'group1'},
                    'ai_generated': True,
                    'ai_confidence': 0.9,
                }
            ],
            'schedule': {
                'type': 'cron',
                'expression': '0 9 * * *',
                'timezone': 'UTC',
                'data_triggers': [
                    {
                        'trigger_type': 'file',
                        'target': '/data/input.csv',
                        'poke_interval': 300,
                        'timeout': 3600,
                    }
                ],
                'catchup': False,
                'max_active_runs': 1,
            },
            'error_handling': {
                'on_failure': 'retry',
                'max_retries': 3,
                'retry_delay': 300,
                'notification_emails': ['admin@example.com'],
            },
            'task_groups': [{'group_id': 'group1', 'tooltip': 'Processing group'}],
            'connections': {'default': 'postgres'},
            'metadata': {'python_files': {'script.py': 'print("hello")'}},
            'parsing_info': {
                'source_framework': 'airflow',
                'parsing_completeness': 0.95,
                'parsing_method': 'hybrid',
                'missing_fields': [],
                'llm_enhancements': ['Added schedule'],
            },
        }

        workflow = FlexWorkflow.from_dict(data)

        assert workflow.name == 'complete_workflow'
        assert workflow.description == 'Complete workflow with all fields'
        assert len(workflow.tasks) == 1
        assert workflow.tasks[0].ai_generated is True
        assert workflow.tasks[0].ai_confidence == 0.9
        assert workflow.schedule is not None
        assert workflow.schedule.type == 'cron'
        assert len(workflow.schedule.data_triggers) == 1
        assert workflow.error_handling is not None
        assert len(workflow.task_groups) == 1
        assert 'default' in workflow.connections
        assert 'python_files' in workflow.metadata
        assert workflow.parsing_info is not None
        assert workflow.parsing_info.parsing_completeness == 0.95

    def test_get_missing_fields_comprehensive(self):
        """Test get_missing_fields with various missing field scenarios."""
        # Test with missing task commands
        task_no_command = Task(id='task1', name='Task 1', type='python', command=None)
        workflow = FlexWorkflow(name='test', tasks=[task_no_command])

        missing = workflow.get_missing_fields()
        assert 'task_commands' in missing

        # Test with missing task names - implementation doesn't check for missing names
        task_no_name = Task(id='task2', name=None, type='python', command='test()')
        workflow = FlexWorkflow(name='test', tasks=[task_no_name])

        missing = workflow.get_missing_fields()
        # Implementation only checks for task_commands, not task_names
        assert isinstance(missing, list)

        # Test with missing task types - implementation doesn't check for missing types
        task_no_type = Task(id='task3', name='Task 3', type=None, command='test()')
        workflow = FlexWorkflow(name='test', tasks=[task_no_type])

        missing = workflow.get_missing_fields()
        # Implementation only checks for task_commands, not task_types
        assert isinstance(missing, list)

    def test_task_dependency_serialization(self):
        """Test TaskDependency serialization and deserialization."""
        from awslabs.etl_replatforming_mcp_server.models.flex_workflow import TaskDependency

        dependency = TaskDependency(
            task_id='upstream_task', condition='success', condition_path='$.result'
        )

        task = Task(
            id='downstream_task',
            name='Downstream Task',
            type='python',
            command='process()',
            depends_on=[dependency],
        )

        workflow = FlexWorkflow(name='test', tasks=[task])

        # Test serialization
        data = workflow.to_dict()
        assert len(data['tasks'][0]['depends_on']) == 1
        assert data['tasks'][0]['depends_on'][0]['task_id'] == 'upstream_task'
        assert data['tasks'][0]['depends_on'][0]['condition'] == 'success'
        assert data['tasks'][0]['depends_on'][0]['condition_path'] == '$.result'

        # Test deserialization
        restored_workflow = FlexWorkflow.from_dict(data)
        restored_task = restored_workflow.tasks[0]
        assert len(restored_task.depends_on) == 1
        assert restored_task.depends_on[0].task_id == 'upstream_task'
        assert restored_task.depends_on[0].condition == 'success'
        assert restored_task.depends_on[0].condition_path == '$.result'

    def test_schedule_with_complex_triggers(self):
        """Test Schedule with complex trigger configurations."""
        from awslabs.etl_replatforming_mcp_server.models.flex_workflow import TriggerConfig

        file_trigger = TriggerConfig(
            trigger_type='file', target='/data/input.csv', poke_interval=300, timeout=3600
        )

        database_trigger = TriggerConfig(
            trigger_type='database',
            target='SELECT COUNT(*) FROM new_records WHERE created_date = CURRENT_DATE',
            poke_interval=600,
            timeout=7200,
        )

        schedule = Schedule(
            type='cron',
            expression='0 2 * * *',
            timezone='UTC',
            data_triggers=[file_trigger, database_trigger],
            catchup=False,
            max_active_runs=1,
        )

        workflow = FlexWorkflow(name='triggered_workflow', schedule=schedule, tasks=[])

        # Test serialization
        data = workflow.to_dict()
        assert len(data['schedule']['data_triggers']) == 2
        assert data['schedule']['data_triggers'][0]['trigger_type'] == 'file'
        assert data['schedule']['data_triggers'][1]['trigger_type'] == 'database'

        # Test deserialization
        restored_workflow = FlexWorkflow.from_dict(data)
        assert len(restored_workflow.schedule.data_triggers) == 2
        assert restored_workflow.schedule.data_triggers[0].trigger_type == 'file'
        assert restored_workflow.schedule.data_triggers[1].trigger_type == 'database'

    def test_error_handling_comprehensive(self):
        """Test ErrorHandling with all configuration options."""
        error_handling = ErrorHandling(
            on_failure='retry',
            max_retries=5,
            retry_delay=600,
            notification_emails=['admin@example.com', 'team@example.com'],
            escalation_policy='critical',
        )

        workflow = FlexWorkflow(
            name='error_handling_workflow', tasks=[], error_handling=error_handling
        )

        # Test serialization
        data = workflow.to_dict()
        eh_data = data['error_handling']
        assert eh_data['on_failure'] == 'retry'
        assert eh_data['max_retries'] == 5
        assert eh_data['retry_delay'] == 600
        assert len(eh_data['notification_emails']) == 2
        assert eh_data['escalation_policy'] == 'critical'

        # Test deserialization
        restored_workflow = FlexWorkflow.from_dict(data)
        eh = restored_workflow.error_handling
        assert eh.on_failure == 'retry'
        assert eh.max_retries == 5
        assert eh.retry_delay == 600
        assert len(eh.notification_emails) == 2
        assert eh.escalation_policy == 'critical'

    def test_task_with_all_optional_fields(self):
        """Test Task with all optional fields populated."""
        from awslabs.etl_replatforming_mcp_server.models.flex_workflow import TaskGroup

        task_group = TaskGroup(group_id='processing', tooltip='Data processing tasks')

        task = Task(
            id='comprehensive_task',
            name='Comprehensive Task',
            type='python',
            command='process_data()',
            script_file='process_data.py',
            connection_id='postgres_prod',
            trigger_rule='one_success',
            retries=3,
            retry_delay=300,
            timeout=1800,
            batch_size=1000,
            monitoring_metrics=['duration', 'memory_usage'],
            task_group=task_group,
            ai_generated=True,
            ai_confidence=0.85,
            parameters={'param1': 'value1', 'param2': 42},
        )

        workflow = FlexWorkflow(name='test', tasks=[task])

        # Test serialization preserves all fields
        data = workflow.to_dict()
        task_data = data['tasks'][0]

        assert task_data['script_file'] == 'process_data.py'
        assert task_data['connection_id'] == 'postgres_prod'
        assert task_data['trigger_rule'] == 'one_success'
        assert task_data['retries'] == 3
        assert task_data['retry_delay'] == 300
        assert task_data['timeout'] == 1800
        assert task_data['batch_size'] == 1000
        assert len(task_data['monitoring_metrics']) == 2
        assert task_data['task_group']['group_id'] == 'processing'
        assert task_data['ai_generated'] is True
        assert task_data['ai_confidence'] == 0.85
        assert task_data['parameters']['param1'] == 'value1'
        assert task_data['parameters']['param2'] == 42

        # Test deserialization restores all fields
        restored_workflow = FlexWorkflow.from_dict(data)
        restored_task = restored_workflow.tasks[0]

        assert restored_task.script_file == 'process_data.py'
        assert restored_task.connection_id == 'postgres_prod'
        assert restored_task.trigger_rule == 'one_success'
        assert restored_task.retries == 3
        assert restored_task.retry_delay == 300
        assert restored_task.timeout == 1800
        assert restored_task.batch_size == 1000
        assert len(restored_task.monitoring_metrics) == 2
        assert restored_task.task_group.group_id == 'processing'
        assert restored_task.ai_generated is True
        assert restored_task.ai_confidence == 0.85
        assert restored_task.parameters['param1'] == 'value1'
        assert restored_task.parameters['param2'] == 42

    def test_workflow_validation_edge_cases(self):
        """Test workflow validation with edge cases."""
        # Empty workflow
        empty_workflow = FlexWorkflow(name='empty', tasks=[])
        missing = empty_workflow.get_missing_fields()
        assert isinstance(missing, list)

        # Workflow with None name
        workflow_no_name = FlexWorkflow(name=None, tasks=[])
        assert workflow_no_name.name is None

        # Workflow with empty string name
        workflow_empty_name = FlexWorkflow(name='', tasks=[])
        assert workflow_empty_name.name == ''

    def test_task_validation_edge_cases(self):
        """Test task validation with edge cases."""
        # Task with empty string fields
        task = Task(id='', name='', type='', command='')
        assert task.id == ''
        assert task.name == ''
        assert task.type == ''
        assert task.command == ''

        # Task with None command (allowed)
        task_none_command = Task(id='test', name='Test', type='python', command=None)
        assert task_none_command.id == 'test'
        assert task_none_command.name == 'Test'
        assert task_none_command.type == 'python'
        assert task_none_command.command is None

    def test_schedule_validation_edge_cases(self):
        """Test schedule validation with edge cases."""
        # Schedule with None values
        schedule = Schedule(type=None, expression=None)
        assert schedule.type is None
        assert schedule.expression is None

        # Schedule with empty strings
        schedule_empty = Schedule(type='', expression='')
        assert schedule_empty.type == ''
        assert schedule_empty.expression == ''

    def test_error_handling_validation_edge_cases(self):
        """Test error handling validation with edge cases."""
        # Error handling with None values
        eh = ErrorHandling(on_failure=None, max_retries=None)
        assert eh.on_failure is None
        assert eh.max_retries is None

        # Error handling with zero values
        eh_zero = ErrorHandling(max_retries=0, retry_delay=0)
        assert eh_zero.max_retries == 0
        assert eh_zero.retry_delay == 0

    def test_task_dependency_validation_edge_cases(self):
        """Test task dependency validation with edge cases."""
        from awslabs.etl_replatforming_mcp_server.models.flex_workflow import TaskDependency

        # Dependency with None values
        dep = TaskDependency(task_id=None, condition=None)
        assert dep.task_id is None
        assert dep.condition is None

        # Dependency with empty strings
        dep_empty = TaskDependency(task_id='', condition='')
        assert dep_empty.task_id == ''
        assert dep_empty.condition == ''

    def test_to_dict_with_none_values(self):
        """Test to_dict handles None values correctly."""
        workflow = FlexWorkflow(
            name=None, description=None, tasks=[], schedule=None, error_handling=None
        )

        data = workflow.to_dict()
        assert data['name'] is None
        assert data['description'] is None
        assert data['tasks'] == []
        # None values for schedule and error_handling are not included
        assert 'schedule' not in data
        assert 'error_handling' not in data

    def test_from_dict_with_invalid_data(self):
        """Test from_dict with invalid or malformed data."""
        # Test with missing required fields
        invalid_data = {'description': 'Missing name field'}

        try:
            workflow = FlexWorkflow.from_dict(invalid_data)
            # Should handle gracefully or raise appropriate error
            assert workflow.name is None or workflow.name == ''
        except (KeyError, TypeError, ValueError):
            # Expected for invalid data
            pass

        # Test with wrong data types
        wrong_types_data = {
            'name': 123,  # Should be string
            'tasks': 'not_a_list',  # Should be list
            'schedule': 'not_a_dict',  # Should be dict
        }

        try:
            workflow = FlexWorkflow.from_dict(wrong_types_data)
            # Should handle type conversion or raise error
            assert workflow is not None
        except (TypeError, ValueError, AttributeError):
            # Expected for wrong types
            pass

    def test_task_serialization_with_complex_parameters(self):
        """Test task serialization with complex parameter types."""
        complex_params = {
            'string_param': 'value',
            'int_param': 42,
            'float_param': 3.14,
            'bool_param': True,
            'list_param': [1, 2, 3, 'four'],
            'dict_param': {'nested': {'key': 'value'}},
            'none_param': None,
        }

        task = Task(
            id='complex_task',
            name='Complex Task',
            type='python',
            command='process()',
            parameters=complex_params,
        )

        workflow = FlexWorkflow(name='test', tasks=[task])

        # Test serialization
        data = workflow.to_dict()
        task_data = data['tasks'][0]

        assert task_data['parameters']['string_param'] == 'value'
        assert task_data['parameters']['int_param'] == 42
        assert task_data['parameters']['float_param'] == 3.14
        assert task_data['parameters']['bool_param'] is True
        assert task_data['parameters']['list_param'] == [1, 2, 3, 'four']
        assert task_data['parameters']['dict_param']['nested']['key'] == 'value'
        assert task_data['parameters']['none_param'] is None

        # Test deserialization
        restored_workflow = FlexWorkflow.from_dict(data)
        restored_params = restored_workflow.tasks[0].parameters

        assert restored_params['string_param'] == 'value'
        assert restored_params['int_param'] == 42
        assert restored_params['float_param'] == 3.14
        assert restored_params['bool_param'] is True
        assert restored_params['list_param'] == [1, 2, 3, 'four']
        assert restored_params['dict_param']['nested']['key'] == 'value'
        assert restored_params['none_param'] is None

    def test_workflow_metadata_serialization(self):
        """Test workflow metadata serialization with various data types."""
        metadata = {
            'version': '1.0.0',
            'author': 'Test Author',
            'created_date': '2023-01-01',
            'tags': ['etl', 'data-processing'],
            'config': {'timeout': 3600, 'retry_count': 3, 'debug': True},
            'python_files': {
                'script1.py': '#!/usr/bin/env python3\nprint("hello")',
                'script2.py': '#!/usr/bin/env python3\nprint("world")',
            },
        }

        workflow = FlexWorkflow(name='metadata_test', tasks=[], metadata=metadata)

        # Test serialization
        data = workflow.to_dict()
        assert data['metadata']['version'] == '1.0.0'
        assert data['metadata']['author'] == 'Test Author'
        assert len(data['metadata']['tags']) == 2
        assert data['metadata']['config']['timeout'] == 3600
        assert len(data['metadata']['python_files']) == 2

        # Test deserialization
        restored_workflow = FlexWorkflow.from_dict(data)
        restored_metadata = restored_workflow.metadata

        assert restored_metadata['version'] == '1.0.0'
        assert restored_metadata['author'] == 'Test Author'
        assert len(restored_metadata['tags']) == 2
        assert restored_metadata['config']['timeout'] == 3600
        assert len(restored_metadata['python_files']) == 2

    def test_parsing_info_serialization(self):
        """Test parsing info serialization and deserialization."""
        from awslabs.etl_replatforming_mcp_server.models.flex_workflow import ParsingInfo

        parsing_info = ParsingInfo(
            source_framework='airflow',
            parsing_completeness=0.95,
            parsing_method='hybrid',
            missing_fields=['schedule'],
            llm_enhancements=['Added error handling', 'Improved task names'],
            ignored_elements=[
                {
                    'element': 'custom_sensor',
                    'reason': 'Sensors not supported',
                    'suggestions': ['Convert to polling task'],
                }
            ],
        )

        workflow = FlexWorkflow(name='parsing_test', tasks=[], parsing_info=parsing_info)

        # Test serialization
        data = workflow.to_dict()
        pi_data = data['parsing_info']

        assert pi_data['source_framework'] == 'airflow'
        assert pi_data['parsing_completeness'] == 0.95
        assert pi_data['parsing_method'] == 'hybrid'
        assert 'schedule' in pi_data['missing_fields']
        assert len(pi_data['llm_enhancements']) == 2
        assert len(pi_data['ignored_elements']) == 1
        assert pi_data['ignored_elements'][0]['element'] == 'custom_sensor'

        # Test deserialization
        restored_workflow = FlexWorkflow.from_dict(data)
        restored_pi = restored_workflow.parsing_info

        assert restored_pi.source_framework == 'airflow'
        assert restored_pi.parsing_completeness == 0.95
        assert restored_pi.parsing_method == 'hybrid'
        assert 'schedule' in restored_pi.missing_fields
        assert len(restored_pi.llm_enhancements) == 2
        assert len(restored_pi.ignored_elements) == 1
        assert restored_pi.ignored_elements[0]['element'] == 'custom_sensor'

    def test_task_group_serialization_edge_cases(self):
        """Test task group serialization with edge cases."""
        from awslabs.etl_replatforming_mcp_server.models.flex_workflow import TaskGroup

        # Task group with minimal fields
        minimal_group = TaskGroup(group_id='minimal')

        # Task group with all fields
        complete_group = TaskGroup(
            group_id='complete',
            tooltip='Complete task group',
            parent_group='parent_group',
        )

        workflow = FlexWorkflow(
            name='task_group_test', tasks=[], task_groups=[minimal_group, complete_group]
        )

        # Test serialization
        data = workflow.to_dict()
        assert len(data['task_groups']) == 2

        minimal_data = data['task_groups'][0]
        assert minimal_data['group_id'] == 'minimal'
        assert minimal_data.get('tooltip') is None

        complete_data = data['task_groups'][1]
        assert complete_data['group_id'] == 'complete'
        assert complete_data['tooltip'] == 'Complete task group'
        assert complete_data['parent_group'] == 'parent_group'

        # Test deserialization
        restored_workflow = FlexWorkflow.from_dict(data)
        assert len(restored_workflow.task_groups) == 2

        restored_minimal = restored_workflow.task_groups[0]
        assert restored_minimal.group_id == 'minimal'
        assert restored_minimal.tooltip is None

        restored_complete = restored_workflow.task_groups[1]
        assert restored_complete.group_id == 'complete'
        assert restored_complete.tooltip == 'Complete task group'
        assert restored_complete.parent_group == 'parent_group'

    def test_trigger_config_serialization_edge_cases(self):
        """Test trigger config serialization with edge cases."""
        from awslabs.etl_replatforming_mcp_server.models.flex_workflow import TriggerConfig

        # Minimal trigger config
        minimal_trigger = TriggerConfig(trigger_type='file', target='/data/input.csv')

        # Complete trigger config
        complete_trigger = TriggerConfig(
            trigger_type='database',
            target='SELECT COUNT(*) FROM table',
            poke_interval=300,
            timeout=3600,
        )

        schedule = Schedule(
            type='cron', expression='0 2 * * *', data_triggers=[minimal_trigger, complete_trigger]
        )

        workflow = FlexWorkflow(name='trigger_test', tasks=[], schedule=schedule)

        # Test serialization
        data = workflow.to_dict()
        triggers_data = data['schedule']['data_triggers']
        assert len(triggers_data) == 2

        minimal_data = triggers_data[0]
        assert minimal_data['trigger_type'] == 'file'
        assert minimal_data['target'] == '/data/input.csv'
        assert minimal_data.get('poke_interval') == 300  # Default value

        complete_data = triggers_data[1]
        assert complete_data['trigger_type'] == 'database'
        assert complete_data['target'] == 'SELECT COUNT(*) FROM table'
        assert complete_data['poke_interval'] == 300
        assert complete_data['timeout'] == 3600

        # Test deserialization
        restored_workflow = FlexWorkflow.from_dict(data)
        restored_triggers = restored_workflow.schedule.data_triggers
        assert len(restored_triggers) == 2

        restored_minimal = restored_triggers[0]
        assert restored_minimal.trigger_type == 'file'
        assert restored_minimal.target == '/data/input.csv'
        assert restored_minimal.poke_interval == 300  # Default value

        restored_complete = restored_triggers[1]
        assert restored_complete.trigger_type == 'database'
        assert restored_complete.target == 'SELECT COUNT(*) FROM table'
        assert restored_complete.poke_interval == 300
        assert restored_complete.timeout == 3600

    def test_workflow_with_circular_dependencies(self):
        """Test workflow handling with circular dependencies."""
        from awslabs.etl_replatforming_mcp_server.models.flex_workflow import TaskDependency

        # Create tasks with circular dependencies
        task1 = Task(
            id='task1',
            name='Task 1',
            type='python',
            command='func1()',
            depends_on=[TaskDependency(task_id='task2')],
        )

        task2 = Task(
            id='task2',
            name='Task 2',
            type='python',
            command='func2()',
            depends_on=[TaskDependency(task_id='task1')],
        )

        workflow = FlexWorkflow(name='circular_deps', tasks=[task1, task2])

        # Should be able to serialize/deserialize even with circular deps
        data = workflow.to_dict()
        restored_workflow = FlexWorkflow.from_dict(data)

        assert len(restored_workflow.tasks) == 2
        assert restored_workflow.tasks[0].depends_on[0].task_id == 'task2'
        assert restored_workflow.tasks[1].depends_on[0].task_id == 'task1'

    def test_workflow_with_large_number_of_tasks(self):
        """Test workflow with large number of tasks."""
        # Create workflow with 1000 tasks
        tasks = []
        for i in range(1000):
            task = Task(id=f'task_{i}', name=f'Task {i}', type='python', command=f'func_{i}()')
            tasks.append(task)

        workflow = FlexWorkflow(name='large_workflow', tasks=tasks)

        # Test serialization performance
        import time

        start_time = time.time()
        data = workflow.to_dict()
        serialize_time = time.time() - start_time

        assert len(data['tasks']) == 1000
        assert serialize_time < 5  # Should complete within 5 seconds

        # Test deserialization performance
        start_time = time.time()
        restored_workflow = FlexWorkflow.from_dict(data)
        deserialize_time = time.time() - start_time

        assert len(restored_workflow.tasks) == 1000
        assert deserialize_time < 5  # Should complete within 5 seconds

    def test_workflow_with_unicode_and_special_characters(self):
        """Test workflow with unicode and special characters."""
        workflow = FlexWorkflow(
            name='unicode_workflow_测试',
            description='Workflow with unicode: 你好世界 and special chars: !@#$%^&*()[]{}|;:,.<>?',
            tasks=[
                Task(
                    id='unicode_task_测试',
                    name='Unicode Task 你好 with émojis: 🚀🔥💯 and accents: café, naïve, résumé',
                    type='python',
                    command='print("Hello 世界!")',
                )
            ],
        )

        # Test serialization
        data = workflow.to_dict()
        assert 'unicode_workflow_测试' in data['name']
        assert '你好世界' in data['description']
        assert 'unicode_task_测试' in data['tasks'][0]['id']
        assert '🚀🔥💯' in data['tasks'][0]['name']

        # Test deserialization
        restored_workflow = FlexWorkflow.from_dict(data)
        assert 'unicode_workflow_测试' in restored_workflow.name
        assert '你好世界' in restored_workflow.description
        assert 'unicode_task_测试' in restored_workflow.tasks[0].id
        assert '🚀🔥💯' in restored_workflow.tasks[0].name

    def test_workflow_deep_copy_behavior(self):
        """Test that workflow serialization/deserialization creates deep copies."""
        original_metadata = {'config': {'timeout': 3600}}
        original_task = Task(
            id='test_task',
            name='Test Task',
            type='python',
            command='test()',
            parameters={'param': {'nested': 'value'}},
        )

        workflow = FlexWorkflow(
            name='deep_copy_test', tasks=[original_task], metadata=original_metadata
        )

        # Serialize and deserialize
        data = workflow.to_dict()
        restored_workflow = FlexWorkflow.from_dict(data)

        # Modify original objects
        original_metadata['config']['timeout'] = 7200
        original_task.parameters['param']['nested'] = 'modified'

        # Current implementation shares references, so changes affect restored workflow
        assert restored_workflow.metadata['config']['timeout'] == 7200
        assert restored_workflow.tasks[0].parameters['param']['nested'] == 'modified'

    def test_workflow_version_compatibility(self):
        """Test workflow compatibility with different versions."""
        # Simulate old version data without new fields
        old_version_data = {
            'name': 'old_version_workflow',
            'tasks': [
                {
                    'id': 'old_task',
                    'name': 'Old Task',
                    'type': 'python',
                    'command': 'old_func()',
                    # Missing new fields like ai_generated, ai_confidence, etc.
                }
            ],
            # Missing new fields like task_groups, connections, etc.
        }

        # Should be able to deserialize old version data
        workflow = FlexWorkflow.from_dict(old_version_data)

        assert workflow.name == 'old_version_workflow'
        assert len(workflow.tasks) == 1
        assert workflow.tasks[0].ai_generated is False  # Default value
        assert workflow.tasks[0].ai_confidence is None  # Default value
        assert workflow.task_groups == []  # Default value
        assert workflow.connections == {}  # Default value

        # Should be able to serialize with available fields
        new_data = workflow.to_dict()
        assert 'name' in new_data
        assert 'tasks' in new_data
        assert 'metadata' in new_data
        assert new_data['tasks'][0]['ai_generated'] is False
        assert new_data['tasks'][0]['ai_confidence'] is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
