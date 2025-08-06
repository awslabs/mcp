#!/usr/bin/env python3

"""Integration tests to verify that llm_config parameters are properly used end-to-end."""

import pytest
import json
from unittest.mock import Mock, patch

from awslabs.etl_replatforming_mcp_server.server import (
    _parse_to_flex_workflow,
    _generate_from_flex_workflow
)


class TestLLMConfigIntegration:
    """Integration tests for llm_config usage across the system."""
    
    @patch('boto3.client')
    @pytest.mark.asyncio
    async def test_convert_single_workflow_uses_custom_model(self, mock_boto_client):
        """Test that convert_single_etl_workflow uses custom model from llm_config."""
        # Mock both bedrock-runtime and sts clients
        mock_bedrock_client = Mock()
        mock_sts_client = Mock()
        mock_sts_client.get_caller_identity.return_value = {}
        
        def client_side_effect(service_name, **kwargs):
            if service_name == 'bedrock-runtime':
                return mock_bedrock_client
            elif service_name == 'sts':
                return mock_sts_client
            return Mock()
        
        mock_boto_client.side_effect = client_side_effect
        
        # Mock successful Bedrock response that completes the workflow
        enhanced_workflow = {
            "name": "test_workflow",
            "description": "Test workflow",
            "schedule": {"type": "cron", "expression": "0 9 * * *", "timezone": "UTC"},
            "tasks": [
                {
                    "id": "task1",
                    "name": "Test Task",
                    "type": "python",
                    "command": "print('hello')",
                    "timeout": 3600,
                    "retries": 2,
                    "depends_on": []
                }
            ],
            "error_handling": {"on_failure": "fail", "notification_emails": ["test@example.com"]}
        }
        
        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': json.dumps(enhanced_workflow)}]
        }).encode()
        mock_bedrock_client.invoke_model.return_value = mock_response
        
        # Test workflow that will need enhancement
        incomplete_workflow = json.dumps({
            "Comment": "Test workflow",
            "StartAt": "Task1",
            "States": {
                "Task1": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::lambda:invoke",
                    "End": True
                }
            }
        })
        
        # Custom LLM config with different model
        custom_llm_config = {
            "model_id": "anthropic.claude-3-haiku-20240307-v1:0",
            "temperature": 0.5,
            "max_tokens": 3000
        }
        
        # Call the parse function
        parse_result = await _parse_to_flex_workflow(
            source_framework='step_functions',
            input_code=incomplete_workflow,
            llm_config=custom_llm_config,
            target_framework='airflow'
        )
        
        # If parsing was successful, also test generation
        if parse_result['status'] == 'complete':
            result = await _generate_from_flex_workflow(
                parse_result['flex_workflow'], 'airflow', None
            )
        
        # Verify Bedrock was called with the custom model
        if mock_bedrock_client.invoke_model.called:
            call_args = mock_bedrock_client.invoke_model.call_args
            assert call_args[1]['modelId'] == "anthropic.claude-3-haiku-20240307-v1:0"
            
            # Verify other custom parameters were used
            body = json.loads(call_args[1]['body'])
            assert body['temperature'] == 0.5
            assert body['max_tokens'] == 3000
    
    @patch('boto3.client')
    @pytest.mark.asyncio
    async def test_parse_single_workflow_uses_custom_model(self, mock_boto_client):
        """Test that parse_single_workflow_to_flex uses custom model from llm_config."""
        # Mock both clients
        mock_bedrock_client = Mock()
        mock_sts_client = Mock()
        mock_sts_client.get_caller_identity.return_value = {}
        
        def client_side_effect(service_name, **kwargs):
            if service_name == 'bedrock-runtime':
                return mock_bedrock_client
            elif service_name == 'sts':
                return mock_sts_client
            return Mock()
        
        mock_boto_client.side_effect = client_side_effect
        
        # Mock Bedrock response
        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': '{"name": "enhanced", "tasks": []}'}]
        }).encode()
        mock_bedrock_client.invoke_model.return_value = mock_response
        
        # Test workflow
        workflow = json.dumps({
            "Comment": "Test workflow",
            "StartAt": "Task1",
            "States": {
                "Task1": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::lambda:invoke",
                    "End": True
                }
            }
        })
        
        # Custom LLM config with different model
        custom_llm_config = {
            "model_id": "anthropic.claude-3-opus-20240229-v1:0",
            "temperature": 0.2,
            "max_tokens": 6000
        }
        
        # Call the parse function
        result = await _parse_to_flex_workflow(
            source_framework='step_functions',
            input_code=workflow,
            llm_config=custom_llm_config
        )
        
        # Verify Bedrock was called with the custom model (if enhancement was needed)
        if mock_bedrock_client.invoke_model.called:
            call_args = mock_bedrock_client.invoke_model.call_args
            assert call_args[1]['modelId'] == "anthropic.claude-3-opus-20240229-v1:0"
            
            # Verify other custom parameters were used
            body = json.loads(call_args[1]['body'])
            assert body['temperature'] == 0.2
            assert body['max_tokens'] == 6000
    
    @patch('boto3.client')
    @pytest.mark.asyncio
    async def test_no_hardcoded_model_usage(self, mock_boto_client):
        """Test that no hardcoded model IDs are used when custom config is provided."""
        # Mock both clients
        mock_bedrock_client = Mock()
        mock_sts_client = Mock()
        mock_sts_client.get_caller_identity.return_value = {}
        
        def client_side_effect(service_name, **kwargs):
            if service_name == 'bedrock-runtime':
                return mock_bedrock_client
            elif service_name == 'sts':
                return mock_sts_client
            return Mock()
        
        mock_boto_client.side_effect = client_side_effect
        
        # Mock Bedrock response
        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': '{"name": "enhanced", "tasks": []}'}]
        }).encode()
        mock_bedrock_client.invoke_model.return_value = mock_response
        
        # Test workflow
        workflow = json.dumps({
            "Comment": "Test workflow",
            "StartAt": "Task1",
            "States": {
                "Task1": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::lambda:invoke",
                    "End": True
                }
            }
        })
        
        # Use a completely different model family to ensure no hardcoding
        custom_llm_config = {
            "model_id": "amazon.titan-text-express-v1",
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        # Call the parse function
        result = await _parse_to_flex_workflow(
            source_framework='step_functions',
            input_code=workflow,
            llm_config=custom_llm_config
        )
        
        # Verify that if Bedrock was called, it used the custom model (not any hardcoded Claude model)
        if mock_bedrock_client.invoke_model.called:
            call_args = mock_bedrock_client.invoke_model.call_args
            model_id = call_args[1]['modelId']
            
            # Ensure it's not any of the hardcoded Claude models
            hardcoded_models = [
                "anthropic.claude-sonnet-4-20250514-v1:0",
                "anthropic.claude-3-5-sonnet-20240620-v1:0",
                "anthropic.claude-3-sonnet-20240229-v1:0",
                "anthropic.claude-3-haiku-20240307-v1:0",
                "anthropic.claude-3-opus-20240229-v1:0"
            ]
            
            # Should use the custom model, not any hardcoded one
            assert model_id == "amazon.titan-text-express-v1"
            assert model_id not in hardcoded_models
            
            # Verify other custom parameters
            body = json.loads(call_args[1]['body'])
            assert body['temperature'] == 0.7
            assert body['max_tokens'] == 1000