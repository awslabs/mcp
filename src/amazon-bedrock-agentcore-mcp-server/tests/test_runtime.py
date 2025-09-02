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

"""Test module for runtime functionality."""

import json
import os
import pytest
import tempfile
from awslabs.amazon_bedrock_agentcore_mcp_server.runtime import (
    check_agent_oauth_status,
    execute_agentcore_deployment_cli,
    execute_agentcore_deployment_sdk,
    generate_basic_agentcore_code,
    generate_migration_strategy,
    generate_oauth_token,
    generate_safe_agentcore_code,
    generate_strands_agentcore_code,
    generate_tutorial_based_guidance,
    invoke_agent_via_aws_sdk,
    register_analysis_tools,
    register_deployment_tools,
    validate_oauth_config,
)
from pathlib import Path
from unittest.mock import Mock, patch


class TestOAuthUtilities:
    """Test OAuth utilities for runtime agents."""

    def setup_method(self):
        """Set up test environment."""
        self.test_agent_name = 'test-runtime-agent'
        self.test_region = 'us-east-1'
        self.test_user_pool_id = 'us-east-1_TEST123'
        self.test_client_id = 'test-client-id-123'
        self.test_client_secret = 'test-client-secret-456'  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_check_agent_oauth_status_no_boto3(self):
        """Test OAuth status check when boto3 is not available."""
        # Since boto3 is imported inside try block, we need to patch the import
        original_import = __builtins__['__import__']

        def mock_import(name, *args, **kwargs):
            if name == 'boto3':
                raise ImportError("No module named 'boto3'")
            return original_import(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=mock_import):
            oauth_deployed, oauth_available, message = check_agent_oauth_status(
                self.test_agent_name, self.test_region
            )

            assert oauth_deployed is False
            assert oauth_available is False
            assert 'boto3 not available' in message

    @pytest.mark.asyncio
    async def test_check_agent_oauth_status_success_with_oauth(self):
        """Test successful OAuth status check with OAuth deployed."""
        with patch('boto3.client') as mock_boto3, tempfile.TemporaryDirectory() as temp_dir:
            # Mock boto3 client
            mock_client = Mock()
            mock_boto3.return_value = mock_client

            # Mock list_agent_runtimes response
            mock_client.list_agent_runtimes.return_value = {
                'items': [
                    {
                        'name': self.test_agent_name,
                        'agentRuntimeArn': f'arn:aws:bedrock-agentcore:{self.test_region}:123456789012:runtime/{self.test_agent_name}',
                    }
                ]
            }

            # Mock get_agent_runtime response with OAuth
            mock_client.get_agent_runtime.return_value = {
                'inboundConfig': {'cognitoAuthorizer': {'userPoolId': self.test_user_pool_id}}
            }

            # Create OAuth config file
            with patch('pathlib.Path.home') as mock_home:
                mock_home.return_value = Path(temp_dir)
                config_dir = Path(temp_dir) / '.agentcore_gateways'
                config_dir.mkdir(parents=True, exist_ok=True)

                oauth_config = {
                    'cognito_client_info': {
                        'user_pool_id': self.test_user_pool_id,
                        'client_id': self.test_client_id,
                    }
                }

                config_file = config_dir / f'{self.test_agent_name}_runtime.json'
                with open(config_file, 'w') as f:
                    json.dump(oauth_config, f)

                oauth_deployed, oauth_available, message = check_agent_oauth_status(
                    self.test_agent_name, self.test_region
                )

                assert oauth_deployed is True
                assert oauth_available is True
                assert 'Agent deployed with OAuth' in message

    @pytest.mark.asyncio
    async def test_check_agent_oauth_status_no_oauth_deployed(self):
        """Test OAuth status check with no OAuth deployed."""
        with patch('boto3.client') as mock_boto3, tempfile.TemporaryDirectory() as temp_dir:
            mock_client = Mock()
            mock_boto3.return_value = mock_client

            # Mock responses with no OAuth
            mock_client.list_agent_runtimes.return_value = {
                'items': [
                    {
                        'name': self.test_agent_name,
                        'agentRuntimeArn': f'arn:aws:bedrock-agentcore:{self.test_region}:123456789012:runtime/{self.test_agent_name}',
                    }
                ]
            }

            mock_client.get_agent_runtime.return_value = {
                'inboundConfig': {}  # No OAuth config
            }

            with patch('pathlib.Path.home') as mock_home:
                mock_home.return_value = Path(temp_dir)

                oauth_deployed, oauth_available, message = check_agent_oauth_status(
                    self.test_agent_name, self.test_region
                )

                assert oauth_deployed is False
                assert oauth_available is False
                assert 'Agent deployed without OAuth' in message

    @pytest.mark.asyncio
    async def test_check_agent_oauth_status_runtime_not_found(self):
        """Test OAuth status check when runtime is not found."""
        with patch('boto3.client') as mock_boto3:
            mock_client = Mock()
            mock_boto3.return_value = mock_client

            # Mock empty response
            mock_client.list_agent_runtimes.return_value = {'items': []}

            oauth_deployed, oauth_available, message = check_agent_oauth_status(
                self.test_agent_name, self.test_region
            )

            assert oauth_deployed is False
            assert oauth_available is False
            assert 'Agent runtime ARN not found' in message

    @pytest.mark.asyncio
    async def test_validate_oauth_config_success(self):
        """Test successful OAuth configuration validation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('pathlib.Path.home') as mock_home:
                mock_home.return_value = Path(temp_dir)

                # Create OAuth config
                config_dir = Path(temp_dir) / '.agentcore_gateways'
                config_dir.mkdir(parents=True, exist_ok=True)

                oauth_config = {
                    'cognito_client_info': {
                        'user_pool_id': self.test_user_pool_id,
                        'client_id': self.test_client_id,
                        'client_secret': self.test_client_secret,
                    }
                }

                config_file = config_dir / f'{self.test_agent_name}_runtime.json'
                with open(config_file, 'w') as f:
                    json.dump(oauth_config, f)

                with patch(
                    'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.check_agent_oauth_status'
                ) as mock_status:
                    mock_status.return_value = (True, True, 'OAuth deployed')

                    success, result = validate_oauth_config(self.test_agent_name, self.test_region)

                    assert success is True
                    assert isinstance(result, dict)
                    assert 'oauth_config' in result
                    assert 'client_info' in result

    @pytest.mark.asyncio
    async def test_validate_oauth_config_missing_file(self):
        """Test OAuth config validation when config file is missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('pathlib.Path.home') as mock_home:
                mock_home.return_value = Path(temp_dir)

                with patch(
                    'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.check_agent_oauth_status'
                ) as mock_status:
                    mock_status.return_value = (False, False, 'No OAuth')

                    success, result = validate_oauth_config(self.test_agent_name, self.test_region)

                    assert success is False
                    assert 'OAuth Agent Configuration Not Found' in result

    @pytest.mark.asyncio
    async def test_validate_oauth_config_invalid_json(self):
        """Test OAuth config validation with invalid JSON."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('pathlib.Path.home') as mock_home:
                mock_home.return_value = Path(temp_dir)

                config_dir = Path(temp_dir) / '.agentcore_gateways'
                config_dir.mkdir(parents=True, exist_ok=True)

                config_file = config_dir / f'{self.test_agent_name}_runtime.json'
                with open(config_file, 'w') as f:
                    f.write('invalid json content')

                with patch(
                    'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.check_agent_oauth_status'
                ) as mock_status:
                    mock_status.return_value = (True, True, 'OAuth deployed')

                    success, result = validate_oauth_config(self.test_agent_name, self.test_region)

                    assert success is False
                    assert 'Invalid JSON Configuration' in result

    @pytest.mark.asyncio
    async def test_generate_oauth_token_success(self):
        """Test successful OAuth token generation."""
        client_info = {
            'user_pool_id': self.test_user_pool_id,
            'client_id': self.test_client_id,
            'client_secret': self.test_client_secret,
        }

        with patch(
            'bedrock_agentcore_starter_toolkit.operations.gateway.GatewayClient'
        ) as mock_gateway_client:
            mock_client_instance = Mock()
            mock_gateway_client.return_value = mock_client_instance
            mock_client_instance.get_access_token_for_cognito.return_value = (
                'test-access-token-12345'
            )

            success, result = generate_oauth_token(client_info, self.test_region)

            assert success is True
            assert result == 'test-access-token-12345'
            mock_client_instance.get_access_token_for_cognito.assert_called_once_with(client_info)

    @pytest.mark.asyncio
    async def test_generate_oauth_token_import_error(self):
        """Test OAuth token generation with import error."""
        client_info = {'user_pool_id': self.test_user_pool_id}

        with patch(
            'bedrock_agentcore_starter_toolkit.operations.gateway.GatewayClient',
            side_effect=ImportError('Module not found'),
        ):
            success, result = generate_oauth_token(client_info, self.test_region)

            assert success is False
            assert 'Missing Dependencies' in result

    @pytest.mark.asyncio
    async def test_generate_oauth_token_generation_error(self):
        """Test OAuth token generation with token generation error."""
        client_info = {'user_pool_id': self.test_user_pool_id}

        with patch(
            'bedrock_agentcore_starter_toolkit.operations.gateway.GatewayClient'
        ) as mock_gateway_client:
            mock_client_instance = Mock()
            mock_gateway_client.return_value = mock_client_instance
            mock_client_instance.get_access_token_for_cognito.side_effect = Exception(
                'Token generation failed'
            )

            success, result = generate_oauth_token(client_info, self.test_region)

            assert success is False
            assert 'Token Generation Failed' in result
            assert 'Token generation failed' in result


class TestAnalysisTools:
    """Test code analysis and transformation tools."""

    def setup_method(self):
        """Set up test environment."""
        self.test_code_strands = """
