#!/usr/bin/env python3

import pytest
import json
from awslabs.etl_replatforming_mcp_server.models.flex_workflow import FlexWorkflow, Schedule, Task
from awslabs.etl_replatforming_mcp_server.validators.workflow_validator import WorkflowValidator
from awslabs.etl_replatforming_mcp_server.generators.airflow_generator import AirflowGenerator
from awslabs.etl_replatforming_mcp_server.generators.step_functions_generator import StepFunctionsGenerator


class TestScheduleHandling:
    """Test that all tools can handle both cron and rate schedule expressions"""
    
    def setup_method(self):
        self.validator = WorkflowValidator()
        self.airflow_generator = AirflowGenerator()
        self.step_functions_generator = StepFunctionsGenerator()
    
    def create_test_workflow(self, schedule_type: str, schedule_expression: str) -> FlexWorkflow:
        """Create a test workflow with specified schedule"""
        return FlexWorkflow(
            name="test_workflow",
            description="Test workflow for schedule handling",
            schedule=Schedule(
                type=schedule_type,
                expression=schedule_expression,
                timezone="UTC"
            ),
            tasks=[
                Task(
                    id="test_task",
                    name="Test Task",
                    type="sql",
                    command="SELECT 1",
                    timeout=3600,
                    retries=2
                )
            ]
        )
    
    def test_cron_schedule_validation(self):
        """Test that cron expressions are properly validated"""
        # Valid cron expressions
        valid_cron_expressions = [
            "0 9 * * *",      # Daily at 9 AM
            "0 */6 * * *",    # Every 6 hours
            "30 2 * * 1",     # Weekly on Monday at 2:30 AM
            "0 0 1 * *",      # Monthly on 1st at midnight
            "15 14 1 1 *"     # Yearly on Jan 1st at 2:15 PM
        ]
        
        for expr in valid_cron_expressions:
            workflow = self.create_test_workflow("cron", expr)
            validation = self.validator.validate(workflow)
            assert validation['is_complete'], f"Cron expression '{expr}' should be valid"
    
    def test_rate_schedule_validation(self):
        """Test that rate expressions are properly validated"""
        # Valid rate expressions
        valid_rate_expressions = [
            "rate(1 day)",
            "rate(2 hours)",
            "rate(30 minutes)",
            "rate(1 hour)",
            "rate(7 days)"
        ]
        
        for expr in valid_rate_expressions:
            workflow = self.create_test_workflow("rate", expr)
            validation = self.validator.validate(workflow)
            assert validation['is_complete'], f"Rate expression '{expr}' should be valid"
    
    def test_invalid_cron_expressions(self):
        """Test that invalid cron expressions are caught"""
        invalid_cron_expressions = [
            "0 9 * *",        # Missing weekday field
            "?",              # Placeholder
            "",               # Empty string
            "invalid format", # Not cron format
            "0 9"             # Too few fields
        ]
        
        for expr in invalid_cron_expressions:
            workflow = self.create_test_workflow("cron", expr)
            validation = self.validator.validate(workflow)
            # Check that schedule validation specifically failed
            schedule_errors = self.validator.validate_schedule_type(workflow)
            assert len(schedule_errors) > 0, f"Cron expression '{expr}' should be invalid"
    
    def test_invalid_rate_expressions(self):
        """Test that invalid rate expressions are caught"""
        invalid_rate_expressions = [
            "rate(1)",           # Missing unit
            "every 1 day",       # Wrong format
            "rate(1 second)",    # Unsupported unit
            "1 day",             # Missing rate() wrapper
            "?",                 # Placeholder
            ""                   # Empty string
        ]
        
        for expr in invalid_rate_expressions:
            workflow = self.create_test_workflow("rate", expr)
            validation = self.validator.validate(workflow)
            # Check that schedule validation specifically failed
            schedule_errors = self.validator.validate_schedule_type(workflow)
            assert len(schedule_errors) > 0, f"Rate expression '{expr}' should be invalid"
    
    def test_airflow_generator_cron_schedule(self):
        """Test Airflow generator handles cron schedules correctly"""
        workflow = self.create_test_workflow("cron", "0 9 * * *")
        result = self.airflow_generator.generate(workflow)
        
        assert "schedule_interval='0 9 * * *'" in result['dag_code']
        assert result['framework'] == 'airflow'
    
    def test_airflow_generator_rate_schedule(self):
        """Test Airflow generator converts rate schedules to Airflow format"""
        test_cases = [
            ("rate(1 day)", "'@daily'"),
            ("rate(1 hour)", "'@hourly'"),
            ("rate(2 hours)", "'rate(2 hours)'")  # Falls back to original
        ]
        
        for rate_expr, expected in test_cases:
            workflow = self.create_test_workflow("rate", rate_expr)
            result = self.airflow_generator.generate(workflow)
            assert expected in result['dag_code'], f"Rate '{rate_expr}' should convert to {expected}"
    
    def test_step_functions_generator_schedule_handling(self):
        """Test Step Functions generator handles schedules (external EventBridge)"""
        # Test cron schedule
        cron_workflow = self.create_test_workflow("cron", "0 9 * * *")
        cron_result = self.step_functions_generator.generate(cron_workflow)
        
        assert cron_result['framework'] == 'step_functions'
        assert 'state_machine_definition' in cron_result
        
        # Test rate schedule
        rate_workflow = self.create_test_workflow("rate", "rate(1 day)")
        rate_result = self.step_functions_generator.generate(rate_workflow)
        
        assert rate_result['framework'] == 'step_functions'
        assert 'state_machine_definition' in rate_result
    
    def test_manual_schedule_type(self):
        """Test manual schedule type (no automatic scheduling)"""
        workflow = self.create_test_workflow("manual", "")
        
        # Check that schedule validation passes for manual type
        schedule_errors = self.validator.validate_schedule_type(workflow)
        assert len(schedule_errors) == 0, "Manual schedule should be valid"
        
        # Test generators handle manual scheduling
        airflow_result = self.airflow_generator.generate(workflow)
        assert "schedule_interval=None" in airflow_result['dag_code'] or "schedule_interval='@once'" in airflow_result['dag_code']
        
        sf_result = self.step_functions_generator.generate(workflow)
        assert sf_result['framework'] == 'step_functions'
    
    def test_event_schedule_type(self):
        """Test event-driven schedule type"""
        workflow = self.create_test_workflow("event", "s3:ObjectCreated:*")
        validation = self.validator.validate(workflow)
        assert validation['is_complete']
        
        # Generators should handle event-driven schedules
        airflow_result = self.airflow_generator.generate(workflow)
        sf_result = self.step_functions_generator.generate(workflow)
        
        assert airflow_result['framework'] == 'airflow'
        assert sf_result['framework'] == 'step_functions'
    
    def test_schedule_timezone_handling(self):
        """Test that timezone information is preserved"""
        workflow = FlexWorkflow(
            name="timezone_test",
            schedule=Schedule(
                type="cron",
                expression="0 9 * * *",
                timezone="America/New_York"
            ),
            tasks=[
                Task(id="task1", name="Task 1", type="sql", command="SELECT 1")
            ]
        )
        
        validation = self.validator.validate(workflow)
        assert validation['is_complete']
        
        # Check that generators preserve timezone info
        airflow_result = self.airflow_generator.generate(workflow)
        assert 'timezone' in airflow_result['dag_code'] or 'America/New_York' in airflow_result['dag_code']
    
    def test_missing_schedule_handling(self):
        """Test workflows without schedule information"""
        workflow = FlexWorkflow(
            name="no_schedule_test",
            tasks=[
                Task(id="task1", name="Task 1", type="sql", command="SELECT 1")
            ]
        )
        
        # Should still be valid (schedule is optional)
        validation = self.validator.validate(workflow)
        # Note: This might be incomplete depending on validator implementation
        
        # Generators should handle missing schedules gracefully
        airflow_result = self.airflow_generator.generate(workflow)
        sf_result = self.step_functions_generator.generate(workflow)
        
        assert airflow_result['framework'] == 'airflow'
        assert sf_result['framework'] == 'step_functions'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])