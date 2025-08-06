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

"""Tests for parsers."""

import pytest
import json

from awslabs.etl_replatforming_mcp_server.parsers.step_functions_parser import StepFunctionsParser
from awslabs.etl_replatforming_mcp_server.parsers.airflow_parser import AirflowParser


class TestAirflowParser:
    """Test Airflow parser functionality."""
    
    def test_framework_name(self):
        """Test framework name property"""
        parser = AirflowParser()
        assert parser.framework_name == "airflow"
    
    def test_parse_code_basic(self):
        """Test basic Airflow DAG parsing"""
        parser = AirflowParser()
        
        dag_code = '''
from airflow import DAG
from datetime import datetime

dag = DAG(
    'test_dag',
    description='Test DAG',
    schedule_interval='@daily',
    start_date=datetime(2024, 1, 1)
)
'''
        
        workflow = parser.parse_code(dag_code)
        
        assert workflow.name == 'test_dag'
        assert workflow.description == 'Test DAG'


class TestStepFunctionsParser:
    """Test Step Functions parser functionality."""
    
    def test_parse_code_valid_json(self):
        """Test parsing valid Step Functions JSON."""
        parser = StepFunctionsParser()
        
        input_code = json.dumps({
            "Comment": "Test Pipeline",
            "StartAt": "Task1",
            "States": {
                "Task1": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::aws-sdk:redshiftdata:executeStatement",
                    "Parameters": {
                        "Sql": "SELECT * FROM test_table"
                    },
                    "End": True
                }
            }
        })
        
        workflow = parser.parse_code(input_code)
        
        assert workflow.name == "test_pipeline"
        assert len(workflow.tasks) == 1
        assert workflow.tasks[0].id == "Task1"
    
    def test_parse_code_invalid_json(self):
        """Test parsing invalid JSON raises error."""
        parser = StepFunctionsParser()
        
        with pytest.raises(Exception):
            parser.parse_code("invalid json {")