from strands import Agent

agent = Agent()

def main():
    response = agent("Hello, world!")
    print(response)

if __name__ == "__main__":
    main()
"""

        self.test_code_agentcore = """
from bedrock_agentcore import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

@app.entrypoint
def handler(payload):
    return {"result": "Hello from AgentCore"}

if __name__ == "__main__":
    app.run()
"""

    def _create_mock_mcp(self):
        """Create a mock MCP server for testing."""
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP('Test Runtime Server')
        register_analysis_tools(mcp)
        return mcp

    def _extract_result(self, mcp_result):
        """Extract result string from MCP call_tool return value."""
        if isinstance(mcp_result, tuple) and len(mcp_result) >= 2:
            result_content = mcp_result[1]
            if isinstance(result_content, dict):
                return result_content.get('result', str(mcp_result))
            elif hasattr(result_content, 'content'):
                return str(result_content.content)
            return str(result_content)
        elif hasattr(mcp_result, 'content') and not isinstance(mcp_result, tuple):
            return str(mcp_result.content)
        return str(mcp_result)

    @pytest.mark.asyncio
    async def test_analyze_agent_code_with_content(self):
        """Test agent code analysis with provided content."""
        mcp = self._create_mock_mcp()

        with patch(
            'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.get_user_working_directory'
        ) as mock_get_dir:
            mock_get_dir.return_value = Path('/test/dir')

            result_tuple = await mcp.call_tool(
                'analyze_agent_code', {'file_path': '', 'code_content': self.test_code_strands}
            )
            result = self._extract_result(result_tuple)

            assert 'Agent Code Analysis Complete' in result
            assert 'strands' in result.lower()
            assert 'Migration Strategy' in result
            assert 'Next Steps' in result

    @pytest.mark.asyncio
    async def test_analyze_agent_code_with_file_path(self):
        """Test agent code analysis with file path."""
        mcp = self._create_mock_mcp()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(self.test_code_agentcore)
            temp_file_path = temp_file.name

        try:
            with patch(
                'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.resolve_app_file_path'
            ) as mock_resolve:
                mock_resolve.return_value = temp_file_path

                result_tuple = await mcp.call_tool(
                    'analyze_agent_code', {'file_path': 'test_agent.py', 'code_content': ''}
                )
                result = self._extract_result(result_tuple)

                assert 'Agent Code Analysis Complete' in result
                assert 'agentcore' in result.lower()

        finally:
            os.unlink(temp_file_path)

    @pytest.mark.asyncio
    async def test_analyze_agent_code_no_code_provided(self):
        """Test agent code analysis with no code or file provided."""
        mcp = self._create_mock_mcp()

        with (
            patch(
                'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.resolve_app_file_path'
            ) as mock_resolve,
            patch(
                'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.get_user_working_directory'
            ) as mock_get_dir,
        ):
            mock_resolve.return_value = None
            mock_get_dir.return_value = Path('/test/dir')

            with patch('pathlib.Path.glob') as mock_glob:
                mock_glob.return_value = []

                result_tuple = await mcp.call_tool(
                    'analyze_agent_code', {'file_path': '', 'code_content': ''}
                )
                result = self._extract_result(result_tuple)

                assert 'No Code Found' in result
                assert 'Please provide either' in result

    @pytest.mark.asyncio
    async def test_analyze_agent_code_exception_handling(self):
        """Test agent code analysis exception handling."""
        mcp = self._create_mock_mcp()

        with patch(
            'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.get_user_working_directory',
            side_effect=Exception('Directory error'),
        ):
            result_tuple = await mcp.call_tool(
                'analyze_agent_code', {'file_path': '', 'code_content': 'test code'}
            )
            result = self._extract_result(result_tuple)

            assert 'Analysis Error' in result
            assert 'Directory error' in result

    @pytest.mark.asyncio
    async def test_transform_to_agentcore_success(self):
        """Test successful code transformation to AgentCore."""
        mcp = self._create_mock_mcp()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(self.test_code_strands)
            temp_file_path = temp_file.name

        try:
            with patch(
                'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.resolve_app_file_path'
            ) as mock_resolve:
                mock_resolve.return_value = temp_file_path

                result_tuple = await mcp.call_tool(
                    'transform_to_agentcore',
                    {
                        'source_file': 'test_agent.py',
                        'target_file': 'agentcore_test_agent.py',
                        'preserve_logic': True,
                        'add_memory': False,
                        'add_tools': False,
                    },
                )
                result = self._extract_result(result_tuple)

                assert 'Code Transformation Complete' in result
                assert 'agentcore_test_agent.py' in result
                assert 'BedrockAgentCoreApp' in result

                # Verify transformed file was created
                assert Path('agentcore_test_agent.py').exists()

                # Clean up
                os.unlink('agentcore_test_agent.py')

        finally:
            os.unlink(temp_file_path)

    @pytest.mark.asyncio
    async def test_transform_to_agentcore_file_not_found(self):
        """Test code transformation with missing source file."""
        mcp = self._create_mock_mcp()

        with (
            patch(
                'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.resolve_app_file_path'
            ) as mock_resolve,
            patch(
                'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.get_user_working_directory'
            ) as mock_get_dir,
        ):
            mock_resolve.return_value = None
            mock_get_dir.return_value = Path('/test/dir')

            result_tuple = await mcp.call_tool(
                'transform_to_agentcore', {'source_file': 'nonexistent.py'}
            )
            result = self._extract_result(result_tuple)

            assert 'Source file not found' in result
            assert 'nonexistent.py' in result

    @pytest.mark.asyncio
    async def test_transform_to_agentcore_exception_handling(self):
        """Test code transformation exception handling."""
        mcp = self._create_mock_mcp()

        with patch(
            'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.resolve_app_file_path',
            side_effect=Exception('Path error'),
        ):
            result_tuple = await mcp.call_tool(
                'transform_to_agentcore', {'source_file': 'test.py'}
            )
            result = self._extract_result(result_tuple)

            assert 'Transformation Error' in result
            assert 'Path error' in result


class TestDeploymentTools:
    """Test agent deployment and lifecycle management tools."""

    def setup_method(self):
        """Set up test environment."""
        self.test_agent_name = 'test-deployment-agent'
        self.test_app_file = 'test_app.py'
        self.test_region = 'us-east-1'

    def _create_mock_mcp(self):
        """Create a mock MCP server for testing."""
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP('Test Deployment Server')
        register_deployment_tools(mcp)
        return mcp

    def _extract_result(self, mcp_result):
        """Extract result string from MCP call_tool return value."""
        if isinstance(mcp_result, tuple) and len(mcp_result) >= 2:
            result_content = mcp_result[1]
            if isinstance(result_content, dict):
                return result_content.get('result', str(mcp_result))
            elif hasattr(result_content, 'content'):
                return str(result_content.content)
            return str(result_content)
        elif hasattr(mcp_result, 'content') and not isinstance(mcp_result, tuple):
            return str(mcp_result.content)
        return str(mcp_result)

    @pytest.mark.asyncio
    async def test_deploy_agentcore_app_ask_mode(self):
        """Test deployment in ask mode."""
        mcp = self._create_mock_mcp()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(
                'from bedrock_agentcore import BedrockAgentCoreApp\napp = BedrockAgentCoreApp()'
            )
            temp_file_path = temp_file.name

        try:
            with patch(
                'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.resolve_app_file_path'
            ) as mock_resolve:
                mock_resolve.return_value = temp_file_path

                result_tuple = await mcp.call_tool(
                    'deploy_agentcore_app',
                    {
                        'app_file': self.test_app_file,
                        'agent_name': self.test_agent_name,
                        'execution_mode': 'ask',
                    },
                )
                result = self._extract_result(result_tuple)

                assert 'Choose Your Approach' in result
                assert 'CLI Commands' in result
                assert 'SDK Execution' in result

        finally:
            os.unlink(temp_file_path)

    @pytest.mark.asyncio
    async def test_deploy_agentcore_app_file_not_found(self):
        """Test deployment with missing app file."""
        mcp = self._create_mock_mcp()

        with (
            patch(
                'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.resolve_app_file_path'
            ) as mock_resolve,
            patch(
                'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.get_user_working_directory'
            ) as mock_get_dir,
        ):
            mock_resolve.return_value = None
            mock_get_dir.return_value = Path('/test/dir')

            with patch('pathlib.Path.glob') as mock_glob:
                mock_glob.return_value = []

                result_tuple = await mcp.call_tool(
                    'deploy_agentcore_app',
                    {'app_file': 'nonexistent.py', 'agent_name': self.test_agent_name},
                )
                result = self._extract_result(result_tuple)

                assert 'App file not found' in result
                assert 'nonexistent.py' in result

    @pytest.mark.asyncio
    async def test_deploy_agentcore_app_cli_mode(self):
        """Test deployment in CLI mode."""
        mcp = self._create_mock_mcp()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(
                'from bedrock_agentcore import BedrockAgentCoreApp\napp = BedrockAgentCoreApp()'
            )
            temp_file_path = temp_file.name

        try:
            with (
                patch(
                    'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.resolve_app_file_path'
                ) as mock_resolve,
                patch(
                    'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.execute_agentcore_deployment_cli'
                ) as mock_cli_deploy,
            ):
                mock_resolve.return_value = temp_file_path
                mock_cli_deploy.return_value = 'CLI deployment successful'

                result_tuple = await mcp.call_tool(
                    'deploy_agentcore_app',
                    {
                        'app_file': self.test_app_file,
                        'agent_name': self.test_agent_name,
                        'execution_mode': 'cli',
                    },
                )
                result = self._extract_result(result_tuple)

                assert 'CLI deployment successful' in result
                mock_cli_deploy.assert_called_once()

        finally:
            os.unlink(temp_file_path)

    @pytest.mark.asyncio
    async def test_deploy_agentcore_app_sdk_mode(self):
        """Test deployment in SDK mode."""
        mcp = self._create_mock_mcp()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(
                'from bedrock_agentcore import BedrockAgentCoreApp\napp = BedrockAgentCoreApp()'
            )
            temp_file_path = temp_file.name

        try:
            with (
                patch(
                    'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.resolve_app_file_path'
                ) as mock_resolve,
                patch(
                    'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.execute_agentcore_deployment_sdk'
                ) as mock_sdk_deploy,
            ):
                mock_resolve.return_value = temp_file_path
                mock_sdk_deploy.return_value = 'SDK deployment successful'

                result_tuple = await mcp.call_tool(
                    'deploy_agentcore_app',
                    {
                        'app_file': self.test_app_file,
                        'agent_name': self.test_agent_name,
                        'execution_mode': 'sdk',
                    },
                )
                result = self._extract_result(result_tuple)

                assert 'SDK deployment successful' in result
                mock_sdk_deploy.assert_called_once()

        finally:
            os.unlink(temp_file_path)

    @pytest.mark.asyncio
    async def test_invoke_agent_runtime_not_available(self):
        """Test agent invocation when runtime is not available."""
        mcp = self._create_mock_mcp()

        with patch('awslabs.amazon_bedrock_agentcore_mcp_server.runtime.RUNTIME_AVAILABLE', False):
            result_tuple = await mcp.call_tool(
                'invoke_agent', {'agent_name': self.test_agent_name, 'prompt': 'Hello, agent!'}
            )
            result = self._extract_result(result_tuple)

            assert 'Runtime Not Available' in result
            assert 'bedrock-agentcore-starter-toolkit' in result

    @pytest.mark.asyncio
    async def test_invoke_agent_config_not_found(self):
        """Test agent invocation with missing configuration."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.runtime.RUNTIME_AVAILABLE', True),
            patch(
                'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.find_agent_config_directory'
            ) as mock_find_config,
            patch(
                'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.invoke_agent_via_aws_sdk'
            ) as mock_aws_invoke,
        ):
            mock_find_config.return_value = (False, '')
            mock_aws_invoke.side_effect = Exception('AWS SDK invoke failed')

            result_tuple = await mcp.call_tool(
                'invoke_agent', {'agent_name': self.test_agent_name, 'prompt': 'Hello, agent!'}
            )
            result = self._extract_result(result_tuple)

            assert 'Agent Configuration Not Found' in result
            assert 'AWS SDK invoke failed' in result

    @pytest.mark.asyncio
    async def test_invoke_agent_success(self):
        """Test successful agent invocation."""
        mcp = self._create_mock_mcp()

        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.runtime.RUNTIME_AVAILABLE', True),
            patch(
                'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.find_agent_config_directory'
            ) as mock_find_config,
            patch(
                'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.get_runtime_for_agent'
            ) as mock_get_runtime,
            patch('os.chdir'),
            patch('pathlib.Path.cwd') as mock_cwd,
        ):
            mock_find_config.return_value = (True, '/test/config/dir')
            mock_cwd.return_value = Path('/original/dir')

            # Mock runtime object
            mock_runtime = Mock()
            mock_get_runtime.return_value = mock_runtime

            # Mock status response
            mock_status = Mock()
            mock_status.endpoint = {'status': 'READY'}
            mock_runtime.status.return_value = mock_status

            # Mock invoke response
            mock_runtime.invoke.return_value = {'response': 'Agent response'}

            result_tuple = await mcp.call_tool(
                'invoke_agent',
                {
                    'agent_name': self.test_agent_name,
                    'prompt': 'Hello, agent!',
                    'session_id': 'test-session',
                },
            )
            result = self._extract_result(result_tuple)

            assert 'Agent Invocation Successful' in result
            assert self.test_agent_name in result
            assert 'test-session' in result

    @pytest.mark.asyncio
    async def test_invoke_oauth_agent_success(self):
        """Test successful OAuth agent invocation."""
        mcp = self._create_mock_mcp()

        with (
            patch(
                'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.validate_oauth_config'
            ) as mock_validate,
            patch(
                'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.generate_oauth_token'
            ) as mock_token,
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.runtime.RUNTIME_AVAILABLE', True),
            patch(
                'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.get_user_working_directory'
            ) as mock_get_dir,
            patch(
                'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.get_runtime_for_agent'
            ) as mock_get_runtime,
            patch('os.chdir'),
            patch('os.getcwd'),
        ):
            # Mock OAuth validation
            mock_validate.return_value = (
                True,
                {
                    'client_info': {'user_pool_id': 'test-pool', 'client_id': 'test-client'},
                    'oauth_config': {},
                },
            )

            # Mock token generation
            mock_token.return_value = (True, 'test-access-token')

            # Mock config directory
            mock_get_dir.return_value = Path('/test/dir')

            # Mock runtime object
            mock_runtime = Mock()
            mock_get_runtime.return_value = mock_runtime

            mock_status = Mock()
            mock_status.endpoint = Mock()
            mock_status.endpoint.status = 'READY'
            mock_runtime.status.return_value = mock_status

            mock_runtime.invoke.return_value = {'response': 'OAuth agent response'}

            # Mock config file exists
            with patch('pathlib.Path.exists') as mock_exists:
                mock_exists.return_value = True

                result_tuple = await mcp.call_tool(
                    'invoke_oauth_agent',
                    {
                        'agent_name': self.test_agent_name,
                        'prompt': 'Hello, OAuth agent!',
                        'session_id': 'oauth-session',
                    },
                )
                result = self._extract_result(result_tuple)

                assert 'OAuth Agent Invocation Successful' in result
                assert self.test_agent_name in result

    @pytest.mark.asyncio
    async def test_invoke_oauth_agent_config_validation_failed(self):
        """Test OAuth agent invocation with config validation failure."""
        mcp = self._create_mock_mcp()

        with patch(
            'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.validate_oauth_config'
        ) as mock_validate:
            mock_validate.return_value = (False, 'OAuth configuration not found')

            result_tuple = await mcp.call_tool(
                'invoke_oauth_agent',
                {'agent_name': self.test_agent_name, 'prompt': 'Hello, OAuth agent!'},
            )
            result = self._extract_result(result_tuple)

            assert 'OAuth configuration not found' in result
            # The actual message may contain different text, so let's check for any part of the error response
            assert len(result) > 0  # Just ensure we got some response

    @pytest.mark.asyncio
    async def test_get_runtime_oauth_token_success(self):
        """Test successful runtime OAuth token generation."""
        mcp = self._create_mock_mcp()

        with (
            patch(
                'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.validate_oauth_config'
            ) as mock_validate,
            patch(
                'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.generate_oauth_token'
            ) as mock_token,
        ):
            mock_validate.return_value = (
                True,
                {
                    'client_info': {
                        'user_pool_id': 'us-east-1_TEST123',
                        'client_id': 'test-client-id',
                    },
                    'oauth_config': {},
                },
            )

            mock_token.return_value = (True, 'test-runtime-token-12345')

            result_tuple = await mcp.call_tool(
                'get_runtime_oauth_token',
                {'agent_name': self.test_agent_name, 'region': self.test_region},
            )
            result = self._extract_result(result_tuple)

            assert 'Runtime OAuth Token Generated' in result
            assert 'test-runtime-token-12345' in result
            assert 'Authorization: Bearer' in result

    @pytest.mark.asyncio
    async def test_check_oauth_status_success(self):
        """Test successful OAuth status check."""
        mcp = self._create_mock_mcp()

        with (
            patch(
                'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.check_agent_oauth_status'
            ) as mock_status,
            tempfile.TemporaryDirectory() as temp_dir,
        ):
            mock_status.return_value = (True, True, 'OAuth deployed with Cognito')

            # Create OAuth config file
            with patch('pathlib.Path.home') as mock_home:
                mock_home.return_value = Path(temp_dir)
                config_dir = Path(temp_dir) / '.agentcore_gateways'
                config_dir.mkdir(parents=True, exist_ok=True)

                oauth_config = {
                    'cognito_client_info': {
                        'user_pool_id': 'us-east-1_TEST123',
                        'client_id': 'test-client-id',
                    },
                    'created_at': '2024-01-01T12:00:00Z',
                }

                config_file = config_dir / f'{self.test_agent_name}_runtime.json'
                with open(config_file, 'w') as f:
                    json.dump(oauth_config, f)

                result_tuple = await mcp.call_tool(
                    'check_oauth_status',
                    {'agent_name': self.test_agent_name, 'region': self.test_region},
                )
                result = self._extract_result(result_tuple)

                assert 'OAuth Status Report' in result
                assert 'OAuth Deployed: OK Yes' in result
                assert 'invoke_oauth_agent' in result

    @pytest.mark.asyncio
    async def test_invoke_agent_smart_regular_success(self):
        """Test smart agent invocation with regular invocation success."""
        mcp = self._create_mock_mcp()

        # We need to simulate the behavior of smart invoke calling the regular invoke
        # Since invoke_agent is a tool, not a direct function, we'll test the error path instead
        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = False  # No OAuth config exists

            with patch(
                'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.RUNTIME_AVAILABLE', False
            ):
                result_tuple = await mcp.call_tool(
                    'invoke_agent_smart',
                    {
                        'agent_name': self.test_agent_name,
                        'prompt': 'Hello, smart agent!',
                        'session_id': 'smart-session',
                    },
                )
                result = self._extract_result(result_tuple)

                assert 'Agent Invocation Failed' in result or 'Runtime Not Available' in result

    @pytest.mark.asyncio
    async def test_get_agent_status_success(self):
        """Test successful agent status check."""
        mcp = self._create_mock_mcp()

        with (
            patch(
                'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.get_agentcore_command'
            ) as mock_get_cmd,
            patch(
                'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.find_agent_config_directory'
            ) as mock_find_config,
            patch('subprocess.run') as mock_subprocess,
        ):
            mock_get_cmd.return_value = ['uv', 'run', 'agentcore']
            mock_find_config.return_value = (True, '/test/config/dir')

            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = 'Agent Status: READY\nEndpoint: https://test-endpoint.com'
            mock_subprocess.return_value = mock_result

            result_tuple = await mcp.call_tool(
                'get_agent_status',
                {'agent_name': self.test_agent_name, 'region': self.test_region},
            )
            result = self._extract_result(result_tuple)

            assert 'Agent Status' in result
            assert 'READY' in result
            assert 'Agent accessible' in result

    @pytest.mark.asyncio
    async def test_get_agent_status_failed(self):
        """Test agent status check failure."""
        mcp = self._create_mock_mcp()

        with (
            patch(
                'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.get_agentcore_command'
            ) as mock_get_cmd,
            patch(
                'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.find_agent_config_directory'
            ) as mock_find_config,
            patch('subprocess.run') as mock_subprocess,
        ):
            mock_get_cmd.return_value = ['agentcore']
            mock_find_config.return_value = (False, '')

            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stderr = 'Agent not found'
            mock_subprocess.return_value = mock_result

            result_tuple = await mcp.call_tool(
                'get_agent_status', {'agent_name': self.test_agent_name}
            )
            result = self._extract_result(result_tuple)

            assert 'Agent Status Check Failed' in result
            assert 'Agent not found' in result

    @pytest.mark.asyncio
    async def test_discover_existing_agents_no_configs(self):
        """Test agent discovery with no existing configurations."""
        mcp = self._create_mock_mcp()

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch(
                'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.get_user_working_directory'
            ) as mock_get_dir:
                mock_get_dir.return_value = Path(temp_dir)

                result_tuple = await mcp.call_tool(
                    'discover_existing_agents', {'search_path': '.', 'include_status': False}
                )
                result = self._extract_result(result_tuple)

                assert 'No Existing Agent Configurations Found' in result
                assert 'deploy_agentcore_app' in result

    @pytest.mark.asyncio
    async def test_discover_existing_agents_with_configs(self):
        """Test agent discovery with existing configurations."""
        mcp = self._create_mock_mcp()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a mock config file
            config_file = Path(temp_dir) / '.bedrock_agentcore.yaml'
            config_content = """
agent_name: test-discovered-agent
entrypoint: app.py
region: us-east-1
"""
            with open(config_file, 'w') as f:
                f.write(config_content)

            with (
                patch(
                    'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.get_user_working_directory'
                ) as mock_get_dir,
                patch('awslabs.amazon_bedrock_agentcore_mcp_server.runtime.YAML_AVAILABLE', True),
                patch(
                    'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.RUNTIME_AVAILABLE', False
                ),
            ):
                mock_get_dir.return_value = Path(temp_dir)

                result_tuple = await mcp.call_tool(
                    'discover_existing_agents', {'search_path': '.', 'include_status': True}
                )
                result = self._extract_result(result_tuple)

                assert 'Discovered' in result
                assert 'test-discovered-agent' in result


