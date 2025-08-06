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

"""Unit tests for single workflow MCP tools with updated names following Python best practices."""

import pytest
import json
from unittest.mock import Mock, patch

# Import the actual implementation functions, not the MCP tool wrappers
from awslabs.etl_replatforming_mcp_server.server import (
    _parse_to_flex_workflow,
    _generate_from_flex_workflow,
    _validate_flex_workflow,
    _prompt_user_for_missing
)
from awslabs.etl_replatforming_mcp_server.models.flex_workflow import FlexWorkflow


@pytest.fixture
def step_functions_workflow():
    """Complete Step Functions workflow definition."""
    return json.dumps({
        "Comment": "Customer ETL Pipeline",
        "StartAt": "ExtractData",
        "States": {
            "ExtractData": {
                "Type": "Task",
                "Resource": "arn:aws:states:::lambda:invoke",
                "Parameters": {"FunctionName": "extract-customer-data"},
                "Next": "LoadData"
            },
            "LoadData": {
                "Type": "Task", 
                "Resource": "arn:aws:states:::lambda:invoke",
                "Parameters": {"FunctionName": "load-to-warehouse"},
                "End": True
            }
        }
    })


@pytest.fixture
def airflow_dag():
    """Complete Airflow DAG definition."""
    return '''
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime

dag = DAG('customer_etl', start_date=datetime(2024, 1, 1), schedule_interval='@daily')

extract_task = PythonOperator(task_id='extract_data', python_callable=lambda: None, dag=dag)
load_task = PythonOperator(task_id='load_data', python_callable=lambda: None, dag=dag)

extract_task >> load_task
'''


@pytest.fixture
def complete_flex_workflow():
    """Complete FLEX workflow."""
    return {
        "name": "customer_etl",
        "description": "Customer ETL pipeline",
        "schedule": {"type": "cron", "expression": "0 9 * * *", "timezone": "UTC"},
        "tasks": [
            {
                "id": "extract_data",
                "name": "Extract Data",
                "type": "python",
                "command": "extract_data()",
                "timeout": 3600,
                "retries": 2,
                "depends_on": []
            },
            {
                "id": "load_data",
                "name": "Load Data",
                "type": "python", 
                "command": "load_data()",
                "timeout": 3600,
                "retries": 2,
                "depends_on": []
            }
        ],
        "error_handling": {"on_failure": "fail", "notification_emails": ["team@company.com"]}
    }


@pytest.fixture
def incomplete_flex_workflow():
    """Incomplete FLEX workflow missing schedule."""
    return {
        "name": "customer_etl",
        "description": "Customer ETL pipeline",
        "schedule": {"type": "cron", "expression": "?", "timezone": "UTC"},
        "tasks": [
            {
                "id": "extract_data",
                "name": "Extract Data",
                "type": "python",
                "command": "extract_data()",
                "timeout": 3600,
                "retries": 2,
                "depends_on": []
            }
        ]
    }


@pytest.fixture
def mock_bedrock_service():
    """Mock Bedrock service to avoid AWS calls."""
    with patch('awslabs.etl_replatforming_mcp_server.server._get_bedrock_service') as mock:
        bedrock = Mock()
        bedrock.enhance_flex_workflow.return_value = None
        mock.return_value = bedrock
        yield mock


class TestConvertSingleEtlWorkflow:
    """Test convert-single-etl-workflow tool."""

    @pytest.mark.asyncio
    async def test_step_functions_to_airflow_conversion(self, mock_bedrock_service, step_functions_workflow):
        """Test Step Functions to Airflow conversion."""
        # Act - Parse to FLEX
        parse_result = await _parse_to_flex_workflow(
            'step_functions', step_functions_workflow, None, 'airflow'
        )
        
        # Assert parse result
        assert parse_result['status'] in ['complete', 'incomplete']
        
        # If complete, test generation
        if parse_result['status'] == 'complete':
            generation_result = await _generate_from_flex_workflow(
                parse_result['flex_workflow'], 'airflow', None
            )
            assert generation_result['status'] == 'complete'
            assert 'target_config' in generation_result
            target_code = generation_result['target_config']
            if isinstance(target_code, dict):
                target_code = target_code.get('dag_code', str(target_code))
            assert 'DAG' in target_code

    @pytest.mark.asyncio
    async def test_airflow_to_step_functions_conversion(self, mock_bedrock_service, airflow_dag):
        """Test Airflow to Step Functions conversion."""
        # Act - Parse to FLEX
        parse_result = await _parse_to_flex_workflow(
            'airflow', airflow_dag, None, 'step_functions'
        )
        
        # Assert parse result
        assert parse_result['status'] in ['complete', 'incomplete']
        
        # If complete, test generation
        if parse_result['status'] == 'complete':
            generation_result = await _generate_from_flex_workflow(
                parse_result['flex_workflow'], 'step_functions', None
            )
            assert generation_result['status'] == 'complete'
            assert 'target_config' in generation_result
            target_code = generation_result['target_config']
            if isinstance(target_code, dict):
                target_code = target_code.get('state_machine', str(target_code))
            assert 'StartAt' in target_code

    @pytest.mark.asyncio
    async def test_conversion_with_context_document(self, mock_bedrock_service, step_functions_workflow):
        """Test conversion with organizational context."""
        # Arrange
        context = "Use prefix 'etl_' for all workflow names"
        
        # Act - Parse then generate with context
        parse_result = await _parse_to_flex_workflow(
            'step_functions', step_functions_workflow, None, 'airflow'
        )
        
        # Assert
        assert parse_result['status'] in ['complete', 'incomplete']
        
        if parse_result['status'] == 'complete':
            generation_result = await _generate_from_flex_workflow(
                parse_result['flex_workflow'], 'airflow', context
            )
            assert generation_result['status'] == 'complete'

    @pytest.mark.asyncio
    async def test_invalid_source_framework(self, mock_bedrock_service):
        """Test error handling for invalid source framework."""
        # Act & Assert
        with pytest.raises(ValueError, match="No parser available"):
            await _parse_to_flex_workflow(
                'invalid_framework', "{}", None, 'airflow'
            )

    @pytest.mark.asyncio
    async def test_invalid_target_framework(self, mock_bedrock_service, step_functions_workflow):
        """Test error handling for invalid target framework."""
        # Arrange - First parse successfully
        parse_result = await _parse_to_flex_workflow(
            'step_functions', step_functions_workflow, None
        )
        
        # Act & Assert - Then try invalid target framework
        if parse_result['status'] == 'complete':
            with pytest.raises(ValueError, match="No generator available"):
                await _generate_from_flex_workflow(
                    parse_result['flex_workflow'], 'invalid_framework', None
                )

    @pytest.mark.asyncio
    async def test_malformed_json_input(self, mock_bedrock_service):
        """Test error handling for malformed JSON."""
        # Act & Assert
        from awslabs.etl_replatforming_mcp_server.models.exceptions import ParsingError
        with pytest.raises(ParsingError):
            await _parse_to_flex_workflow(
                'step_functions', "invalid json", None, 'airflow'
            )


