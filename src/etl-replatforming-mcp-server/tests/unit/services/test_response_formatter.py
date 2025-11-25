from unittest.mock import patch

import pytest

from awslabs.etl_replatforming_mcp_server.models.flex_workflow import FlexWorkflow, Task
from awslabs.etl_replatforming_mcp_server.services.response_formatter import (
    ResponseFormatter,
)


class TestResponseFormatter:
    """Tests for awslabs.etl_replatforming_mcp_server.services.response_formatter"""

    def test_prompt_user_for_missing_basic(self):
        """Test basic user prompt for missing fields"""
        workflow = FlexWorkflow(name='test', tasks=[])
        validation_result = {
            'completion_percentage': 0.5,
            'missing_fields': ['schedule_configuration'],
        }

        result = ResponseFormatter.prompt_user_for_missing(workflow, validation_result)

        assert result['status'] == 'incomplete'
        assert result['completion_percentage'] == 0.5
        assert 'Schedule: Replace' in result['missing_information']
        assert 'cron expression' in result['missing_information']

    def test_prompt_user_for_missing_task_details(self):
        """Test user prompt for missing task execution details"""
        workflow = FlexWorkflow(name='test', tasks=[])
        validation_result = {
            'completion_percentage': 0.8,
            'missing_fields': [
                'task_extract_execution_details',
                'task_transform_sql_query',
            ],
        }

        result = ResponseFormatter.prompt_user_for_missing(workflow, validation_result)

        assert "Task 'extract': Replace '?' in command field" in result['missing_information']
        assert (
            "Task 'transform': Replace '?' in command field with SQL query"
            in result['missing_information']
        )

    def test_prompt_user_for_missing_with_target_framework(self):
        """Test user prompt with target framework context"""
        workflow = FlexWorkflow(name='test', tasks=[])
        validation_result = {
            'completion_percentage': 0.7,
            'missing_fields': ['schedule_configuration'],
        }

        result = ResponseFormatter.prompt_user_for_missing(workflow, validation_result, 'airflow')

        assert 'airflow' in result['message']
        assert 'Task type conversions for airflow' in result['message']

    def test_prompt_user_for_missing_no_fields(self):
        """Test user prompt when no fields are missing"""
        workflow = FlexWorkflow(name='test', tasks=[])
        validation_result = {'completion_percentage': 1.0, 'missing_fields': []}

        result = ResponseFormatter.prompt_user_for_missing(workflow, validation_result)

        assert result['missing_information'] == 'No missing fields identified.'

    def test_format_parse_response(self):
        """Test formatting parse response"""
        workflow = FlexWorkflow(
            name='test',
            tasks=[Task(id='t1', name='Task 1', type='python', command='test()')],
        )
        parse_result = {
            'flex_workflow': workflow,
            'validation_result': {'is_complete': True},
        }

        result = ResponseFormatter.format_parse_response(parse_result)

        assert result['status'] == 'complete'
        assert result['flex_workflow'] == workflow
        assert result['completion_percentage'] == 1.0
        assert result['message'] == 'FLEX workflow generated successfully.'

    @patch('boto3.client')
    def test_check_bedrock_availability_success(self, mock_boto_client):
        """Test Bedrock availability check when available"""
        mock_boto_client.return_value = None  # No exception

        result = ResponseFormatter._check_bedrock_availability()

        assert result == ''

    @patch('boto3.client')
    def test_check_bedrock_availability_no_credentials(self, mock_boto_client):
        """Test Bedrock availability check with no credentials"""
        mock_boto_client.side_effect = Exception('Unable to locate credentials')

        result = ResponseFormatter._check_bedrock_availability()

        assert 'AWS credentials not configured' in result

    @patch('boto3.client')
    def test_check_bedrock_availability_access_denied(self, mock_boto_client):
        """Test Bedrock availability check with access denied"""
        mock_boto_client.side_effect = Exception('AccessDeniedException')

        result = ResponseFormatter._check_bedrock_availability()

        assert 'Bedrock access denied' in result

    @patch('boto3.client')
    def test_check_bedrock_availability_other_error(self, mock_boto_client):
        """Test Bedrock availability check with other error"""
        mock_boto_client.side_effect = Exception('Other error')

        result = ResponseFormatter._check_bedrock_availability()

        assert 'Bedrock unavailable' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
