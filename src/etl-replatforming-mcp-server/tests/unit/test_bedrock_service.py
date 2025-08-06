#!/usr/bin/env python3

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from awslabs.etl_replatforming_mcp_server.services.bedrock_service import BedrockService
from awslabs.etl_replatforming_mcp_server.models.llm_config import LLMConfig, LLMProvider


class TestBedrockService:
    """Test cases for BedrockService"""
    
    @patch('boto3.client')
    def test_initialization_default_config(self, mock_boto_client):
        """Test BedrockService initialization with default config"""
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
        
        service = BedrockService()
        
        assert service.config.model_id == LLMProvider.ANTHROPIC_CLAUDE_3_SONNET.value
        assert service.config.max_tokens == 4000
        assert service.config.temperature == 0.1
        # Verify both clients were created
        assert mock_boto_client.call_count == 2
    
    @patch('boto3.client')
    def test_initialization_custom_config(self, mock_boto_client):
        """Test BedrockService initialization with custom config"""
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
        
        custom_config = LLMConfig(
            model_id=LLMProvider.ANTHROPIC_CLAUDE_3_HAIKU.value,
            region="us-west-2",
            temperature=0.2
        )
        service = BedrockService(custom_config)
        
        assert service.config.model_id == LLMProvider.ANTHROPIC_CLAUDE_3_HAIKU.value
        assert service.config.region == "us-west-2"
        assert service.config.temperature == 0.2
        # Verify both clients were created
        assert mock_boto_client.call_count == 2
    
    @patch('boto3.client')
    def test_build_enhancement_prompt(self, mock_boto_client):
        """Test _build_enhancement_prompt method"""
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
        
        service = BedrockService()
        
        incomplete_workflow = {"name": "test", "tasks": []}
        input_code = "test code"
        source_framework = "airflow"
        
        prompt = service._build_enhancement_prompt(incomplete_workflow, input_code, source_framework)
        
        assert "airflow" in prompt
        assert "test code" in prompt
        assert "FLEX workflow" in prompt
        assert "JSON" in prompt
    
    @patch('boto3.client')
    def test_parse_bedrock_response_valid_json(self, mock_boto_client):
        """Test _parse_bedrock_response with valid JSON"""
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
        
        service = BedrockService()
        
        response = 'Here is the enhanced workflow: {"name": "test", "tasks": []}'
        result = service._parse_bedrock_response(response)
        
        assert result == {"name": "test", "tasks": []}
    
    @patch('boto3.client')
    def test_parse_bedrock_response_invalid_json(self, mock_boto_client):
        """Test _parse_bedrock_response with invalid JSON"""
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
        
        service = BedrockService()
        
        response = "This is not JSON"
        result = service._parse_bedrock_response(response)
        
        assert result is None
    
    @patch('boto3.client')
    def test_parse_bedrock_response_no_json(self, mock_boto_client):
        """Test _parse_bedrock_response with no JSON brackets"""
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
        
        service = BedrockService()
        
        response = "No JSON here at all"
        result = service._parse_bedrock_response(response)
        
        assert result is None
    
    @patch('boto3.client')
    def test_parse_bedrock_response_malformed_json(self, mock_boto_client):
        """Test _parse_bedrock_response with malformed JSON"""
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
        
        service = BedrockService()
        
        response = 'Here is the workflow: {"name": "test", "tasks": [}'
        result = service._parse_bedrock_response(response)
        
        assert result is None
    
    @patch('boto3.client')
    def test_invoke_bedrock_success(self, mock_boto_client):
        """Test _invoke_bedrock method success"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Mock response
        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': 'Enhanced workflow response'}]
        }).encode()
        mock_client.invoke_model.return_value = mock_response
        
        service = BedrockService()
        config = LLMConfig()
        result = service._invoke_bedrock("test prompt", config)
        
        assert result == "Enhanced workflow response"
        mock_client.invoke_model.assert_called_once()
        
        # Verify the call arguments
        call_args = mock_client.invoke_model.call_args
        assert call_args[1]['modelId'] == config.model_id
        
        body = json.loads(call_args[1]['body'])
        assert body['max_tokens'] == config.max_tokens
        assert body['temperature'] == config.temperature
        assert body['top_p'] == config.top_p
        assert body['messages'][0]['content'] == "test prompt"
    
    @patch('boto3.client')
    def test_invoke_bedrock_with_extra_params(self, mock_boto_client):
        """Test _invoke_bedrock with extra parameters"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': 'Response'}]
        }).encode()
        mock_client.invoke_model.return_value = mock_response
        
        service = BedrockService()
        config = LLMConfig(extra_params={"stop_sequences": ["Human:"]})
        service._invoke_bedrock("test prompt", config)
        
        call_args = mock_client.invoke_model.call_args
        body = json.loads(call_args[1]['body'])
        assert body['stop_sequences'] == ["Human:"]
    
    @patch('boto3.client')
    def test_enhance_flex_workflow_success(self, mock_boto_client):
        """Test enhance_flex_workflow method success"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Mock successful Bedrock response
        enhanced_workflow = {"name": "enhanced", "tasks": [{"id": "task1"}]}
        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': f'Enhanced: {json.dumps(enhanced_workflow)}'}]
        }).encode()
        mock_client.invoke_model.return_value = mock_response
        
        service = BedrockService()
        incomplete_workflow = {"name": "test", "tasks": []}
        
        result = service.enhance_flex_workflow(
            incomplete_workflow, "input code", "airflow"
        )
        
        assert result == enhanced_workflow
    
    @patch('boto3.client')
    def test_enhance_flex_workflow_with_custom_config(self, mock_boto_client):
        """Test enhance_flex_workflow with custom config"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        enhanced_workflow = {"name": "enhanced"}
        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': f'{json.dumps(enhanced_workflow)}'}]
        }).encode()
        mock_client.invoke_model.return_value = mock_response
        
        service = BedrockService()
        custom_config = {"temperature": 0.5, "max_tokens": 6000}
        
        result = service.enhance_flex_workflow(
            {}, "code", "airflow", custom_config
        )
        
        assert result == enhanced_workflow
        
        # Verify custom config was used
        call_args = mock_client.invoke_model.call_args
        body = json.loads(call_args[1]['body'])
        assert body['temperature'] == 0.5
        assert body['max_tokens'] == 6000
    
    @patch('boto3.client')
    def test_enhance_flex_workflow_bedrock_failure(self, mock_boto_client):
        """Test enhance_flex_workflow when Bedrock call fails"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.invoke_model.side_effect = Exception("Bedrock error")
        
        service = BedrockService()
        
        result = service.enhance_flex_workflow({}, "code", "airflow")
        
        assert result is None
    
    @patch('boto3.client')
    def test_enhance_flex_workflow_invalid_response(self, mock_boto_client):
        """Test enhance_flex_workflow with invalid response"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        mock_response = {
            'body': Mock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [{'text': 'Invalid JSON response'}]
        }).encode()
        mock_client.invoke_model.return_value = mock_response
        
        service = BedrockService()
        
        result = service.enhance_flex_workflow({}, "code", "airflow")
        
        assert result is None