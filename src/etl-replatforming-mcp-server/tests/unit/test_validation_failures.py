#!/usr/bin/env python3

import pytest
from awslabs.etl_replatforming_mcp_server.models.flex_workflow import FlexWorkflow, Schedule, Task, TaskDependency, ErrorHandling
from awslabs.etl_replatforming_mcp_server.validators.workflow_validator import WorkflowValidator


class TestValidationFailures:
    """Test that validations fail for invalid values as documented in README"""
    
    def setup_method(self):
        self.validator = WorkflowValidator()
    
    def create_base_workflow(self) -> FlexWorkflow:
        """Create a valid base workflow for testing"""
        return FlexWorkflow(
            name="test_workflow",
            description="Test workflow",
            schedule=Schedule(
                type="cron",
                expression="0 9 * * *",
                timezone="UTC"
            ),
            tasks=[
                Task(
                    id="task1",
                    name="Test Task",
                    type="sql",
                    command="SELECT 1",
                    timeout=3600,
                    retries=2
                )
            ]
        )
    
    def test_invalid_schedule_types(self):
        """Test that invalid schedule types fail validation"""
        # Note: Schedule types are validated based on expression compatibility
        invalid_combinations = [
            ("cron", "rate(1 day)"),  # cron type with rate expression
            ("rate", "0 9 * * *"),    # rate type with cron expression
            ("cron", "invalid_cron"), # cron type with invalid expression
            ("rate", "invalid_rate")  # rate type with invalid expression
        ]
        
        for invalid_type, invalid_expr in invalid_combinations:
            workflow = self.create_base_workflow()
            workflow.schedule.type = invalid_type
            workflow.schedule.expression = invalid_expr
            
            schedule_errors = self.validator.validate_schedule_type(workflow)
            assert len(schedule_errors) > 0, f"Schedule type '{invalid_type}' with expression '{invalid_expr}' should be invalid"
    
    def test_valid_schedule_types(self):
        """Test that valid schedule types pass validation"""
        valid_combinations = [
            ("cron", "0 9 * * *"),
            ("rate", "rate(1 day)"),
            ("manual", ""),
            ("event", "s3:ObjectCreated:*")
        ]
        
        for valid_type, valid_expr in valid_combinations:
            workflow = self.create_base_workflow()
            workflow.schedule.type = valid_type
            workflow.schedule.expression = valid_expr
            
            schedule_errors = self.validator.validate_schedule_type(workflow)
            assert len(schedule_errors) == 0, f"Schedule type '{valid_type}' with expression '{valid_expr}' should be valid"
    
    def test_invalid_dependency_conditions(self):
        """Test that invalid dependency conditions fail validation"""
        invalid_conditions = [
            "completed",
            "failed", 
            "succeeded",
            "skipped",
            "invalid_condition"
        ]
        
        for invalid_condition in invalid_conditions:
            workflow = self.create_base_workflow()
            # Add a second task with invalid dependency condition
            workflow.tasks.append(
                Task(
                    id="task2",
                    name="Task 2",
                    type="sql", 
                    command="SELECT 2",
                    depends_on=[
                        TaskDependency(task_id="task1", condition=invalid_condition)
                    ]
                )
            )
            
            validation = self.validator.validate(workflow)
            dependency_errors = self.validator.validate_dependency_conditions(workflow)
            assert len(dependency_errors) > 0, f"Dependency condition '{invalid_condition}' should be invalid"
    
    def test_valid_dependency_conditions(self):
        """Test that valid dependency conditions pass validation"""
        valid_conditions = ["success", "failure", "always", None]
        
        for valid_condition in valid_conditions:
            workflow = self.create_base_workflow()
            # Add a second task with valid dependency condition
            workflow.tasks.append(
                Task(
                    id="task2",
                    name="Task 2", 
                    type="sql",
                    command="SELECT 2",
                    depends_on=[
                        TaskDependency(task_id="task1", condition=valid_condition)
                    ]
                )
            )
            
            dependency_errors = self.validator.validate_dependency_conditions(workflow)
            assert len(dependency_errors) == 0, f"Dependency condition '{valid_condition}' should be valid"
    
    def test_invalid_error_handling_failure_actions(self):
        """Test that invalid error handling failure actions fail validation"""
        invalid_failure_actions = [
            "stop",
            "abort", 
            "terminate",
            "skip",
            "ignore",
            "invalid_action"
        ]
        
        for invalid_action in invalid_failure_actions:
            workflow = self.create_base_workflow()
            workflow.error_handling = ErrorHandling(
                on_failure=invalid_action,
                notification_emails=["test@example.com"]
            )
            
            validation = self.validator.validate(workflow)
            error_handling_errors = self.validator.validate_error_handling(workflow)
            assert len(error_handling_errors) > 0, f"Error handling action '{invalid_action}' should be invalid"
    
    def test_valid_error_handling_failure_actions(self):
        """Test that valid error handling failure actions pass validation"""
        valid_failure_actions = ["fail", "continue", "retry"]
        
        for valid_action in valid_failure_actions:
            workflow = self.create_base_workflow()
            workflow.error_handling = ErrorHandling(
                on_failure=valid_action,
                notification_emails=["test@example.com"]
            )
            
            error_handling_errors = self.validator.validate_error_handling(workflow)
            assert len(error_handling_errors) == 0, f"Error handling action '{valid_action}' should be valid"
    
    def test_invalid_email_formats(self):
        """Test that invalid email formats fail validation"""
        invalid_emails = [
            "invalid-email",
            "test@",
            "@example.com",
            "test.example.com",
            "test@example",
            "test space@example.com"
        ]
        
        for invalid_email in invalid_emails:
            workflow = self.create_base_workflow()
            workflow.error_handling = ErrorHandling(
                on_failure="fail",
                notification_emails=[invalid_email]
            )
            
            error_handling_errors = self.validator.validate_error_handling(workflow)
            assert len(error_handling_errors) > 0, f"Email '{invalid_email}' should be invalid"
    
    def test_valid_email_formats(self):
        """Test that valid email formats pass validation"""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk", 
            "test123@test-domain.org",
            "admin@company.io"
        ]
        
        for valid_email in valid_emails:
            workflow = self.create_base_workflow()
            workflow.error_handling = ErrorHandling(
                on_failure="fail",
                notification_emails=[valid_email]
            )
            
            error_handling_errors = self.validator.validate_error_handling(workflow)
            assert len(error_handling_errors) == 0, f"Email '{valid_email}' should be valid"
    
    def test_invalid_timeout_values(self):
        """Test that invalid timeout values fail validation"""
        invalid_timeouts = [0, -1, 86401, 100000]  # 0, negative, > 24 hours
        
        for invalid_timeout in invalid_timeouts:
            workflow = self.create_base_workflow()
            workflow.tasks[0].timeout = invalid_timeout
            
            timeout_errors = self.validator.validate_task_timeouts(workflow)
            assert len(timeout_errors) > 0, f"Timeout '{invalid_timeout}' should be invalid"
    
    def test_valid_timeout_values(self):
        """Test that valid timeout values pass validation"""
        valid_timeouts = [1, 3600, 86400]  # 1 second, 1 hour, 24 hours
        
        for valid_timeout in valid_timeouts:
            workflow = self.create_base_workflow()
            workflow.tasks[0].timeout = valid_timeout
            
            timeout_errors = self.validator.validate_task_timeouts(workflow)
            assert len(timeout_errors) == 0, f"Timeout '{valid_timeout}' should be valid"
    
    def test_invalid_retry_values(self):
        """Test that invalid retry values fail validation"""
        invalid_retries = [-1, 11, 100]  # negative, > 10
        
        for invalid_retry in invalid_retries:
            workflow = self.create_base_workflow()
            workflow.tasks[0].retries = invalid_retry
            
            retry_errors = self.validator.validate_task_retries(workflow)
            assert len(retry_errors) > 0, f"Retries '{invalid_retry}' should be invalid"
    
    def test_valid_retry_values(self):
        """Test that valid retry values pass validation"""
        valid_retries = [0, 5, 10]  # 0 to 10 retries
        
        for valid_retry in valid_retries:
            workflow = self.create_base_workflow()
            workflow.tasks[0].retries = valid_retry
            
            retry_errors = self.validator.validate_task_retries(workflow)
            assert len(retry_errors) == 0, f"Retries '{valid_retry}' should be valid"
    
    def test_invalid_retry_delay_values(self):
        """Test that invalid retry delay values fail validation"""
        invalid_delays = [-1, 3601, 7200]  # negative, > 1 hour
        
        for invalid_delay in invalid_delays:
            workflow = self.create_base_workflow()
            workflow.tasks[0].retry_delay = invalid_delay
            
            retry_errors = self.validator.validate_task_retries(workflow)
            assert len(retry_errors) > 0, f"Retry delay '{invalid_delay}' should be invalid"
    
    def test_valid_retry_delay_values(self):
        """Test that valid retry delay values pass validation"""
        valid_delays = [0, 300, 3600]  # 0 to 1 hour
        
        for valid_delay in valid_delays:
            workflow = self.create_base_workflow()
            workflow.tasks[0].retry_delay = valid_delay
            
            retry_errors = self.validator.validate_task_retries(workflow)
            assert len(retry_errors) == 0, f"Retry delay '{valid_delay}' should be valid"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])