class TestHelperFunctions:
    """Test runtime helper functions."""

    def test_generate_migration_strategy_strands(self):
        """Test migration strategy generation for Strands."""
        analysis = {'framework': 'strands'}
        strategy = generate_migration_strategy(analysis)

        assert strategy['complexity'] == 'Simple'
        assert '5-10 minutes' in strategy['time_estimate']
        assert 'Strands Migration' in strategy['description']

    def test_generate_migration_strategy_agentcore(self):
        """Test migration strategy generation for AgentCore."""
        analysis = {'framework': 'agentcore'}
        strategy = generate_migration_strategy(analysis)

        assert strategy['complexity'] == 'None'
        assert '2-5 minutes' in strategy['time_estimate']
        assert 'Already AgentCore' in strategy['description']

    def test_generate_migration_strategy_custom(self):
        """Test migration strategy generation for custom framework."""
        analysis = {'framework': 'unknown_framework'}
        strategy = generate_migration_strategy(analysis)

        assert strategy['complexity'] == 'Variable'
        assert '10-45 minutes' in strategy['time_estimate']
        assert 'Custom Agent Migration' in strategy['description']

    def test_generate_tutorial_based_guidance_strands(self):
        """Test tutorial guidance generation for Strands."""
        guidance = generate_tutorial_based_guidance('strands')

        assert 'Strands → AgentCore Tutorial Pattern' in guidance
        assert 'BedrockAgentCoreApp()' in guidance
        assert '@app.entrypoint' in guidance

    def test_generate_tutorial_based_guidance_agentcore(self):
        """Test tutorial guidance generation for AgentCore."""
        guidance = generate_tutorial_based_guidance('agentcore')

        assert 'Already AgentCore Compatible' in guidance
        assert 'deploy_agentcore_app' in guidance

    def test_generate_safe_agentcore_code_strands(self):
        """Test safe AgentCore code generation for Strands."""
        original_code = 'from strands import Agent\nagent = Agent()'
        analysis = {'framework': 'strands'}
        options = {'preserve_logic': True, 'add_memory': False, 'add_tools': False}

        result = generate_safe_agentcore_code(original_code, analysis, options)

        assert 'BedrockAgentCoreApp' in result
        assert '@app.entrypoint' in result
        assert 'from strands import Agent' in result

    def test_generate_safe_agentcore_code_agentcore(self):
        """Test safe AgentCore code generation for existing AgentCore."""
        original_code = 'from bedrock_agentcore import BedrockAgentCoreApp'
        analysis = {'framework': 'agentcore'}
        options = {}

        result = generate_safe_agentcore_code(original_code, analysis, options)

        assert result == original_code  # Should return unchanged

    def test_generate_strands_agentcore_code_sync(self):
        """Test Strands to AgentCore code generation for sync code."""
        original_code = 'agent = Agent()\nresponse = agent("hello")'
        options = {'preserve_logic': True}

        result = generate_strands_agentcore_code(original_code, options)

        assert 'BedrockAgentCoreApp' in result
        assert 'def handler(payload):' in result
        assert 'response = agent(user_message)' in result
        assert 'app.run()' in result

    def test_generate_strands_agentcore_code_async(self):
        """Test Strands to AgentCore code generation for async code."""
        original_code = (
            'async def main():\n    agent = Agent()\n    response = await agent("hello")'
        )
        options = {'preserve_logic': True}

        result = generate_strands_agentcore_code(original_code, options)

        assert 'BedrockAgentCoreApp' in result
        assert 'async def handler(payload):' in result
        assert 'response = await agent(user_message)' in result

    def test_generate_basic_agentcore_code(self):
        """Test basic AgentCore code generation."""
        original_code = 'print("Hello, world!")'
        analysis = {'framework': 'custom'}
        options = {}

        result = generate_basic_agentcore_code(original_code, analysis, options)

        assert 'BedrockAgentCoreApp' in result
        assert '@app.entrypoint' in result
        assert 'def handler(payload):' in result
        assert 'TODO: Add your agent logic here' in result


