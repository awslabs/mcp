#!/usr/bin/env python3

"""Tests to verify that llm_config parameters are actually used and not hardcoded."""

import pytest
import json
from unittest.mock import Mock, patch, call

from awslabs.etl_replatforming_mcp_server.services.bedrock_service import BedrockService
from awslabs.etl_replatforming_mcp_server.models.llm_config import LLMConfig, LLMProvider
from awslabs.etl_replatforming_mcp_server.server import _parse_to_flex_workflow


class TestLLMConfigUsage:
    """Test that llm_config parameters are actually used in Bedrock calls."""
    
    @patch('boto3.client')
    def test_bedrock_service_uses_custom_model_id(self, mock_boto_client):
        """Test that BedrockService uses custom model_id from config."""
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
        
        # Mock successful Bedrock response
        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': '{"name": "test", "tasks": []}'}]
        }).encode()
        mock_bedrock_client.invoke_model.return_value = mock_response
        
        # Test with custom model
        custom_model = "anthropic.claude-3-haiku-20240307-v1:0"
        custom_config = {"model_id": custom_model, "temperature": 0.5, "max_tokens": 2000}
        
        service = BedrockService()
        service.enhance_flex_workflow(
            {"name": "test"}, "test code", "airflow", custom_config
        )
        
        # Verify the custom model was used
        mock_bedrock_client.invoke_model.assert_called_once()
        call_args = mock_bedrock_client.invoke_model.call_args
        
        assert call_args[1]['modelId'] == custom_model
        
        # Verify other custom parameters were used
        body = json.loads(call_args[1]['body'])
        assert body['temperature'] == 0.5
        assert body['max_tokens'] == 2000
    
    @patch('boto3.client')
    def test_bedrock_service_uses_default_model_when_no_custom_config(self, mock_boto_client):
        """Test that BedrockService uses default model when no custom config provided."""
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
        
        # Mock successful response
        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': '{"name": "test", "tasks": []}'}]
        }).encode()
        mock_bedrock_client.invoke_model.return_value = mock_response
        
        service = BedrockService()
        service.enhance_flex_workflow(
            {"name": "test"}, "test code", "airflow"
        )
        
        # Verify default model was used
        mock_bedrock_client.invoke_model.assert_called_once()
        call_args = mock_bedrock_client.invoke_model.call_args
        
        assert call_args[1]['modelId'] == LLMProvider.ANTHROPIC_CLAUDE_SONNET_4.value
        
        # Verify default parameters were used
        body = json.loads(call_args[1]['body'])
        assert body['temperature'] == 0.1
        assert body['max_tokens'] == 50000
    
    @patch('boto3.client')
    def test_bedrock_service_uses_different_models_in_sequence(self, mock_boto_client):
        """Test that BedrockService can use different models in sequence."""
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
        
        # Mock successful response
        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': '{"name": "test", "tasks": []}'}]
        }).encode()
        mock_bedrock_client.invoke_model.return_value = mock_response
        
        service = BedrockService()
        
        # First call with Claude Haiku
        haiku_config = {"model_id": "anthropic.claude-3-haiku-20240307-v1:0"}
        service.enhance_flex_workflow(
            {"name": "test1"}, "test code", "airflow", haiku_config
        )
        
        # Second call with Claude Opus
        opus_config = {"model_id": "anthropic.claude-3-opus-20240229-v1:0"}
        service.enhance_flex_workflow(
            {"name": "test2"}, "test code", "airflow", opus_config
        )
        
        # Verify both models were used
        assert mock_bedrock_client.invoke_model.call_count == 2
        
        calls = mock_bedrock_client.invoke_model.call_args_list
        assert calls[0][1]['modelId'] == "anthropic.claude-3-haiku-20240307-v1:0"
        assert calls[1][1]['modelId'] == "anthropic.claude-3-opus-20240229-v1:0"
    

    
    @patch('boto3.client')
    def test_bedrock_service_handles_extra_params(self, mock_boto_client):
        """Test that BedrockService properly handles extra_params in config."""
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
        
        # Mock successful response
        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': '{"name": "test", "tasks": []}'}]
        }).encode()
        mock_bedrock_client.invoke_model.return_value = mock_response
        
        # Test with extra parameters
        custom_config = {
            "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
            "extra_params": {
                "stop_sequences": ["Human:", "Assistant:"],
                "system": "You are a helpful assistant"
            }
        }
        
        service = BedrockService()
        service.enhance_flex_workflow(
            {"name": "test"}, "test code", "airflow", custom_config
        )
        
        # Verify extra params were included in the request body
        mock_bedrock_client.invoke_model.assert_called_once()
        call_args = mock_bedrock_client.invoke_model.call_args
        
        body = json.loads(call_args[1]['body'])
        assert body['stop_sequences'] == ["Human:", "Assistant:"]
        assert body['system'] == "You are a helpful assistant"
    
    @patch('boto3.client')
    def test_bedrock_service_uses_custom_region(self, mock_boto_client):
        """Test that BedrockService uses custom region from config."""
        # Mock clients
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
        
        # Test with custom region
        custom_region = "eu-west-1"
        custom_config = LLMConfig(region=custom_region)
        
        service = BedrockService(custom_config)
        
        # Verify client was created with custom region
        bedrock_calls = [call for call in mock_boto_client.call_args_list 
                        if call[0][0] == 'bedrock-runtime']
        assert len(bedrock_calls) > 0
        assert bedrock_calls[0][1]['region_name'] == custom_region