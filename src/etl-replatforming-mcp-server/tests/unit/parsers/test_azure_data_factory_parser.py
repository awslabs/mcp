import json

import pytest

from awslabs.etl_replatforming_mcp_server.models.exceptions import ParsingError
from awslabs.etl_replatforming_mcp_server.parsers.azure_data_factory_parser import (
    AzureDataFactoryParser,
)


class TestAzureDataFactoryParserEfficient:
    """Efficient test cases for Azure Data Factory parser maintaining 95% coverage"""

    def setup_method(self):
        self.parser = AzureDataFactoryParser()

    def test_parse_basic_pipeline_complete_flow(self):
        """Test complete pipeline parsing flow - covers main parsing logic"""
        basic_pipeline = {
            'name': 'BasicETLPipeline',
            'properties': {
                'description': 'Basic ETL pipeline',
                'activities': [
                    {
                        'name': 'CopyData',
                        'type': 'Copy',
                        'inputs': [{'referenceName': 'SourceDataset', 'type': 'DatasetReference'}],
                        'outputs': [{'referenceName': 'SinkDataset', 'type': 'DatasetReference'}],
                        'typeProperties': {
                            'source': {
                                'type': 'SqlSource',
                                'sqlReaderQuery': 'SELECT * FROM source_table',
                            },
                            'sink': {'type': 'SqlSink'},
                        },
                    }
                ],
            },
        }

        result = self.parser.parse_code(json.dumps(basic_pipeline))
        assert result.name == 'BasicETLPipeline'
        assert result.description == 'Basic ETL pipeline'
        assert len(result.tasks) == 1
        assert result.tasks[0].id == 'CopyData'
        assert result.tasks[0].type == 'copy'

    def test_parse_all_activity_types(self):
        """Test parsing all major activity types - covers activity type mapping"""
        activities_pipeline = {
            'name': 'AllActivities',
            'properties': {
                'activities': [
                    {
                        'name': 'CopyTask',
                        'type': 'Copy',
                        'typeProperties': {
                            'source': {'type': 'SqlSource'},
                            'sink': {'type': 'SqlSink'},
                        },
                    },
                    {
                        'name': 'CustomTask',
                        'type': 'Custom',
                        'typeProperties': {'command': 'python script.py'},
                    },
                    {
                        'name': 'StoredProcTask',
                        'type': 'SqlServerStoredProcedure',
                        'typeProperties': {'storedProcedureName': 'sp_process'},
                    },
                    {
                        'name': 'WebTask',
                        'type': 'WebActivity',
                        'typeProperties': {'url': 'https://api.example.com', 'method': 'GET'},
                    },
                    {
                        'name': 'IfTask',
                        'type': 'IfCondition',
                        'typeProperties': {'expression': {'value': '@true', 'type': 'Expression'}},
                    },
                    {
                        'name': 'ForEachTask',
                        'type': 'ForEach',
                        'typeProperties': {
                            'items': {'value': '@pipeline().parameters.list', 'type': 'Expression'}
                        },
                    },
                    {
                        'name': 'ExecuteTask',
                        'type': 'ExecutePipeline',
                        'typeProperties': {
                            'pipeline': {'referenceName': 'Child', 'type': 'PipelineReference'}
                        },
                    },
                    {
                        'name': 'LookupTask',
                        'type': 'Lookup',
                        'typeProperties': {'source': {'type': 'SqlSource'}},
                    },
                    {
                        'name': 'ScriptTask',
                        'type': 'Script',
                        'typeProperties': {'scripts': [{'text': 'echo "Hello"'}]},
                    },
                    {
                        'name': 'DatabricksTask',
                        'type': 'DatabricksNotebook',
                        'typeProperties': {'notebookPath': '/notebooks/etl'},
                    },
                    {'name': 'UnknownTask', 'type': 'UnknownType'},
                ]
            },
        }

        result = self.parser.parse_code(json.dumps(activities_pipeline))
        assert len(result.tasks) == 11

        # Verify task type mappings
        task_types = {task.id: task.type for task in result.tasks}
        assert task_types['CopyTask'] == 'copy'
        assert task_types['CustomTask'] == 'bash'
        assert task_types['StoredProcTask'] == 'sql'
        assert task_types['WebTask'] == 'http'
        assert task_types['IfTask'] == 'python'
        assert task_types['ForEachTask'] == 'python'
        assert task_types['ExecuteTask'] == 'pipeline'
        assert task_types['LookupTask'] == 'sql'
        assert task_types['ScriptTask'] == 'sql'  # Script activity maps to sql type
        assert task_types['DatabricksTask'] == 'notebook'
        assert task_types['UnknownTask'] == 'python'  # Default

    def test_parse_dependencies_and_conditions(self):
        """Test dependency parsing with different conditions - covers dependency logic"""
        pipeline_with_deps = {
            'properties': {
                'activities': [
                    {'name': 'Task1', 'type': 'Copy'},
                    {
                        'name': 'Task2',
                        'type': 'Copy',
                        'dependsOn': [
                            {'activity': 'Task1', 'dependencyConditions': ['Succeeded']},
                        ],
                    },
                    {
                        'name': 'Task3',
                        'type': 'Copy',
                        'dependsOn': [
                            {'activity': 'Task1', 'dependencyConditions': ['Failed']},
                            {'activity': 'Task2', 'dependencyConditions': ['Completed']},
                        ],
                    },
                ]
            }
        }

        deps = self.parser.parse_dependencies(pipeline_with_deps)
        assert len(deps) == 3

        # Check dependency conditions
        conditions = [dep.condition for dep in deps]
        assert 'success' in conditions
        assert 'failure' in conditions
        assert 'always' in conditions  # 'Completed' maps to 'always' condition

    def test_parse_activity_with_policy_and_timeout(self):
        """Test activity parsing with policy, timeout, and retry - covers policy parsing"""
        activity_with_policy = {
            'properties': {
                'activities': [
                    {
                        'name': 'PolicyTask',
                        'type': 'Copy',
                        'policy': {
                            'timeout': '02:30:45',  # 2h 30m 45s
                            'retry': 3,
                            'retryIntervalInSeconds': 60,
                        },
                        'linkedServiceName': {
                            'referenceName': 'MyService',
                            'type': 'LinkedServiceReference',
                        },
                        'typeProperties': {
                            'dataset': {'referenceName': 'MyDataset', 'type': 'DatasetReference'}
                        },
                    }
                ]
            }
        }

        tasks = self.parser.parse_tasks(activity_with_policy)
        task = tasks[0]
        assert task.timeout == 9045  # 2h 30m 45s in seconds
        assert task.retries == 3
        assert 'linked_service' in task.parameters
        assert task.parameters['linked_service'] == 'MyService'
        assert 'dataset' in task.parameters

    def test_parse_timeout_formats(self):
        """Test various timeout format parsing - covers timeout parsing logic"""
        # Test different timeout formats
        assert self.parser._parse_timeout('02:30:45') == 9045  # HH:MM:SS
        assert self.parser._parse_timeout('15:30') == 55800  # HH:MM (treated as hours:minutes)
        assert self.parser._parse_timeout('1.12:30:45') == 131445  # Days.HH:MM:SS
        assert self.parser._parse_timeout('00:00:30') == 30  # 30 seconds
        assert self.parser._parse_timeout('invalid') == 3600  # Invalid returns 1 hour
        assert self.parser._parse_timeout('abc:def:ghi') == 3600  # ValueError case
        assert self.parser._parse_timeout(None) is None
        assert self.parser._parse_timeout('') is None

    def test_convert_adf_expressions(self):
        """Test ADF expression conversion - covers expression parsing"""
        # Test various expression types
        assert 'pipeline().parameters.inputPath' in self.parser._convert_adf_expression(
            '@pipeline().parameters.inputPath'
        )
        assert 'output.result' in self.parser._convert_adf_expression(
            "@activity('Task1').output.result"
        )
        assert self.parser._convert_adf_expression('simple string') == 'simple string'

        # Test complex expression
        complex_expr = (
            "@concat(pipeline().parameters.basePath, '/', formatDateTime(utcnow(), 'yyyy-MM-dd'))"
        )
        result = self.parser._convert_adf_expression(complex_expr)
        assert 'concat' in result and 'formatDateTime' in result

    def test_parse_edge_cases_and_missing_fields(self):
        """Test parsing with missing fields and edge cases - covers error handling"""
        # Test missing properties
        result = self.parser.parse_code('{"name": "InvalidPipeline"}')
        assert result.name == 'InvalidPipeline'
        assert len(result.tasks) == 0

        # Test missing activities
        result = self.parser.parse_code(
            '{"name": "NoActivities", "properties": {"description": "Test"}}'
        )
        assert len(result.tasks) == 0

        # Test activity without name
        pipeline = {'properties': {'activities': [{'type': 'Copy'}]}}
        tasks = self.parser.parse_tasks(pipeline)
        assert tasks[0].id == 'unknown_activity'

        # Test activity without type
        pipeline = {'properties': {'activities': [{'name': 'NoType'}]}}
        tasks = self.parser.parse_tasks(pipeline)
        assert tasks[0].type == 'python'  # Default

    def test_parse_metadata_variations(self):
        """Test metadata parsing with various field combinations - covers metadata logic"""
        # Test with all fields
        metadata = self.parser.parse_metadata(
            {'name': 'TestPipeline', 'properties': {'description': 'Test Description'}}
        )
        assert metadata['name'] == 'TestPipeline'
        assert metadata['description'] == 'Test Description'

        # Test without name
        metadata = self.parser.parse_metadata({'properties': {'description': 'Test Description'}})
        assert metadata['name'] == 'adf_pipeline'

        # Test without description
        metadata = self.parser.parse_metadata({'name': 'TestPipeline', 'properties': {}})
        assert metadata['description'] == 'Converted from Azure Data Factory pipeline'

        # Test with empty description
        metadata = self.parser.parse_metadata(
            {'name': 'TestPipeline', 'properties': {'description': ''}}
        )
        assert metadata['description'] == ''

    def test_extract_command_variations(self):
        """Test command extraction for different activity types - covers command extraction logic"""
        # Test Copy activity variations
        copy_activity = {
            'typeProperties': {'source': {'type': 'SqlSource'}, 'sink': {'type': 'SqlSink'}}
        }
        assert 'SqlSource' in self.parser._extract_command(copy_activity, 'Copy')

        copy_no_props = {}
        assert (
            self.parser._extract_command(copy_no_props, 'Copy') == '# Copy from unknown to unknown'
        )

        # Test Custom activity variations
        custom_with_cmd = {'typeProperties': {'command': 'python script.py'}}
        assert self.parser._extract_command(custom_with_cmd, 'Custom') == '# Custom activity'

        custom_no_cmd = {'typeProperties': {}}
        assert self.parser._extract_command(custom_no_cmd, 'Custom') == '# Custom activity'

        # Test StoredProcedure variations
        sp_with_name = {'typeProperties': {'storedProcedureName': 'sp_process_data'}}
        assert 'sp_process_data' in self.parser._extract_command(
            sp_with_name, 'SqlServerStoredProcedure'
        )

        sp_no_name = {'typeProperties': {}}
        assert self.parser._extract_command(sp_no_name, 'SqlServerStoredProcedure') == 'EXEC '

        # Test WebActivity variations
        web_with_url = {'typeProperties': {'url': 'https://api.example.com', 'method': 'POST'}}
        assert (
            self.parser._extract_command(web_with_url, 'WebActivity')
            == 'POST https://api.example.com'
        )

        web_no_url = {'typeProperties': {'method': 'POST'}}
        assert self.parser._extract_command(web_no_url, 'WebActivity') == 'POST '

        # Test ExecutePipeline variations
        exec_with_ref = {
            'typeProperties': {
                'pipeline': {'referenceName': 'ChildPipeline', 'type': 'PipelineReference'}
            }
        }
        assert 'ChildPipeline' in self.parser._extract_command(exec_with_ref, 'ExecutePipeline')

        exec_no_ref = {'typeProperties': {}}
        assert (
            self.parser._extract_command(exec_no_ref, 'ExecutePipeline') == '# Execute pipeline: '
        )

        # Test Script activity
        script_with_scripts = {
            'typeProperties': {'scripts': [{'text': 'echo "Hello"'}, {'text': 'echo "World"'}]}
        }
        assert self.parser._extract_command(script_with_scripts, 'Script') == 'echo "Hello"'

        script_empty = {'typeProperties': {'scripts': []}}
        assert self.parser._extract_command(script_empty, 'Script') == '# Script activity'

        # Test Databricks activity
        databricks_activity = {'typeProperties': {'notebookPath': '/notebooks/etl_process'}}
        assert '/notebooks/etl_process' in self.parser._extract_command(
            databricks_activity, 'DatabricksNotebook'
        )

    def test_framework_detection_and_validation(self):
        """Test framework detection and input validation - covers validation logic"""
        # Valid ADF JSON
        assert self.parser.detect_framework('{"properties": {"activities": []}}') is True
        assert self.parser.validate_input('{"properties": {"activities": []}}') is True

        # Invalid cases
        assert self.parser.detect_framework('invalid json') is False
        assert self.parser.detect_framework('{"no_properties": true}') is False
        assert self.parser.detect_framework('') is False
        assert self.parser.detect_framework(None) is False

        assert self.parser.validate_input('invalid') is False
        assert self.parser.validate_input('{"no_properties": true}') is False
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
        from awslabs.etl_replatforming_mcp_server.models.flex_workflow import FlexWorkflow, Task

        # Test with tasks
        workflow = FlexWorkflow(
            name='test', tasks=[Task(id='task1', name='Task 1', type='copy', command='copy data')]
        )
        completeness = self.parser.get_parsing_completeness(workflow)
        assert completeness == 0.6666666666666666

        # Test empty workflow
        empty_workflow = FlexWorkflow(name='empty', tasks=[])
        completeness = self.parser.get_parsing_completeness(empty_workflow)
        assert completeness == 0.3333333333333333

    def test_abstract_base_methods(self):
        """Test abstract base class methods - covers base class implementation"""
        source_data = {'properties': {'activities': []}}

        # Test methods that return None or empty collections
        assert self.parser.parse_schedule(source_data) is None
        assert self.parser.parse_error_handling(source_data) is None
        assert self.parser.parse_loops(source_data) == {}
        assert self.parser.parse_conditional_logic(source_data) == []
        assert self.parser.parse_parallel_execution(source_data) == []
        assert self.parser.parse_task_groups(source_data) == []
        assert self.parser.parse_connections(source_data) == {}
        assert self.parser.parse_trigger_rules(source_data) == {}
        assert self.parser.parse_data_triggers(source_data) == []

    def test_pipeline_with_parameters_and_variables(self):
        """Test parsing pipeline with parameters and variables - covers parameter handling"""
        complex_pipeline = {
            'name': 'ComplexPipeline',
            'properties': {
                'parameters': {
                    'inputPath': {'type': 'String', 'defaultValue': '/data/input'},
                    'batchSize': {'type': 'Int', 'defaultValue': 100},
                },
                'variables': {
                    'counter': {'type': 'Integer', 'defaultValue': 0},
                    'status': {'type': 'String', 'defaultValue': 'pending'},
                },
                'activities': [
                    {
                        'name': 'ParameterizedTask',
                        'type': 'Copy',
                        'typeProperties': {
                            'source': {
                                'type': 'DelimitedTextSource',
                                'storeSettings': {
                                    'path': {
                                        'value': '@pipeline().parameters.inputPath',
                                        'type': 'Expression',
                                    }
                                },
                            }
                        },
                    },
                    {
                        'name': 'SetVar',
                        'type': 'SetVariable',
                        'typeProperties': {
                            'variableName': 'counter',
                            'value': {
                                'value': '@add(variables("counter"), 1)',
                                'type': 'Expression',
                            },
                        },
                    },
                ],
            },
        }

        result = self.parser.parse_code(json.dumps(complex_pipeline))
        assert result.name == 'ComplexPipeline'
        assert len(result.tasks) == 2
        assert 'parameters' in result.metadata
        assert 'variables' in result.metadata

        # Check SetVariable activity
        set_var_task = next(task for task in result.tasks if task.id == 'SetVar')
        assert set_var_task.type == 'python'
        assert set_var_task.command == '# SetVariable activity'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