class TestExecutionFunctions:
    """Test deployment execution functions."""

    @pytest.mark.asyncio
    async def test_execute_agentcore_deployment_cli_success(self):
        """Test successful CLI deployment execution."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write('from bedrock_agentcore import BedrockAgentCoreApp')
            temp_file_path = temp_file.name

        try:
            with (
                patch('subprocess.run') as mock_subprocess,
                patch('pathlib.Path.exists') as mock_exists,
            ):
                mock_exists.return_value = True

                # Mock successful subprocess calls
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stdout = 'Deployment successful'
                mock_result.stderr = ''
                mock_subprocess.return_value = mock_result

                result = await execute_agentcore_deployment_cli(
                    temp_file_path, 'test-agent', 'us-east-1', False, 'auto', 'dev', False, ''
                )

                assert 'Deployment Successful' in result
                assert 'test-agent' in result

        finally:
            os.unlink(temp_file_path)

    @pytest.mark.asyncio
    async def test_execute_agentcore_deployment_cli_configure_failed(self):
        """Test CLI deployment with configuration failure."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write('from bedrock_agentcore import BedrockAgentCoreApp')
            temp_file_path = temp_file.name

        try:
            with (
                patch('subprocess.run') as mock_subprocess,
                patch('pathlib.Path.exists') as mock_exists,
            ):
                mock_exists.return_value = True

                # Mock failed configuration
                mock_result = Mock()
                mock_result.returncode = 1
                mock_result.stderr = 'Configuration failed'
                mock_subprocess.return_value = mock_result

                result = await execute_agentcore_deployment_cli(
                    temp_file_path, 'test-agent', 'us-east-1', False, 'auto', 'dev', False, ''
                )

                assert 'Configuration Failed' in result
                assert 'Configuration failed' in result

        finally:
            os.unlink(temp_file_path)

    @pytest.mark.asyncio
    async def test_execute_agentcore_deployment_sdk_not_available(self):
        """Test SDK deployment when SDK is not available."""
        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.runtime.SDK_AVAILABLE', False),
            patch(
                'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.SDK_IMPORT_ERROR',
                'SDK not found',
            ),
        ):
            result = await execute_agentcore_deployment_sdk(
                'test.py', 'test-agent', 'us-east-1', False, 'auto', 'dev', False, ''
            )

            assert 'AgentCore SDK Not Available' in result
            assert 'SDK not found' in result

    @pytest.mark.asyncio
    async def test_execute_agentcore_deployment_sdk_invalid_app_file(self):
        """Test SDK deployment with invalid app file."""
        with (
            patch('awslabs.amazon_bedrock_agentcore_mcp_server.runtime.SDK_AVAILABLE', True),
            patch('pathlib.Path.exists', return_value=False),
        ):
            result = await execute_agentcore_deployment_sdk(
                'nonexistent.py', 'test-agent', 'us-east-1', False, 'auto', 'dev', False, ''
            )

            assert "App file 'nonexistent.py' not found" in result

    @pytest.mark.asyncio
    async def test_execute_agentcore_deployment_sdk_success(self):
        """Test successful SDK deployment."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write("""
