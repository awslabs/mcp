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

"""Test module for package initialization."""

import awslabs.amazon_bedrock_agentcore_mcp_server as server_module


class TestPackageInitialization:
    """Test package initialization and basic imports."""

    def test_version_defined(self):
        """Test that the version is properly defined."""
        assert hasattr(server_module, '__version__')
        assert server_module.__version__ == '0.1.0'

    def test_package_imports(self):
        """Test that the package can be imported without errors."""
        assert server_module is not None

    def test_module_structure(self):
        """Test that expected modules are available."""
        # Test that we can import the main modules
        from awslabs.amazon_bedrock_agentcore_mcp_server import (
            gateway,
            identity,
            memory,
            models,
            runtime,
            server,
            utils,
        )

        # Verify modules are not None
        assert server is not None
        assert utils is not None
        assert models is not None
        assert runtime is not None
        assert gateway is not None
        assert identity is not None
        assert memory is not None

    def test_constants_available(self):
        """Test that important constants are accessible."""
        from awslabs.amazon_bedrock_agentcore_mcp_server import consts

        assert consts is not None
        # Test that we can import specific constants
        assert hasattr(consts, 'DEFAULT_AWS_REGION')
        assert consts.DEFAULT_AWS_REGION == 'us-east-1'

    def test_pydantic_models_available(self):
        """Test that Pydantic models can be imported."""
        from awslabs.amazon_bedrock_agentcore_mcp_server.models import (
            AgentConfig,
        )

        # Should be able to create instances
        agent_config = AgentConfig(name='test')
        assert agent_config.name == 'test'

    def test_server_importable(self):
        """Test that the main server can be imported."""
        from awslabs.amazon_bedrock_agentcore_mcp_server.server import mcp

        assert mcp is not None
        assert hasattr(mcp, 'name')
        assert 'AgentCore MCP Server' in mcp.name


class TestModuleAvailability:
    """Test that all modules are properly available."""

    def test_utils_functions_available(self):
        """Test that utility functions are accessible."""
        from awslabs.amazon_bedrock_agentcore_mcp_server.utils import (
            SDK_AVAILABLE,
            get_user_working_directory,
            resolve_app_file_path,
        )

        # These should be importable without errors
        assert isinstance(SDK_AVAILABLE, bool)
        assert callable(resolve_app_file_path)
        assert callable(get_user_working_directory)

    def test_runtime_functions_available(self):
        """Test that runtime functions are accessible."""
        from awslabs.amazon_bedrock_agentcore_mcp_server.runtime import (
            analyze_code_patterns,
            register_analysis_tools,
            register_deployment_tools,
        )

        # These should be importable without errors
        assert callable(register_analysis_tools)
        assert callable(register_deployment_tools)
        assert callable(analyze_code_patterns)

    def test_all_register_functions_available(self):
        """Test that all module registration functions exist."""
        from awslabs.amazon_bedrock_agentcore_mcp_server.gateway import register_gateway_tools
        from awslabs.amazon_bedrock_agentcore_mcp_server.identity import (
            register_identity_tools,
            register_oauth_tools,
        )
        from awslabs.amazon_bedrock_agentcore_mcp_server.memory import register_memory_tools
        from awslabs.amazon_bedrock_agentcore_mcp_server.utils import (
            register_discovery_tools,
            register_environment_tools,
        )

        # All should be callable
        register_functions = [
            register_oauth_tools,
            register_environment_tools,
            register_discovery_tools,
            register_gateway_tools,
            register_identity_tools,
            register_memory_tools,
        ]

        for func in register_functions:
            assert callable(func)


if __name__ == '__main__':
    # Run basic initialization tests
    print('Testing package initialization...')

    # Test version
    print(f'✓ Package version: {server_module.__version__}')

    # Test basic imports
    print('✓ Server module imported')

    # Test server instance
    from awslabs.amazon_bedrock_agentcore_mcp_server.server import mcp

    print(f'✓ Server instance: {mcp.name}')

    print('All initialization tests passed!')
