import json

import pytest

from awslabs.etl_replatforming_mcp_server.models.exceptions import ParsingError
from awslabs.etl_replatforming_mcp_server.parsers.step_functions_parser import StepFunctionsParser


class TestStepFunctionsParserEfficient:
    """Efficient test cases for Step Functions parser maintaining 92% coverage"""

    def setup_method(self):
        self.parser = StepFunctionsParser()

    def test_parse_basic_state_machine_complete_flow(self):
        """Test complete state machine parsing flow - covers main parsing logic"""
        basic_state_machine = {
            'Comment': 'Basic ETL Pipeline',
            'StartAt': 'ExtractData',
            'States': {
                'ExtractData': {
                    'Type': 'Task',
                    'Resource': 'arn:aws:states:::aws-sdk:redshiftdata:executeStatement',
                    'Parameters': {'Sql': 'SELECT * FROM source_table'},
                    'End': True,
                }
            },
        }

        result = self.parser.parse_code(json.dumps(basic_state_machine))
        assert result.name == 'basic_etl_pipeline'
        assert result.description == 'Basic ETL Pipeline'
        assert len(result.tasks) == 1
        assert result.tasks[0].id == 'ExtractData'
        assert result.tasks[0].type == 'sql'

    def test_parse_all_task_types(self):
        """Test parsing all major task types - covers task type mapping"""
        all_tasks_machine = {
            'StartAt': 'LambdaTask',
            'States': {
                'LambdaTask': {
                    'Type': 'Task',
                    'Resource': 'arn:aws:states:::lambda:invoke',
                    'Parameters': {'FunctionName': 'my-function'},
                    'Next': 'BatchTask',
                },
                'BatchTask': {
                    'Type': 'Task',
                    'Resource': 'arn:aws:states:::batch:submitJob',
                    'Parameters': {'JobDefinition': 'my-job', 'JobQueue': 'my-queue'},
                    'Next': 'RedshiftTask',
                },
                'RedshiftTask': {
                    'Type': 'Task',
                    'Resource': 'arn:aws:states:::aws-sdk:redshiftdata:executeStatement',
                    'Parameters': {
                        'Sql': 'SELECT * FROM customers',
                        'ClusterIdentifier': 'cluster',
                    },
                    'Next': 'SNSTask',
                },
                'SNSTask': {
                    'Type': 'Task',
                    'Resource': 'arn:aws:states:::sns:publish',
                    'Parameters': {'Message': 'Hello World', 'TopicArn': 'arn:aws:sns:topic'},
                    'Next': 'S3Task',
                },
                'S3Task': {
                    'Type': 'Task',
                    'Resource': 'arn:aws:states:::s3:getObject',
                    'Parameters': {'Bucket': 'my-bucket', 'Key': 'data/file.csv'},
                    'Next': 'GenericTask',
                },
                'GenericTask': {
                    'Type': 'Task',
                    'Resource': 'arn:aws:states:::dynamodb:putItem',
                    'End': True,
                },
            },
        }

        result = self.parser.parse_code(json.dumps(all_tasks_machine))
        assert len(result.tasks) == 6

        # Verify task type mappings
        task_types = {task.id: task.type for task in result.tasks}
        assert task_types['LambdaTask'] == 'python'
        assert task_types['BatchTask'] == 'container'
        assert task_types['RedshiftTask'] == 'sql'
        assert task_types['SNSTask'] == 'email'
        assert task_types['S3Task'] == 'file_transfer'
        assert task_types['GenericTask'] == 'bash'

    def test_parse_control_flow_states(self):
        """Test parsing Choice, Map, Parallel, and Pass states - covers control flow logic"""
        control_flow_machine = {
            'StartAt': 'ChoiceState',
            'States': {
                'ChoiceState': {
                    'Type': 'Choice',
                    'Choices': [
                        {'Variable': '$.count', 'NumericGreaterThan': 10, 'Next': 'MapState'},
                        {'Variable': '$.status', 'StringEquals': 'success', 'Next': 'PassState'},
                    ],
                    'Default': 'ParallelState',
                },
                'MapState': {
                    'Type': 'Map',
                    'ItemsPath': '$.items',
                    'MaxConcurrency': 5,
                    'Iterator': {
                        'StartAt': 'ProcessItem',
                        'States': {
                            'ProcessItem': {
                                'Type': 'Task',
                                'Resource': 'arn:aws:states:::lambda:invoke',
                                'End': True,
                            }
                        },
                    },
                    'End': True,
                },
                'ParallelState': {
                    'Type': 'Parallel',
                    'Branches': [
                        {
                            'StartAt': 'Branch1Task',
                            'States': {
                                'Branch1Task': {
                                    'Type': 'Task',
                                    'Resource': 'arn:aws:states:::lambda:invoke',
                                    'End': True,
                                }
                            },
                        }
                    ],
                    'End': True,
                },
                'PassState': {
                    'Type': 'Pass',
                    'Result': {'message': 'Hello'},
                    'End': True,
                },
            },
        }

        result = self.parser.parse_code(json.dumps(control_flow_machine))

        # Verify control flow states
        task_types = {task.id: task.type for task in result.tasks}
        assert task_types['ChoiceState'] == 'branch'
        assert task_types['MapState'] == 'for_each'
        assert task_types['ParallelState'] == 'bash'
        assert task_types['PassState'] == 'bash'

        # Verify Map state loop configuration
        map_task = next(task for task in result.tasks if task.id == 'MapState')
        assert map_task.loop is not None
        assert map_task.loop.max_concurrency == 5

    def test_parse_choice_conditions_comprehensive(self):
        """Test all choice condition types - covers choice condition parsing"""
        # Test basic conditions
        basic_conditions = [
            {'Variable': '$.count', 'NumericGreaterThan': 10, 'Next': 'Task1'},
            {'Variable': '$.value', 'NumericLessThan': 5, 'Next': 'Task2'},
            {'Variable': '$.status', 'NumericEquals': 200, 'Next': 'Task3'},
            {'Variable': '$.isValid', 'BooleanEquals': True, 'Next': 'Task4'},
            {'Variable': '$.type', 'StringEquals': 'success', 'Next': 'Task5'},
        ]

        for choice in basic_conditions:
            condition = self.parser._extract_choice_condition(choice)
            assert 'output.' in condition

        # Test AND condition
        and_choice = {
            'And': [
                {'Variable': '$.count', 'NumericGreaterThan': 0},
                {'Variable': '$.status', 'StringEquals': 'active'},
            ],
            'Next': 'Process',
        }
        and_condition = self.parser._extract_choice_condition(and_choice)
        assert 'AND' in and_condition
        assert 'output.count > 0' in and_condition
        assert 'output.status == "active"' in and_condition

        # Test OR condition
        or_choice = {
            'Or': [
                {'Variable': '$.type', 'StringEquals': 'error'},
                {'Variable': '$.type', 'StringEquals': 'warning'},
            ],
            'Next': 'HandleIssue',
        }
        or_condition = self.parser._extract_choice_condition(or_choice)
        assert 'OR' in or_condition
        assert 'output.type == "error"' in or_condition

        # Test nested AND/OR
        nested_choice = {
            'And': [
                {
                    'Or': [
                        {'Variable': '$.type', 'StringEquals': 'A'},
                        {'Variable': '$.type', 'StringEquals': 'B'},
                    ]
                },
                {'Variable': '$.count', 'NumericGreaterThan': 0},
            ],
            'Next': 'Process',
        }
        nested_condition = self.parser._extract_choice_condition(nested_choice)
        assert 'AND' in nested_condition and 'OR' in nested_condition

        # Test unknown condition
        unknown_choice = {'UnknownCondition': 'value', 'Next': 'Task'}
        unknown_condition = self.parser._extract_choice_condition(unknown_choice)
        assert unknown_condition == 'unknown_condition'

    def test_parse_dependencies_and_connections(self):
        """Test dependency parsing and connection extraction - covers dependency logic"""
        dependency_machine = {
            'StartAt': 'Task1',
            'States': {
                'Task1': {
                    'Type': 'Task',
                    'Resource': 'arn:aws:states:::lambda:invoke',
                    'Next': 'ChoiceState',
                },
                'ChoiceState': {
                    'Type': 'Choice',
                    'Choices': [
                        {'Variable': '$.result', 'StringEquals': 'success', 'Next': 'Task2'}
                    ],
                    'Default': 'Task3',
                },
                'Task2': {
                    'Type': 'Task',
                    'Resource': 'arn:aws:states:::aws-sdk:redshiftdata:executeStatement',
                    'End': True,
                },
                'Task3': {
                    'Type': 'Task',
                    'Resource': 'arn:aws:states:::batch:submitJob',
                    'End': True,
                },
            },
        }

        # Test dependencies
        deps = self.parser.parse_dependencies(dependency_machine)
        assert len(deps) == 1
        assert deps[0].task_id == 'Task1'

        # Test connections
        connections = self.parser.parse_connections(dependency_machine)
        assert 'lambda_service' in connections
        assert connections['lambda_service'] == 'lambda'
        assert 'redshift_data' in connections
        assert connections['redshift_data'] == 'redshift'
        assert 'batch_service' in connections
        assert connections['batch_service'] == 'batch'

    def test_parse_task_with_retry_and_timeout(self):
        """Test task parsing with retry and timeout configurations - covers retry/timeout logic"""
        task_with_config = {
            'Type': 'Task',
            'Resource': 'arn:aws:states:::lambda:invoke',
            'Parameters': {'FunctionName': 'test-function', 'MaxConcurrency': 10, 'BatchSize': 5},
            'Retry': [
                {'ErrorEquals': ['States.TaskFailed'], 'MaxAttempts': 2, 'IntervalSeconds': 30},
                {'ErrorEquals': ['States.ALL'], 'MaxAttempts': 5, 'IntervalSeconds': 60},
            ],
            'TimeoutSeconds': 300,
        }

        task = self.parser._convert_state_to_task('TestTask', task_with_config, {})
        assert task.retries == 2  # Uses first retry config
        assert task.retry_delay == 30
        assert task.timeout == 300
        assert task.batch_size == 10  # MaxConcurrency takes precedence over BatchSize

    def test_parse_map_state_variations(self):
        """Test Map state with different ItemsPath configurations - covers Map state logic"""
        # Test different ItemsPath patterns
        test_cases = [
            ('$.static.items', 'static'),
            ('$.range.values', 'range'),
            ('$.fileList.files', 'task_output'),
            ('$.items', 'static'),
            ('$', 'static'),
            (None, 'static'),  # No ItemsPath
        ]

        for items_path, expected_source in test_cases:
            state_def = {'Type': 'Map', 'MaxConcurrency': 3}
            if items_path:
                state_def['ItemsPath'] = items_path

            task = self.parser._convert_state_to_task('MapTask', state_def, {})
            assert task.loop.items.source == expected_source
            if expected_source == 'task_output' and items_path:
                assert task.loop.items.path == f'output.{items_path[2:]}'  # Remove '$.'

    def test_parse_edge_cases_and_missing_fields(self):
        """Test parsing with missing fields and edge cases - covers error handling"""
        # Test missing States
        result = self.parser.parse_code('{"Comment": "Invalid", "StartAt": "Task1"}')
        assert result.name == 'invalid'
        assert len(result.tasks) == 0

        # Test missing StartAt
        result = self.parser.parse_code(
            '{"Comment": "Invalid", "States": {"Task1": {"Type": "Task", "End": true}}}'
        )
        assert len(result.tasks) == 1

        # Test unknown state type
        state_def = {'Type': 'UnknownType'}
        task = self.parser._convert_state_to_task('UnknownTask', state_def, {})
        assert task.type == 'bash'
        assert task.command == 'echo "Unknown state type"'

    def test_parse_metadata_variations(self):
        """Test metadata parsing with various field combinations - covers metadata logic"""
        # Test with all fields
        metadata = self.parser.parse_metadata({'Comment': 'Test Workflow', 'StartAt': 'FirstTask'})
        assert metadata['name'] == 'Test Workflow'
        assert metadata['description'] == 'Test Workflow'
        assert metadata['start_at'] == 'FirstTask'

        # Test without Comment
        metadata = self.parser.parse_metadata({'StartAt': 'FirstTask'})
        assert metadata['name'] == 'step_functions_workflow'
        assert metadata['description'] is None

        # Test with empty Comment
        metadata = self.parser.parse_metadata({'Comment': '', 'StartAt': 'FirstTask'})
        assert metadata['name'] == ''
        assert metadata['description'] == ''

    def test_extract_all_states_with_parallel_branches(self):
        """Test extracting all states including parallel branches - covers state extraction logic"""
        states = {
            'ParallelState': {
                'Type': 'Parallel',
                'Branches': [
                    {
                        'StartAt': 'Branch1Task',
                        'States': {
                            'Branch1Task': {
                                'Type': 'Task',
                                'Resource': 'arn:aws:states:::lambda:invoke',
                                'End': True,
                            }
                        },
                    },
                    {
                        'StartAt': 'Branch2Task',
                        'States': {
                            'Branch1Task': {  # Same name as branch 1 - should be renamed
                                'Type': 'Task',
                                'Resource': 'arn:aws:states:::lambda:invoke',
                                'End': True,
                            }
                        },
                    },
                ],
            }
        }

        all_states = self.parser._extract_all_states(states)
        assert 'ParallelState' in all_states
        assert 'Branch1Task' in all_states
        assert 'Branch1Task_1' in all_states  # Renamed for uniqueness

    def test_find_dependencies_variations(self):
        """Test finding dependencies with different transition types - covers dependency finding logic"""
        # Test with Next transitions
        all_states = {
            'Task1': {
                'Type': 'Task',
                'Resource': 'arn:aws:states:::lambda:invoke',
                'Next': 'Task2',
            },
            'Task2': {'Type': 'Task', 'Resource': 'arn:aws:states:::lambda:invoke', 'End': True},
        }
        deps = self.parser._find_dependencies('Task2', all_states)
        assert len(deps) == 1
        assert deps[0].task_id == 'Task1'
        assert deps[0].condition == 'success'

        # Test with Choice state
        all_states = {
            'ChoiceState': {
                'Type': 'Choice',
                'Choices': [{'Variable': '$.count', 'NumericGreaterThan': 10, 'Next': 'Task1'}],
                'Default': 'Task2',
            },
            'Task1': {'Type': 'Task', 'Resource': 'arn:aws:states:::lambda:invoke', 'End': True},
        }
        deps = self.parser._find_dependencies('Task1', all_states)
        assert len(deps) == 1
        assert deps[0].task_id == 'ChoiceState'

    def test_extract_connection_from_resource(self):
        """Test extracting connection IDs from resource ARNs - covers connection extraction logic"""
        test_cases = [
            ('arn:aws:states:::aws-sdk:redshiftdata:executeStatement', 'redshift_data'),
            ('arn:aws:states:::lambda:invoke', 'lambda_service'),
            ('arn:aws:states:::batch:submitJob', 'batch_service'),
            ('arn:aws:states:::sns:publish', 'sns_service'),
            ('arn:aws:states:::s3:getObject', 's3_service'),
            ('', None),
            ('unknown:resource', None),
        ]

        for resource, expected in test_cases:
            result = self.parser._extract_connection_from_resource(resource)
            assert result == expected

    def test_framework_detection_and_validation(self):
        """Test framework detection and input validation - covers validation logic"""
        # Valid Step Functions JSON
        assert self.parser.detect_framework('{"StartAt": "Task1", "States": {}}') is True
        assert self.parser.validate_input('{"States": {}, "StartAt": "Task1"}') is True

        # Invalid cases
        assert self.parser.detect_framework('invalid json') is False
        assert self.parser.detect_framework('{"no_states": true}') is False
        assert self.parser.detect_framework('') is False
        assert self.parser.detect_framework(None) is False

        assert self.parser.validate_input('invalid') is False
        assert self.parser.validate_input('{"no_states": true}') is False
        assert self.parser.validate_input(None) is False

    def test_error_handling(self):
        """Test error handling for invalid inputs - covers exception handling"""
        # Invalid JSON should raise ParsingError
        with pytest.raises(ParsingError):
            self.parser.parse_code('not valid json {')

        with pytest.raises(ParsingError):
            self.parser.parse_code('')

    def test_parsing_completeness_calculation(self):
        """Test parsing completeness calculation - covers completeness logic"""
        from awslabs.etl_replatforming_mcp_server.models.flex_workflow import (
            FlexWorkflow,
            Task,
            TaskDependency,
        )

        # Test with complete workflow
        workflow = FlexWorkflow(
            name='test',
            tasks=[
                Task(
                    id='task1',
                    name='Task 1',
                    type='python',
                    command='test',
                    depends_on=[TaskDependency(task_id='task0')],
                )
            ],
        )
        completeness = self.parser.get_parsing_completeness(workflow)
        assert completeness == 1.0

        # Test empty workflow
        empty_workflow = FlexWorkflow(name='empty', tasks=[])
        completeness = self.parser.get_parsing_completeness(empty_workflow)
        assert completeness == 0.3333333333333333

    def test_abstract_base_methods(self):
        """Test abstract base class methods - covers base class implementation"""
        source_data = {'StartAt': 'Task1', 'States': {}}

        # Test methods that return None or empty collections
        assert self.parser.parse_schedule(source_data) is None
        assert self.parser.parse_error_handling(source_data) is None
        assert self.parser.parse_loops(source_data) == {}
        assert self.parser.parse_trigger_rules(source_data) == {}
        assert self.parser.parse_data_triggers(source_data) == []

        # Test methods that return actual data
        choice_data = {
            'States': {
                'ChoiceState': {
                    'Type': 'Choice',
                    'Choices': [{'Next': 'Task1'}],
                    'Default': 'Task2',
                }
            }
        }
        choice_tasks = self.parser.parse_conditional_logic(choice_data)
        assert len(choice_tasks) == 1
        assert choice_tasks[0].type == 'branch'

        parallel_data = {
            'States': {'ParallelState': {'Type': 'Parallel', 'Branches': [], 'End': True}}
        }
        parallel_tasks = self.parser.parse_parallel_execution(parallel_data)
        assert len(parallel_tasks) == 1
        assert parallel_tasks[0].type == 'bash'

    def test_task_groups_parsing(self):
        """Test task group parsing for parallel states - covers task group logic"""
        source_data = {
            'States': {
                'ParallelState': {
                    'Type': 'Parallel',
                    'Branches': [
                        {'StartAt': 'Task1', 'States': {}},
                        {'StartAt': 'Task2', 'States': {}},
                    ],
                }
            }
        }
        task_groups = self.parser.parse_task_groups(source_data)
        assert len(task_groups) == 2
        assert task_groups[0].group_id == 'ParallelState_branch_0'
        assert task_groups[1].group_id == 'ParallelState_branch_1'

    def test_comprehensive_task_parameter_extraction(self):
        """Test task parameter extraction for different resource types - covers parameter extraction"""
        # Test Redshift task without parameters
        redshift_no_params = {
            'Type': 'Task',
            'Resource': 'arn:aws:states:::aws-sdk:redshiftdata:executeStatement',
            'End': True,
        }
        task = self.parser._convert_state_to_task('RedshiftTask', redshift_no_params, {})
        assert task.type == 'sql'
        assert task.command == ''
        assert task.connection_id == 'redshift_data'

        # Test Lambda with payload
        lambda_with_payload = {
            'Type': 'Task',
            'Resource': 'arn:aws:states:::lambda:invoke',
            'Parameters': {'FunctionName': 'my-function', 'Payload': {'key': 'value'}},
            'End': True,
        }
        task = self.parser._convert_state_to_task('LambdaTask', lambda_with_payload, {})
        assert task.type == 'python'
        assert 'my-function' in task.command

        # Test task without retry configuration
        no_retry_task = {
            'Type': 'Task',
            'Resource': 'arn:aws:states:::lambda:invoke',
            'Parameters': {'FunctionName': 'test-function'},
        }
        task = self.parser._convert_state_to_task('TestTask', no_retry_task, {})
        assert task.retries == 0
        assert task.retry_delay == 300  # Default
        assert task.timeout is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