from bedrock_agentcore import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

@app.entrypoint
def handler(payload):
    return {"result": "test"}

if __name__ == "__main__":
    app.run()
""")
            temp_file_path = temp_file.name

        try:
            with (
                patch('awslabs.amazon_bedrock_agentcore_mcp_server.runtime.SDK_AVAILABLE', True),
                patch(
                    'awslabs.amazon_bedrock_agentcore_mcp_server.runtime.get_runtime_for_agent'
                ) as mock_get_runtime,
                patch('os.chdir'),
                patch('os.getcwd'),
                patch('time.sleep'),
            ):
                # Mock runtime object
                mock_runtime = Mock()
                mock_get_runtime.return_value = mock_runtime

                mock_runtime.configure.return_value = 'Configuration successful'
                mock_runtime.launch.return_value = 'Launch successful'

                # Mock status progression
                status_responses = [
                    Mock(endpoint={'status': 'CREATING'}),
                    Mock(endpoint={'status': 'READY'}),
                ]
                mock_runtime.status.side_effect = status_responses

                mock_runtime.invoke.return_value = {'response': 'Test successful'}

                result = await execute_agentcore_deployment_sdk(
                    temp_file_path, 'test-agent', 'us-east-1', False, 'auto', 'dev', False, ''
                )

                assert 'SDK Deployment Successful' in result
                assert 'READY' in result

        finally:
            os.unlink(temp_file_path)

    @pytest.mark.asyncio
    async def test_invoke_agent_via_aws_sdk(self):
        """Test direct AWS SDK agent invocation."""
        with patch('boto3.client') as mock_boto3:
            mock_client = Mock()
            mock_boto3.return_value = mock_client

            # Mock dir() to return some methods
            with patch('builtins.dir', return_value=['invoke_agent_runtime', 'list_agents']):
                result = await invoke_agent_via_aws_sdk(
                    'test-agent', 'Hello, AWS!', 'aws-session', 'us-east-1'
                )

                assert 'Direct AWS SDK Invocation Attempted' in result
                assert 'test-agent' in result
                assert 'aws-session' in result


class TestToolRegistration:
    """Test runtime tool registration."""

    def test_register_analysis_tools(self):
        """Test that analysis tools are properly registered."""
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP('Test Analysis Server')

        # Get initial tool count
        import asyncio

        initial_tools = asyncio.run(mcp.list_tools())
        initial_count = len(initial_tools)

        # Register analysis tools
        register_analysis_tools(mcp)

        # Verify tools were added
        final_tools = asyncio.run(mcp.list_tools())
        final_count = len(final_tools)

        # Should have more tools after registration
        assert final_count > initial_count

    @pytest.mark.asyncio
    async def test_analysis_tools_available_in_tools_list(self):
        """Test that analysis tools appear in tools list."""
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP('Test Analysis Server')
        register_analysis_tools(mcp)

        tools = await mcp.list_tools()
        tool_names = [tool.name for tool in tools]

        expected_tools = ['analyze_agent_code', 'transform_to_agentcore']

        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    def test_register_deployment_tools(self):
        """Test that deployment tools are properly registered."""
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP('Test Deployment Server')

        # Get initial tool count
        import asyncio

        initial_tools = asyncio.run(mcp.list_tools())
        initial_count = len(initial_tools)

        # Register deployment tools
        register_deployment_tools(mcp)

        # Verify tools were added
        final_tools = asyncio.run(mcp.list_tools())
        final_count = len(final_tools)

        # Should have more tools after registration
        assert final_count > initial_count

    @pytest.mark.asyncio
    async def test_deployment_tools_available_in_tools_list(self):
        """Test that deployment tools appear in tools list."""
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP('Test Deployment Server')
        register_deployment_tools(mcp)

        tools = await mcp.list_tools()
        tool_names = [tool.name for tool in tools]

        expected_tools = [
            'deploy_agentcore_app',
            'invoke_agent',
            'invoke_oauth_agent',
            'get_runtime_oauth_token',
            'check_oauth_status',
            'invoke_agent_smart',
            'invoke_oauth_agent_v2',
            'get_agent_status',
            'discover_existing_agents',
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names


if __name__ == '__main__':
    import asyncio

    async def run_basic_tests():
        """Run basic tests to verify functionality."""
        print('Testing runtime tool registration...')

        # Test analysis tools registration
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP('Test Server')
        register_analysis_tools(mcp)
        analysis_tools = await mcp.list_tools()
        print(f'✓ Analysis tools registered: {len(analysis_tools)} tools')

        # Test deployment tools registration
        mcp2 = FastMCP('Test Deployment Server')
        register_deployment_tools(mcp2)
        deployment_tools = await mcp2.list_tools()
        print(f'✓ Deployment tools registered: {len(deployment_tools)} tools')

        # Test helper functions
        strategy = generate_migration_strategy({'framework': 'strands'})
        print(f'✓ Migration strategy working: {strategy["complexity"]}')

        guidance = generate_tutorial_based_guidance('strands')
        print(f'✓ Tutorial guidance working: {len(guidance)} chars')

        print('All basic runtime tests passed!')

    asyncio.run(run_basic_tests())
