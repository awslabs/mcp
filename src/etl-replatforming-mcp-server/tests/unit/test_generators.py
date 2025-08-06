#!/usr/bin/env python3

import pytest
from awslabs.etl_replatforming_mcp_server.generators.airflow_generator import AirflowGenerator
from awslabs.etl_replatforming_mcp_server.generators.step_functions_generator import StepFunctionsGenerator
from awslabs.etl_replatforming_mcp_server.models.flex_workflow import FlexWorkflow, Task, Schedule


@pytest.fixture
def sample_flex_workflow():
    """Sample FLEX workflow for testing"""
    return FlexWorkflow(
        name="test_workflow",
        description="Test workflow",
        tasks=[
            Task(
                id="task1",
                name="Test Task",
                type="sql",
                command="SELECT * FROM test_table",
                timeout=3600,
                retries=2
            )
        ],
        schedule=Schedule(
            type="rate",
            expression="rate(1 day)"
        )
    )


class TestAirflowGenerator:
    """Test cases for AirflowGenerator"""
    
    def test_generate_default(self, sample_flex_workflow):
        """Test generate with defaults"""
        generator = AirflowGenerator()
        result = generator.generate(sample_flex_workflow)
        
        assert result['framework'] == 'airflow'
        assert 'dag_code' in result
        assert 'dag_id' in result
        assert 'filename' in result
        assert result['dag_id'] == 'etl_test_workflow'
        assert result['filename'] == 'etl_test_workflow.py'
    
    def test_generate_with_context(self, sample_flex_workflow):
        """Test generate with context document"""
        context = "Workflows: custom_{name}, Files: {name}_pipeline.py"
        
        generator = AirflowGenerator()
        result = generator.generate(sample_flex_workflow, context)
        
        # With current implementation, uses simple defaults
        assert result['dag_id'] == 'etl_test_workflow'
        assert result['filename'] == 'etl_test_workflow.py'
    
    def test_generate_dag_code_structure(self, sample_flex_workflow):
        """Test generated DAG code structure"""
        generator = AirflowGenerator()
        result = generator.generate(sample_flex_workflow)
        
        dag_code = result['dag_code']
        assert 'from datetime import datetime, timedelta' in dag_code
        assert 'from airflow import DAG' in dag_code
        assert 'default_args = {' in dag_code
        assert 'dag = DAG(' in dag_code
        assert sample_flex_workflow.name in dag_code


class TestStepFunctionsGenerator:
    """Test cases for StepFunctionsGenerator"""
    
    def test_generate_default(self, sample_flex_workflow):
        """Test generate with defaults"""
        generator = StepFunctionsGenerator()
        result = generator.generate(sample_flex_workflow)
        
        assert result['framework'] == 'step_functions'
        assert 'state_machine_definition' in result
        assert 'state_machine_name' in result
        assert 'execution_role' in result
    
    def test_generate_with_context(self, sample_flex_workflow):
        """Test generate with context document"""
        context = "State machines: custom-{name}, Roles: {name}_custom_role"
        
        generator = StepFunctionsGenerator()
        result = generator.generate(sample_flex_workflow, context)
        
        # Test that it generates without error
        assert result['framework'] == 'step_functions'
        assert 'state_machine_definition' in result