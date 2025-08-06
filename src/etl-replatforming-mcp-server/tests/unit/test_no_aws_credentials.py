#!/usr/bin/env python3

import pytest
import os
import json
from unittest.mock import patch, MagicMock
from awslabs.etl_replatforming_mcp_server.server import (
    convert_single_etl_workflow,
    parse_single_workflow_to_flex,
    generate_single_workflow_from_flex,
    convert_etl_workflow,
    parse_to_flex,
    generate_from_flex
)


@pytest.fixture
def sample_step_functions_json():
    return json.dumps({
        "Comment": "Simple Step Functions workflow",
        "StartAt": "HelloWorld",
        "States": {
            "HelloWorld": {
                "Type": "Task",
                "Resource": "arn:aws:states:::lambda:invoke",
                "Parameters": {
                    "FunctionName": "hello-world-function"
                },
                "End": True
            }
        }
    })


@pytest.fixture
def sample_airflow_dag():
    return """
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

def hello_world():
    print("Hello World")

dag = DAG(
    'hello_world_dag',
    description='Simple Hello World DAG',
    schedule_interval='@daily',
    start_date=datetime(2023, 1, 1),
    catchup=False
)

task = PythonOperator(
    task_id='hello_world_task',
    python_callable=hello_world,
    dag=dag
)
"""


@pytest.fixture
def sample_flex_workflow():
    return {
        "name": "hello_world_workflow",
        "description": "Simple Hello World workflow",
        "schedule": {
            "type": "rate",
            "expression": "rate(1 day)",
            "timezone": "UTC"
        },
        "tasks": [
            {
                "id": "hello_world_task",
                "name": "Hello World Task",
                "type": "python",
                "command": "print('Hello World')",
                "timeout": 300,
                "retries": 1
            }
        ],
        "error_handling": {
            "on_failure": "fail",
            "notification_emails": []
        }
    }


class TestNoAWSCredentials:
    """Test that all 6 MCP tools work without AWS credentials."""

    @patch.dict(os.environ, {}, clear=True)
    @patch('boto3.client')
    def test_convert_single_etl_workflow_no_aws(self, mock_boto3, sample_step_functions_json):
        """Test convert-single-etl-workflow works without AWS credentials."""
        # Mock boto3 to raise credentials error
        mock_boto3.side_effect = Exception("Unable to locate credentials")
        
        # Should work without AWS credentials (deterministic parsing only)
        result = pytest.asyncio.run(convert_single_etl_workflow(
            workflow_content=sample_step_functions_json,
            source_framework="step_functions",
            target_framework="airflow"
        ))
        
        # Should return incomplete result with placeholders
        assert result['status'] in ['complete', 'incomplete']
        assert 'flex_workflow' in result

    @patch.dict(os.environ, {}, clear=True)
    @patch('boto3.client')
    def test_parse_single_workflow_to_flex_no_aws(self, mock_boto3, sample_airflow_dag):
        """Test parse-single-workflow-to-flex works without AWS credentials."""
        mock_boto3.side_effect = Exception("Unable to locate credentials")
        
        result = pytest.asyncio.run(parse_single_workflow_to_flex(
            workflow_content=sample_airflow_dag,
            source_framework="airflow"
        ))
        
        assert result['status'] in ['complete', 'incomplete']
        assert 'flex_workflow' in result

    @patch.dict(os.environ, {}, clear=True)
    def test_generate_single_workflow_from_flex_no_aws(self, sample_flex_workflow):
        """Test generate-single-workflow-from-flex works without AWS credentials."""
        result = pytest.asyncio.run(generate_single_workflow_from_flex(
            flex_workflow=sample_flex_workflow,
            target_framework="airflow"
        ))
        
        assert result['status'] == 'complete'
        assert 'target_code' in result

    @patch.dict(os.environ, {}, clear=True)
    @patch('boto3.client')
    @patch('awslabs.etl_replatforming_mcp_server.utils.directory_processor.DirectoryProcessor.scan_directory')
    @patch('awslabs.etl_replatforming_mcp_server.utils.directory_processor.DirectoryProcessor.create_output_directories')
    @patch('awslabs.etl_replatforming_mcp_server.utils.directory_processor.DirectoryProcessor.save_flex_document')
    @patch('awslabs.etl_replatforming_mcp_server.utils.directory_processor.DirectoryProcessor.save_target_job')
    @patch('builtins.open')
    def test_convert_etl_workflow_no_aws(self, mock_open, mock_save_target, mock_save_flex, 
                                       mock_create_dirs, mock_scan, mock_boto3, sample_step_functions_json):
        """Test convert-etl-workflow works without AWS credentials."""
        mock_boto3.side_effect = Exception("Unable to locate credentials")
        mock_scan.return_value = [('/fake/path/workflow.json', 'step_functions')]
        mock_create_dirs.return_value = ('/fake/flex_dir', '/fake/jobs_dir')
        mock_open.return_value.__enter__.return_value.read.return_value = sample_step_functions_json
        
        result = pytest.asyncio.run(convert_etl_workflow(
            directory_path="/fake/path",
            target_framework="airflow"
        ))
        
        assert result['status'] in ['complete', 'partial']
        assert result['processed_files'] >= 0

    @patch.dict(os.environ, {}, clear=True)
    @patch('boto3.client')
    @patch('awslabs.etl_replatforming_mcp_server.utils.directory_processor.DirectoryProcessor.scan_directory')
    @patch('awslabs.etl_replatforming_mcp_server.utils.directory_processor.DirectoryProcessor.create_output_directories')
    @patch('awslabs.etl_replatforming_mcp_server.utils.directory_processor.DirectoryProcessor.save_flex_document')
    @patch('builtins.open')
    def test_parse_to_flex_no_aws(self, mock_open, mock_save_flex, mock_create_dirs, 
                                 mock_scan, mock_boto3, sample_airflow_dag):
        """Test parse-to-flex works without AWS credentials."""
        mock_boto3.side_effect = Exception("Unable to locate credentials")
        mock_scan.return_value = [('/fake/path/dag.py', 'airflow')]
        mock_create_dirs.return_value = ('/fake/flex_dir', None)
        mock_open.return_value.__enter__.return_value.read.return_value = sample_airflow_dag
        
        result = pytest.asyncio.run(parse_to_flex(
            directory_path="/fake/path"
        ))
        
        assert result['status'] in ['complete', 'partial']
        assert result['processed_files'] >= 0

    @patch.dict(os.environ, {}, clear=True)
    @patch('awslabs.etl_replatforming_mcp_server.utils.directory_processor.DirectoryProcessor.scan_directory')
    @patch('awslabs.etl_replatforming_mcp_server.utils.directory_processor.DirectoryProcessor.create_output_directories')
    @patch('awslabs.etl_replatforming_mcp_server.utils.directory_processor.DirectoryProcessor.save_target_job')
    @patch('builtins.open')
    def test_generate_from_flex_no_aws(self, mock_open, mock_save_target, mock_create_dirs, 
                                      mock_scan, sample_flex_workflow):
        """Test generate-from-flex works without AWS credentials."""
        mock_scan.return_value = [('/fake/path/workflow.flex.json', 'flex')]
        mock_create_dirs.return_value = (None, '/fake/jobs_dir')
        mock_open.return_value.__enter__.return_value = MagicMock()
        mock_open.return_value.__enter__.return_value.__enter__.return_value.read.return_value = json.dumps(sample_flex_workflow)
        
        result = pytest.asyncio.run(generate_from_flex(
            directory_path="/fake/path",
            target_framework="airflow"
        ))
        
        assert result['status'] in ['complete', 'partial']
        assert result['processed_files'] >= 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])