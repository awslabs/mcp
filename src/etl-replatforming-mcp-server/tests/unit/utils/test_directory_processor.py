"""Tests for awslabs.etl_replatforming_mcp_server.utils.directory_processor"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from awslabs.etl_replatforming_mcp_server.utils.directory_processor import (
    DirectoryProcessor,
)


class TestDirectoryProcessor:
    """Tests for awslabs.etl_replatforming_mcp_server.utils.directory_processor"""

    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_dir = Path(self.temp_dir)

    def teardown_method(self):
        """Clean up test fixtures"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_scan_directory_airflow_files(self):
        """Test scanning directory with Airflow files"""
        # Create test Airflow file
        airflow_file = self.test_dir / 'test_dag.py'
        airflow_file.write_text(
            """
from airflow import DAG
from airflow.operators.python import PythonOperator

dag = DAG('test_dag')
task = PythonOperator(task_id='test_task', python_callable=lambda: None)
"""
        )

        result = DirectoryProcessor.scan_directory(str(self.test_dir))

        assert len(result) == 1
        file_path, framework = result[0]
        assert file_path == str(airflow_file)
        assert framework == 'airflow'

    def test_scan_directory_step_functions_files(self):
        """Test scanning directory with Step Functions files"""
        # Create test Step Functions file
        sf_file = self.test_dir / 'state_machine.json'
        sf_file.write_text(
            json.dumps(
                {
                    'Comment': 'Test state machine',
                    'StartAt': 'Task1',
                    'States': {
                        'Task1': {
                            'Type': 'Task',
                            'Resource': 'arn:aws:lambda:us-east-1:123456789012:function:test',
                            'End': True,
                        }
                    },
                }
            )
        )

        result = DirectoryProcessor.scan_directory(str(self.test_dir))

        assert len(result) == 1
        file_path, framework = result[0]
        assert file_path == str(sf_file)
        assert framework == 'step_functions'

    def test_scan_directory_flex_files(self):
        """Test scanning directory with FLEX files"""
        # Create test FLEX file
        flex_file = self.test_dir / 'workflow.flex.json'
        flex_file.write_text(
            json.dumps(
                {
                    'name': 'test_workflow',
                    'tasks': [
                        {
                            'id': 'task1',
                            'name': 'Task 1',
                            'type': 'python',
                            'command': "print('hello')",
                        }
                    ],
                }
            )
        )

        result = DirectoryProcessor.scan_directory(str(self.test_dir))

        assert len(result) == 1
        file_path, framework = result[0]
        assert file_path == str(flex_file)
        assert framework == 'flex'

    def test_scan_directory_empty(self):
        """Test scanning empty directory"""
        result = DirectoryProcessor.scan_directory(str(self.test_dir))
        assert result == []

    def test_scan_directory_mixed_files(self):
        """Test scanning directory with mixed file types"""
        # Create Airflow file
        airflow_file = self.test_dir / 'dag.py'
        airflow_file.write_text('from airflow import DAG')

        # Create Step Functions file
        sf_file = self.test_dir / 'state.json'
        sf_file.write_text('{"StartAt": "Task1", "States": {}}')

        # Create non-workflow file
        other_file = self.test_dir / 'readme.txt'
        other_file.write_text('This is a readme file')

        result = DirectoryProcessor.scan_directory(str(self.test_dir))

        assert len(result) == 2  # Only workflow files
        frameworks = [framework for _, framework in result]
        assert 'airflow' in frameworks
        assert 'step_functions' in frameworks

    def test_create_output_directories(self):
        """Test creating output directories"""
        # Create a mock project structure with pyproject.toml
        project_dir = self.test_dir / 'project'
        project_dir.mkdir()
        (project_dir / 'pyproject.toml').touch()  # Create pyproject.toml to mark as project root

        input_dir = project_dir / 'input'
        input_dir.mkdir()

        flex_dir, jobs_dir = DirectoryProcessor.create_output_directories(
            str(input_dir), 'convert_etl_workflow'
        )

        assert os.path.exists(flex_dir)
        assert os.path.exists(jobs_dir)
        assert 'target_flex_from_source' in flex_dir
        assert 'target_jobs_from_source' in jobs_dir

    def test_create_output_directories_custom_path(self):
        """Test creating output directories with custom output path"""
        input_dir = self.test_dir / 'input'
        input_dir.mkdir()

        custom_output = self.test_dir / 'custom_output'

        flex_dir, jobs_dir = DirectoryProcessor.create_output_directories(
            str(input_dir), 'convert_etl_workflow', str(custom_output)
        )

        assert os.path.exists(flex_dir)
        assert os.path.exists(jobs_dir)
        assert str(custom_output) in flex_dir
        assert str(custom_output) in jobs_dir

    def test_save_flex_document(self):
        """Test saving FLEX document"""
        flex_dict = {
            'name': 'test_workflow',
            'tasks': [{'id': 'task1', 'type': 'python', 'command': "print('test')"}],
        }

        source_file = str(self.test_dir / 'source.py')
        output_dir = str(self.test_dir / 'output')
        os.makedirs(output_dir)

        DirectoryProcessor.save_flex_document(flex_dict, source_file, output_dir)

        expected_file = Path(output_dir) / 'source.flex.json'
        assert expected_file.exists()

        with open(expected_file) as f:
            saved_data = json.load(f)
        assert saved_data['name'] == 'test_workflow'

    def test_save_target_job_airflow(self):
        """Test saving target job for Airflow"""
        target_config = {
            'dag_code': '# Generated DAG code',
            'dag_id': 'test_dag',
            'filename': 'test_dag.py',
        }

        source_file = str(self.test_dir / 'source.json')
        output_dir = str(self.test_dir / 'output')
        os.makedirs(output_dir)

        DirectoryProcessor.save_target_job(target_config, source_file, output_dir, 'airflow')

        expected_file = Path(output_dir) / 'source.py'
        assert expected_file.exists()

        content = expected_file.read_text()
        assert '# Generated DAG code' in content

    def test_save_target_job_step_functions(self):
        """Test saving target job for Step Functions"""
        target_config = {
            'state_machine_definition': {
                'Comment': 'Test state machine',
                'StartAt': 'Task1',
                'States': {'Task1': {'Type': 'Task', 'End': True}},
            },
            'state_machine_name': 'test-workflow',
        }

        source_file = str(self.test_dir / 'source.py')
        output_dir = str(self.test_dir / 'output')
        os.makedirs(output_dir)

        DirectoryProcessor.save_target_job(
            target_config, source_file, output_dir, 'step_functions'
        )

        expected_file = Path(output_dir) / 'source.json'
        assert expected_file.exists()

        with open(expected_file) as f:
            saved_data = json.load(f)
        assert saved_data['Comment'] == 'Test state machine'

    def test_save_target_job_with_python_files(self):
        """Test saving target job with Python files"""
        target_config = {
            'state_machine_definition': {'StartAt': 'Task1', 'States': {}},
            'python_files': {'extract.py': '#!/usr/bin/env python3\ndef extract(): pass'},
        }

        source_file = str(self.test_dir / 'source.py')
        output_dir = str(self.test_dir / 'output')
        os.makedirs(output_dir)

        DirectoryProcessor.save_target_job(
            target_config, source_file, output_dir, 'step_functions'
        )

        # Check main file
        main_file = Path(output_dir) / 'source.json'
        assert main_file.exists()

        # Check Python files directory
        python_dir = Path(output_dir) / 'glue_python_shell_jobs' / 'source'
        assert python_dir.exists()

        python_file = python_dir / 'extract.py'
        assert python_file.exists()

        content = python_file.read_text()
        assert 'def extract(): pass' in content

    def test_detect_framework_file_not_found(self):
        """Test detect_framework with non-existent file"""
        result = DirectoryProcessor.detect_framework('/nonexistent/file.py')
        assert result is None

    def test_detect_framework_azure_data_factory(self):
        """Test detect_framework with Azure Data Factory file"""
        adf_file = self.test_dir / 'pipeline.json'
        adf_file.write_text(
            json.dumps({'properties': {'activities': [{'name': 'CopyData', 'type': 'Copy'}]}})
        )
        result = DirectoryProcessor.detect_framework(str(adf_file))
        assert result == 'azure_data_factory'

    def test_scan_directory_nonexistent(self):
        """Test scan_directory with non-existent directory"""
        result = DirectoryProcessor.scan_directory('/nonexistent/directory')
        assert result == []

    def test_save_flex_document_with_python_files(self):
        """Test save_flex_document with Python files in metadata"""
        flex_dict = {
            'name': 'test_workflow',
            'tasks': [{'id': 'task1', 'type': 'python'}],
            'metadata': {
                'python_files': {'task1.py': '#!/usr/bin/env python3\ndef task1(): pass'}
            },
        }

        source_file = str(self.test_dir / 'source.py')
        output_dir = str(self.test_dir / 'output')
        os.makedirs(output_dir)

        DirectoryProcessor.save_flex_document(flex_dict, source_file, output_dir)

        # Check FLEX file
        flex_file = Path(output_dir) / 'source.flex.json'
        assert flex_file.exists()

        # Check Python files
        python_dir = Path(output_dir) / 'glue_python_shell_jobs' / 'test_workflow'
        assert python_dir.exists()
        assert (python_dir / 'task1.py').exists()
        assert (python_dir / 'task1_glue_job.json').exists()

    def test_detect_framework_json_exception(self):
        """Test detect_framework with JSON file that raises exception"""
        json_file = self.test_dir / 'test.json'
        json_file.write_text('{"valid": "json"}')

        # Mock json.load to raise an exception
        import json as json_module

        original_load = json_module.load

        def mock_load(f):
            raise Exception('Test exception')

        json_module.load = mock_load
        try:
            result = DirectoryProcessor.detect_framework(str(json_file))
            assert result is None
        finally:
            json_module.load = original_load

    def test_detect_framework_python_exception(self):
        """Test detect_framework with Python file that raises exception"""
        py_file = self.test_dir / 'test.py'
        py_file.write_text('print("hello")')

        # Mock open to raise an exception
        import builtins

        original_open = builtins.open

        def mock_open(*args, **kwargs):
            if str(py_file) in str(args[0]):
                raise Exception('Test exception')
            return original_open(*args, **kwargs)

        builtins.open = mock_open
        try:
            result = DirectoryProcessor.detect_framework(str(py_file))
            assert result is None
        finally:
            builtins.open = original_open

    def test_create_output_directories_no_project_root(self):
        """Test create_output_directories when no project root is found"""
        # Create a deep directory structure without pyproject.toml
        deep_dir = self.test_dir / 'a' / 'b' / 'c' / 'd'
        deep_dir.mkdir(parents=True)

        flex_dir, jobs_dir = DirectoryProcessor.create_output_directories(
            str(deep_dir), 'convert_etl_workflow'
        )

        assert os.path.exists(flex_dir)
        assert os.path.exists(jobs_dir)

    def test_save_flex_document_ai_generated_tasks(self):
        """Test save_flex_document with AI-generated tasks"""
        flex_dict = {
            'name': 'ai_workflow',
            'tasks': [{'id': 'task1', 'type': 'python', 'ai_generated': True}],
        }

        source_file = str(self.test_dir / 'source.py')
        output_dir = str(self.test_dir / 'output')
        os.makedirs(output_dir)

        DirectoryProcessor.save_flex_document(flex_dict, source_file, output_dir)

        # Should create file with ai_enhanced marker
        expected_file = Path(output_dir) / 'source.ai_enhanced.flex.json'
        assert expected_file.exists()

    def test_detect_framework_yaml_file(self):
        """Test detect_framework with YAML file."""
        yaml_file = self.test_dir / 'test.yaml'
        yaml_file.write_text('apiVersion: v1\nkind: Workflow')
        result = DirectoryProcessor.detect_framework(str(yaml_file))
        assert result is None

    def test_detect_framework_json_invalid(self):
        """Test detect_framework with invalid JSON."""
        json_file = self.test_dir / 'invalid.json'
        json_file.write_text('invalid json content')
        result = DirectoryProcessor.detect_framework(str(json_file))
        assert result is None

    def test_detect_framework_flex_with_parsing_info(self):
        """Test detect_framework with FLEX file containing parsing_info."""
        flex_content = {
            'name': 'test_workflow',
            'tasks': [{'id': 'task1', 'type': 'python'}],
            'parsing_info': {'source_framework': 'airflow'},
        }
        json_file = self.test_dir / 'test.flex.json'
        json_file.write_text(json.dumps(flex_content))
        result = DirectoryProcessor.detect_framework(str(json_file))
        assert result == 'flex'

    def test_create_output_directories_parse_to_flex(self):
        """Test create_output_directories for parse_to_flex operation."""
        flex_dir, jobs_dir = DirectoryProcessor.create_output_directories(
            str(self.test_dir), 'parse_to_flex'
        )
        assert flex_dir != ''
        assert jobs_dir == ''
        assert Path(flex_dir).exists()
        assert 'target_flex_from_source' in flex_dir

    def test_create_output_directories_generate_from_flex(self):
        """Test create_output_directories for generate_from_flex operation."""
        flex_dir, jobs_dir = DirectoryProcessor.create_output_directories(
            str(self.test_dir), 'generate_from_flex'
        )
        assert flex_dir == ''
        assert jobs_dir != ''
        assert Path(jobs_dir).exists()
        assert 'target_jobs_from_source_flex' in jobs_dir

    def test_save_flex_document_incomplete_with_ai(self):
        """Test save_flex_document with incomplete workflow and AI content."""
        flex_dict = {
            'name': 'test_workflow',
            'tasks': [{'id': 'task1', 'type': 'python'}],
            'parsing_info': {
                'missing_fields': ['task_commands'],
                'llm_enhancements': ['Added schedule'],
            },
        }
        source_file = str(self.test_dir / 'source.py')
        output_dir = str(self.test_dir / 'output')
        os.makedirs(output_dir)
        DirectoryProcessor.save_flex_document(flex_dict, source_file, output_dir)
        expected_file = Path(output_dir) / 'source.ai_enhanced.incomplete.flex.json'
        assert expected_file.exists()

    def test_detect_framework_yaml_files(self):
        """Test detect_framework with YAML files (future framework support)"""
        yaml_file = self.test_dir / 'workflow.yaml'
        yaml_file.write_text('apiVersion: v1\nkind: Workflow')

        result = DirectoryProcessor.detect_framework(str(yaml_file))
        assert result is None  # Currently returns None for YAML files

        yml_file = self.test_dir / 'workflow.yml'
        yml_file.write_text('apiVersion: v1\nkind: Workflow')

        result = DirectoryProcessor.detect_framework(str(yml_file))
        assert result is None  # Currently returns None for YML files

    # Additional comprehensive tests for missing coverage

    def test_save_flex_document_complete_filename_handling(self):
        """Test save_flex_document with various filename scenarios"""
        # Test with .flex already in name
        flex_dict = {
            'name': 'test_workflow',
            'tasks': [{'id': 'task1', 'type': 'python'}],
        }
        source_file = str(self.test_dir / 'source.flex.py')
        output_dir = str(self.test_dir / 'output')
        os.makedirs(output_dir)

        DirectoryProcessor.save_flex_document(flex_dict, source_file, output_dir)

        # Should create file without double .flex
        expected_file = Path(output_dir) / 'source.flex.json'
        assert expected_file.exists()

    def test_save_flex_document_incomplete_only(self):
        """Test save_flex_document with incomplete workflow only"""
        flex_dict = {
            'name': 'test_workflow',
            'tasks': [{'id': 'task1', 'type': 'python'}],
            'parsing_info': {
                'missing_fields': ['task_commands'],
            },
        }
        source_file = str(self.test_dir / 'source.py')
        output_dir = str(self.test_dir / 'output')
        os.makedirs(output_dir)

        DirectoryProcessor.save_flex_document(flex_dict, source_file, output_dir)

        expected_file = Path(output_dir) / 'source.incomplete.flex.json'
        assert expected_file.exists()

    def test_save_flex_document_ai_enhanced_only(self):
        """Test save_flex_document with AI enhanced workflow only"""
        flex_dict = {
            'name': 'test_workflow',
            'tasks': [{'id': 'task1', 'type': 'python'}],
            'parsing_info': {
                'llm_enhancements': ['Added schedule'],
            },
        }
        source_file = str(self.test_dir / 'source.py')
        output_dir = str(self.test_dir / 'output')
        os.makedirs(output_dir)

        DirectoryProcessor.save_flex_document(flex_dict, source_file, output_dir)

        expected_file = Path(output_dir) / 'source.ai_enhanced.flex.json'
        assert expected_file.exists()

    def test_save_flex_document_no_parsing_info(self):
        """Test save_flex_document without parsing_info"""
        flex_dict = {
            'name': 'test_workflow',
            'tasks': [{'id': 'task1', 'type': 'python'}],
        }
        source_file = str(self.test_dir / 'source.py')
        output_dir = str(self.test_dir / 'output')
        os.makedirs(output_dir)

        DirectoryProcessor.save_flex_document(flex_dict, source_file, output_dir)

        expected_file = Path(output_dir) / 'source.flex.json'
        assert expected_file.exists()

    def test_save_flex_document_with_glue_job_definitions(self):
        """Test save_flex_document creates proper Glue job definitions"""
        flex_dict = {
            'name': 'test_workflow',
            'tasks': [{'id': 'task1', 'type': 'python'}],
            'metadata': {
                'python_files': {
                    'extract_data.py': '#!/usr/bin/env python3\ndef extract(): pass',
                    'transform_data.py': '#!/usr/bin/env python3\ndef transform(): pass',
                }
            },
        }
        source_file = str(self.test_dir / 'source.py')
        output_dir = str(self.test_dir / 'output')
        os.makedirs(output_dir)

        DirectoryProcessor.save_flex_document(flex_dict, source_file, output_dir)

        # Check Glue job definitions
        glue_dir = Path(output_dir) / 'glue_python_shell_jobs' / 'test_workflow'
        assert (glue_dir / 'extract_data_glue_job.json').exists()
        assert (glue_dir / 'transform_data_glue_job.json').exists()

        # Verify job definition content
        with open(glue_dir / 'extract_data_glue_job.json') as f:
            job_def = json.load(f)
        assert job_def['Name'] == 'test_workflow_extract_data'
        assert job_def['Command']['Name'] == 'pythonshell'
        assert job_def['GlueVersion'] == '3.0'

    def test_save_target_job_airflow_with_python_files(self):
        """Test save_target_job for Airflow with Python files"""
        target_config = {
            'dag_code': '# Generated Airflow DAG',
            'python_files': {
                'task1.py': '#!/usr/bin/env python3\ndef task1(): pass',
                'task2.py': '#!/usr/bin/env python3\ndef task2(): pass',
            },
        }
        source_file = str(self.test_dir / 'source.json')
        output_dir = str(self.test_dir / 'output')
        os.makedirs(output_dir)

        DirectoryProcessor.save_target_job(target_config, source_file, output_dir, 'airflow')

        # Check main DAG file
        dag_file = Path(output_dir) / 'source.py'
        assert dag_file.exists()
        assert '# Generated Airflow DAG' in dag_file.read_text()

        # Check Python files and Glue job definitions
        glue_dir = Path(output_dir) / 'glue_python_shell_jobs' / 'source'
        assert (glue_dir / 'task1.py').exists()
        assert (glue_dir / 'task2.py').exists()
        assert (glue_dir / 'task1_glue_job.json').exists()
        assert (glue_dir / 'task2_glue_job.json').exists()

    def test_save_target_job_flex_filename_handling(self):
        """Test save_target_job handles .flex filenames correctly"""
        target_config = {
            'state_machine_definition': {'StartAt': 'Task1', 'States': {}},
        }
        source_file = str(self.test_dir / 'source.flex.json')
        output_dir = str(self.test_dir / 'output')
        os.makedirs(output_dir)

        DirectoryProcessor.save_target_job(
            target_config, source_file, output_dir, 'step_functions'
        )

        # Should remove .flex from filename
        expected_file = Path(output_dir) / 'source.json'
        assert expected_file.exists()

    def test_save_target_job_unknown_framework(self):
        """Test save_target_job with unknown framework"""
        target_config = {'some_config': 'value'}
        source_file = str(self.test_dir / 'source.py')
        output_dir = str(self.test_dir / 'output')
        os.makedirs(output_dir)

        DirectoryProcessor.save_target_job(
            target_config, source_file, output_dir, 'unknown_framework'
        )

        # Should default to JSON format
        expected_file = Path(output_dir) / 'source.json'
        assert expected_file.exists()

        with open(expected_file) as f:
            saved_data = json.load(f)
        assert saved_data['some_config'] == 'value'

    def test_save_target_job_empty_config(self):
        """Test save_target_job with empty configuration"""
        target_config = {}
        source_file = str(self.test_dir / 'source.py')
        output_dir = str(self.test_dir / 'output')
        os.makedirs(output_dir)

        DirectoryProcessor.save_target_job(
            target_config, source_file, output_dir, 'step_functions'
        )

        expected_file = Path(output_dir) / 'source.json'
        assert expected_file.exists()

        with open(expected_file) as f:
            saved_data = json.load(f)
        assert saved_data == {}

    def test_detect_framework_io_error_python(self):
        """Test detect_framework handles IOError for Python files"""
        py_file = self.test_dir / 'test.py'
        py_file.write_text('from airflow import DAG')

        # Make file unreadable
        py_file.chmod(0o000)

        try:
            result = DirectoryProcessor.detect_framework(str(py_file))
            # Should return None due to IOError
            assert result is None
        finally:
            # Restore permissions for cleanup
            py_file.chmod(0o644)

    def test_detect_framework_io_error_json(self):
        """Test detect_framework handles IOError for JSON files"""
        json_file = self.test_dir / 'test.json'
        json_file.write_text('{"StartAt": "Task1", "States": {}}')

        # Make file unreadable
        json_file.chmod(0o000)

        try:
            result = DirectoryProcessor.detect_framework(str(json_file))
            # Should return None due to IOError
            assert result is None
        finally:
            # Restore permissions for cleanup
            json_file.chmod(0o644)

    def test_detect_framework_generic_flex_empty_tasks(self):
        """Test detect_framework with FLEX file having empty tasks"""
        flex_content = {
            'name': 'test_workflow',
            'tasks': [],  # Empty tasks list
        }
        json_file = self.test_dir / 'test.json'
        json_file.write_text(json.dumps(flex_content))

        result = DirectoryProcessor.detect_framework(str(json_file))
        # Without parsing_info, it's not detected as FLEX
        assert result is None

    def test_detect_framework_generic_flex_invalid_tasks(self):
        """Test detect_framework with FLEX file having invalid task structure"""
        flex_content = {
            'name': 'test_workflow',
            'tasks': [{'name': 'task1'}],  # Missing 'id' field
        }
        json_file = self.test_dir / 'test.json'
        json_file.write_text(json.dumps(flex_content))

        result = DirectoryProcessor.detect_framework(str(json_file))
        # Should not detect as flex due to invalid task structure
        assert result is None

    def test_detect_framework_tasks_not_list(self):
        """Test detect_framework with tasks field that's not a list"""
        content = {
            'name': 'test_workflow',
            'tasks': 'not_a_list',
        }
        json_file = self.test_dir / 'test.json'
        json_file.write_text(json.dumps(content))

        result = DirectoryProcessor.detect_framework(str(json_file))
        assert result is None

    def test_detect_framework_unknown_extension(self):
        """Test detect_framework with unknown file extension"""
        unknown_file = self.test_dir / 'test.unknown'
        unknown_file.write_text('some content')

        result = DirectoryProcessor.detect_framework(str(unknown_file))
        assert result is None

    def test_scan_directory_with_subdirectories(self):
        """Test scan_directory processes subdirectories"""
        # Create subdirectory structure
        sub_dir = self.test_dir / 'subdir'
        sub_dir.mkdir()

        # Create files in subdirectory
        airflow_file = sub_dir / 'dag.py'
        airflow_file.write_text('from airflow import DAG')

        sf_file = sub_dir / 'state.json'
        sf_file.write_text('{"StartAt": "Task1", "States": {}}')

        result = DirectoryProcessor.scan_directory(str(self.test_dir))

        assert len(result) == 2
        file_paths = [path for path, _ in result]
        assert str(airflow_file) in file_paths
        assert str(sf_file) in file_paths

    def test_create_output_directories_relative_path_error(self):
        """Test create_output_directories when relative path calculation fails"""
        # Create a directory structure that will cause ValueError in relative_to
        temp_root = Path(tempfile.mkdtemp())
        input_dir = Path(tempfile.mkdtemp())  # Different root, will cause ValueError

        try:
            flex_dir, jobs_dir = DirectoryProcessor.create_output_directories(
                str(input_dir), 'convert_etl_workflow'
            )

            # Should use input_dir.name as fallback
            assert os.path.exists(flex_dir)
            assert os.path.exists(jobs_dir)
            assert input_dir.name in flex_dir
            assert input_dir.name in jobs_dir
        finally:
            import shutil

            shutil.rmtree(temp_root, ignore_errors=True)
            shutil.rmtree(input_dir, ignore_errors=True)

    def test_save_flex_document_no_metadata(self):
        """Test save_flex_document without metadata section"""
        flex_dict = {
            'name': 'test_workflow',
            'tasks': [{'id': 'task1', 'type': 'python'}],
            # No metadata section
        }
        source_file = str(self.test_dir / 'source.py')
        output_dir = str(self.test_dir / 'output')
        os.makedirs(output_dir)

        DirectoryProcessor.save_flex_document(flex_dict, source_file, output_dir)

        expected_file = Path(output_dir) / 'source.flex.json'
        assert expected_file.exists()

        # Should not create glue_python_shell_jobs directory
        glue_dir = Path(output_dir) / 'glue_python_shell_jobs'
        assert not glue_dir.exists()

    def test_save_flex_document_empty_python_files(self):
        """Test save_flex_document with empty python_files dict"""
        flex_dict = {
            'name': 'test_workflow',
            'tasks': [{'id': 'task1', 'type': 'python'}],
            'metadata': {
                'python_files': {}  # Empty dict
            },
        }
        source_file = str(self.test_dir / 'source.py')
        output_dir = str(self.test_dir / 'output')
        os.makedirs(output_dir)

        DirectoryProcessor.save_flex_document(flex_dict, source_file, output_dir)

        expected_file = Path(output_dir) / 'source.flex.json'
        assert expected_file.exists()

        # Should not create glue_python_shell_jobs directory
        glue_dir = Path(output_dir) / 'glue_python_shell_jobs'
        assert not glue_dir.exists()

    def test_save_target_job_no_python_files(self):
        """Test save_target_job without python_files"""
        target_config = {
            'state_machine_definition': {'StartAt': 'Task1', 'States': {}},
            # No python_files
        }
        source_file = str(self.test_dir / 'source.py')
        output_dir = str(self.test_dir / 'output')
        os.makedirs(output_dir)

        DirectoryProcessor.save_target_job(
            target_config, source_file, output_dir, 'step_functions'
        )

        expected_file = Path(output_dir) / 'source.json'
        assert expected_file.exists()

        # Should not create glue_python_shell_jobs directory
        glue_dir = Path(output_dir) / 'glue_python_shell_jobs'
        assert not glue_dir.exists()

    def test_save_target_job_empty_python_files(self):
        """Test save_target_job with empty python_files dict"""
        target_config = {
            'state_machine_definition': {'StartAt': 'Task1', 'States': {}},
            'python_files': {},  # Empty dict
        }
        source_file = str(self.test_dir / 'source.py')
        output_dir = str(self.test_dir / 'output')
        os.makedirs(output_dir)

        DirectoryProcessor.save_target_job(
            target_config, source_file, output_dir, 'step_functions'
        )

        expected_file = Path(output_dir) / 'source.json'
        assert expected_file.exists()

        # Should not create glue_python_shell_jobs directory
        glue_dir = Path(output_dir) / 'glue_python_shell_jobs'
        assert not glue_dir.exists()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