class TestParseSingleWorkflowToFlex:
    """Test parse-single-workflow-to-flex functionality."""

    @pytest.mark.asyncio
    async def test_parse_step_functions_workflow(self, mock_bedrock_service, step_functions_workflow):
        """Test parsing Step Functions workflow."""
        # Act
        result = await _parse_to_flex_workflow(
            'step_functions', step_functions_workflow, None
        )
        
        # Assert
        assert result['status'] in ['complete', 'incomplete']
        assert 'flex_workflow' in result

    @pytest.mark.asyncio
    async def test_parse_airflow_workflow(self, mock_bedrock_service, airflow_dag):
        """Test parsing Airflow workflow."""
        # Act
        result = await _parse_to_flex_workflow(
            'airflow', airflow_dag, None
        )
        
        # Assert
        assert result['status'] in ['complete', 'incomplete']
        assert 'flex_workflow' in result

    @pytest.mark.asyncio
    async def test_parse_with_llm_config(self, mock_bedrock_service, step_functions_workflow):
        """Test parsing with custom LLM configuration."""
        # Arrange
        llm_config = {"model_id": "anthropic.claude-3-haiku-20240307-v1:0", "temperature": 0.2}
        
        # Act
        result = await _parse_to_flex_workflow(
            'step_functions', step_functions_workflow, llm_config
        )
        
        # Assert
        assert result['status'] in ['complete', 'incomplete']
        assert 'flex_workflow' in result


class TestGenerateSingleWorkflowFromFlex:
    """Test generate-single-workflow-from-flex functionality."""

    @pytest.mark.asyncio
    async def test_generate_airflow_from_flex(self, mock_bedrock_service, complete_flex_workflow):
        """Test generating Airflow DAG from FLEX workflow."""
        # Arrange
        workflow = FlexWorkflow.from_dict(complete_flex_workflow)
        
        # Act
        result = await _generate_from_flex_workflow(
            workflow, 'airflow', None
        )
        
        # Assert
        assert result['status'] == 'complete'
        assert 'target_config' in result
        target_code = result['target_config']
        if isinstance(target_code, dict):
            target_code = target_code.get('dag_code', str(target_code))
        assert 'DAG' in target_code

    @pytest.mark.asyncio
    async def test_generate_step_functions_from_flex(self, mock_bedrock_service, complete_flex_workflow):
        """Test generating Step Functions from FLEX workflow."""
        # Arrange
        workflow = FlexWorkflow.from_dict(complete_flex_workflow)
        
        # Act
        result = await _generate_from_flex_workflow(
            workflow, 'step_functions', None
        )
        
        # Assert
        assert result['status'] == 'complete'
        assert 'target_config' in result
        target_code = result['target_config']
        if isinstance(target_code, dict):
            target_code = target_code.get('state_machine', str(target_code))
        assert 'StartAt' in target_code

    @pytest.mark.asyncio
    async def test_generate_with_context_document(self, mock_bedrock_service, complete_flex_workflow):
        """Test generation with organizational context."""
        # Arrange
        workflow = FlexWorkflow.from_dict(complete_flex_workflow)
        context = "Use prefix 'etl_' for all workflow names"
        
        # Act
        result = await _generate_from_flex_workflow(
            workflow, 'airflow', context
        )
        
        # Assert
        assert result['status'] == 'complete'
        assert 'target_config' in result

    @pytest.mark.asyncio
    async def test_generate_with_incomplete_flex(self, mock_bedrock_service, incomplete_flex_workflow):
        """Test error handling for incomplete FLEX workflow."""
        # Arrange
        workflow = FlexWorkflow.from_dict(incomplete_flex_workflow)
        validation_result = _validate_flex_workflow(workflow)
        
        # Act & Assert
        if not validation_result['is_complete']:
            # This should be handled by validation before generation
            prompt_result = _prompt_user_for_missing(workflow, validation_result, 'airflow')
            assert prompt_result['status'] == 'incomplete'
            assert 'missing_information' in prompt_result