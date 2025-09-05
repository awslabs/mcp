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

"""Test module for Pydantic models."""

import pytest
from awslabs.amazon_bedrock_agentcore_mcp_server.models import (
    AgentConfig,
    AgentStatus,
    CredentialProviderType,
    DeploymentResult,
    GatewayConfig,
    GatewayTargetType,
    MemoryStrategy,
)
from pydantic import ValidationError


class TestEnums:
    """Test enumeration classes."""

    def test_agent_status_enum(self):
        """Test AgentStatus enumeration."""
        assert AgentStatus.ACTIVE == 'ACTIVE'
        assert AgentStatus.CREATING == 'CREATING'
        assert AgentStatus.FAILED == 'FAILED'

        # Test all values exist
        expected_values = ['ACTIVE', 'CREATING', 'UPDATING', 'DELETING', 'FAILED']
        actual_values = [status.value for status in AgentStatus]
        for expected in expected_values:
            assert expected in actual_values

    def test_memory_strategy_enum(self):
        """Test MemoryStrategy enumeration."""
        assert MemoryStrategy.SEMANTIC == 'semantic'
        assert MemoryStrategy.SUMMARY == 'summary'
        assert MemoryStrategy.EPISODIC == 'episodic'

    def test_gateway_target_type_enum(self):
        """Test GatewayTargetType enumeration."""
        assert GatewayTargetType.LAMBDA == 'lambda'
        assert GatewayTargetType.OPENAPI_SCHEMA == 'openApiSchema'
        assert GatewayTargetType.SMITHY_MODEL == 'smithyModel'

    def test_credential_provider_type_enum(self):
        """Test CredentialProviderType enumeration."""
        assert CredentialProviderType.API_KEY == 'API_KEY'  # pragma: allowlist secret
        assert CredentialProviderType.OAUTH == 'OAUTH'
        assert CredentialProviderType.CUSTOM == 'CUSTOM'


class TestAgentConfig:
    """Test AgentConfig model."""

    def test_agent_config_minimal(self):
        """Test AgentConfig with minimal required fields."""
        config = AgentConfig(name='test-agent')

        assert config.name == 'test-agent'
        assert config.description is None
        assert config.region == 'us-east-1'  # default
        assert config.enable_oauth is False  # default
        assert config.memory_enabled is False  # default

    def test_agent_config_full(self):
        """Test AgentConfig with all fields."""
        config = AgentConfig(
            name='my-agent',
            description='A test agent',
            region='us-west-2',
            enable_oauth=True,
            memory_enabled=True,
        )

        assert config.name == 'my-agent'
        assert config.description == 'A test agent'
        assert config.region == 'us-west-2'
        assert config.enable_oauth is True
        assert config.memory_enabled is True

    def test_agent_config_validation_empty_name(self):
        """Test AgentConfig validates non-empty name."""
        with pytest.raises(ValidationError):
            AgentConfig(name='')

        # Also test missing name parameter (should raise ValidationError)
        with pytest.raises(ValidationError):
            AgentConfig(name=None)  # type: ignore


class TestGatewayConfig:
    """Test GatewayConfig model."""

    def test_gateway_config_minimal(self):
        """Test GatewayConfig with minimal required fields."""
        config = GatewayConfig(name='test-gateway', target_type=GatewayTargetType.LAMBDA)

        assert config.name == 'test-gateway'
        assert config.target_type == GatewayTargetType.LAMBDA
        assert config.description is None
        assert config.region == 'us-east-1'  # default

    def test_gateway_config_smithy_model(self):
        """Test GatewayConfig with Smithy model."""
        config = GatewayConfig(
            name='dynamodb-gateway',
            target_type=GatewayTargetType.SMITHY_MODEL,
            smithy_model='dynamodb',
            region='us-west-2',
        )

        assert config.name == 'dynamodb-gateway'
        assert config.target_type == GatewayTargetType.SMITHY_MODEL
        assert config.smithy_model == 'dynamodb'
        assert config.region == 'us-west-2'

    def test_gateway_config_openapi(self):
        """Test GatewayConfig with OpenAPI spec."""
        openapi_spec = {
            'openapi': '3.0.0',
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {},
        }

        config = GatewayConfig(
            name='api-gateway',
            target_type=GatewayTargetType.OPENAPI_SCHEMA,
            openapi_spec=openapi_spec,
            api_key='test-key-123',  # pragma: allowlist secret
        )

        assert config.name == 'api-gateway'
        assert config.target_type == GatewayTargetType.OPENAPI_SCHEMA
        assert config.openapi_spec == openapi_spec
        assert config.api_key == 'test-key-123'  # pragma: allowlist secret


class TestDeploymentResult:
    """Test DeploymentResult model."""

    def test_deployment_result_success(self):
        """Test successful deployment result."""
        result = DeploymentResult(
            success=True,
            agent_name='my-agent',
            agent_arn='arn:aws:bedrock:us-east-1:123456789012:agent/ABCD1234',
            message='Agent deployed successfully',
            oauth_enabled=True,
        )

        assert result.success is True
        assert result.agent_name == 'my-agent'
        assert result.agent_arn is not None
        assert 'deployed successfully' in result.message
        assert result.oauth_enabled is True

    def test_deployment_result_failure(self):
        """Test failed deployment result."""
        result = DeploymentResult(
            success=False,
            agent_name='failed-agent',
            message='Deployment failed: invalid configuration',
        )

        assert result.success is False
        assert result.agent_name == 'failed-agent'
        assert result.agent_arn is None  # default
        assert 'failed' in result.message
        assert result.oauth_enabled is False  # default

    def test_deployment_result_validation(self):
        """Test DeploymentResult field validation."""
        # Should require success and agent_name
        with pytest.raises(ValidationError):
            DeploymentResult(success=None, agent_name=None, message='test')  # type: ignore


class TestModelSerialization:
    """Test model serialization and deserialization."""

    def test_agent_config_dict_conversion(self):
        """Test converting AgentConfig to/from dict."""
        original_config = AgentConfig(
            name='test-agent', description='Test description', enable_oauth=True
        )

        # Convert to dict
        config_dict = original_config.model_dump()
        assert config_dict['name'] == 'test-agent'
        assert config_dict['enable_oauth'] is True

        # Convert back from dict
        restored_config = AgentConfig(**config_dict)
        assert restored_config.name == original_config.name
        assert restored_config.enable_oauth == original_config.enable_oauth

    def test_gateway_config_json_serialization(self):
        """Test JSON serialization of GatewayConfig."""
        config = GatewayConfig(
            name='test-gateway', target_type=GatewayTargetType.SMITHY_MODEL, smithy_model='s3'
        )

        # Should be able to serialize to JSON
        json_str = config.model_dump_json()
        assert 'test-gateway' in json_str
        assert 'smithyModel' in json_str
        assert 's3' in json_str


if __name__ == '__main__':
    # Run basic model tests
    print('Testing Pydantic models...')

    # Test enum creation
    status = AgentStatus.ACTIVE
    print(f'✓ AgentStatus enum: {status}')

    # Test model creation
    agent_config = AgentConfig(name='test-agent')
    print(f'✓ AgentConfig model: {agent_config.name}')

    # Test model with enum
    gateway_config = GatewayConfig(name='test-gateway', target_type=GatewayTargetType.LAMBDA)
    print(f'✓ GatewayConfig model: {gateway_config.target_type}')

    print('All model tests passed!')
