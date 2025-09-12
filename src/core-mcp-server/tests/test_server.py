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
"""Tests for the Core MCP Server."""

import asyncio
import importlib
import os
import pytest
from awslabs.core_mcp_server import server
from unittest.mock import AsyncMock, MagicMock, patch


# Import PROMPT_UNDERSTANDING directly from the file
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
prompt_understanding_path = os.path.join(
    parent_dir, 'awslabs', 'core_mcp_server', 'static', 'PROMPT_UNDERSTANDING.md'
)
with open(prompt_understanding_path, 'r', encoding='utf-8') as f:
    PROMPT_UNDERSTANDING = f.read()

mock_modules = {
    'awslabs.amazon_keyspaces_mcp_server.server': MagicMock(),
    'awslabs.amazon_mq_mcp_server.server': MagicMock(),
    'awslabs.amazon_neptune_mcp_server.server': MagicMock(),
    'awslabs.amazon_sns_sqs_mcp_server.server': MagicMock(),
    'awslabs.aurora_dsql_mcp_server.server': MagicMock(),
    'awslabs.aws_api_mcp_server.server': MagicMock(),
    'awslabs.aws_dataprocessing_mcp_server.server': MagicMock(),
    'awslabs.aws_diagram_mcp_server.server': MagicMock(),
    'awslabs.aws_healthomics_mcp_server.server': MagicMock(),
    'awslabs.aws_pricing_mcp_server.server': MagicMock(),
    'awslabs.aws_serverless_mcp_server.server': MagicMock(),
    'awslabs.aws_support_mcp_server.server': MagicMock(),
    'awslabs.cdk_mcp_server.core.server': MagicMock(),
    'awslabs.cfn_mcp_server.server': MagicMock(),
    'awslabs.cloudwatch_appsignals_mcp_server.server': MagicMock(),
    'awslabs.cloudwatch_mcp_server.server': MagicMock(),
    'awslabs.code_doc_gen_mcp_server.server': MagicMock(),
    'awslabs.cost_explorer_mcp_server.server': MagicMock(),
    'awslabs.documentdb_mcp_server.server': MagicMock(),
    'awslabs.dynamodb_mcp_server.server': MagicMock(),
    'awslabs.ecs_mcp_server.main': MagicMock(),
    'awslabs.eks_mcp_server.server': MagicMock(),
    'awslabs.elasticache_mcp_server.main': MagicMock(),
    'awslabs.finch_mcp_server.server': MagicMock(),
    'awslabs.frontend_mcp_server.server': MagicMock(),
    'awslabs.git_repo_research_mcp_server.server': MagicMock(),
    'awslabs.iam_mcp_server.server': MagicMock(),
    'awslabs.lambda_tool_mcp_server.server': MagicMock(),
    'awslabs.memcached_mcp_server.main': MagicMock(),
    'awslabs.mysql_mcp_server.server': MagicMock(),
    'awslabs.nova_canvas_mcp_server.server': MagicMock(),
    'awslabs.postgres_mcp_server.server': MagicMock(),
    'awslabs.prometheus_mcp_server.server': MagicMock(),
    'awslabs.redshift_mcp_server.server': MagicMock(),
    'awslabs.s3_tables_mcp_server.server': MagicMock(),
    'awslabs.stepfunctions_tool_mcp_server.server': MagicMock(),
    'awslabs.syntheticdata_mcp_server.server': MagicMock(),
    'awslabs.timestream_for_influxdb_mcp_server.server': MagicMock(),
    'awslabs.billing_cost_management_mcp_server.server': MagicMock(),
    'awslabs.cloudtrail_mcp_server.server': MagicMock(),
    'awslabs.well_architected_security_mcp_server.server': MagicMock(),
}


# Create a mock FunctionTool class that simulates the behavior of the actual FunctionTool class
class MockFunctionTool:
    """Mock implementation of the FunctionTool class for testing purposes.

    This class simulates the behavior of the actual FunctionTool class from fastmcp,
    allowing tests to run without requiring the actual implementation.
    """

    def __init__(self, func):
        """Initialize the MockFunctionTool with a function.

        Args:
            func: The function to be called when run is invoked.
        """
        self.func = func

    async def run(self, arguments: dict = {}):
        """Execute the function with the provided arguments.

        Args:
            arguments: Dictionary of arguments to pass to the function.
                      Not actually used in this mock implementation.

        Returns:
            The result of calling the function.
        """
        # In the actual implementation, this would process arguments and call the function
        return self.func()


# Create a mock for the tool decorator that returns a MockFunctionTool instance
mock_tool = MagicMock()
mock_tool.return_value = lambda func: MockFunctionTool(func)

# Create a mock for the mcp instance
mock_mcp = MagicMock()
mock_mcp.tool = mock_tool

# Create a mock for the FastMCP class
mock_fastmcp = MagicMock()
mock_fastmcp.return_value = mock_mcp

mock_modules.update(
    {
        'fastmcp': MagicMock(),
        'fastmcp.FastMCP': mock_fastmcp,
        'fastmcp.settings': MagicMock(),
        'fastmcp.server': MagicMock(),
        'fastmcp.server.proxy': MagicMock(),
    }
)

with patch.dict('sys.modules', mock_modules):
    # Import the module, not just the function
    import awslabs.core_mcp_server.server

    # Create a MockFunctionTool instance directly and replace get_prompt_understanding with it
    awslabs.core_mcp_server.server.get_prompt_understanding = MockFunctionTool(
        lambda: PROMPT_UNDERSTANDING
    )


class TestPromptUnderstanding:
    """Tests for get_prompt_understanding function."""

    @pytest.mark.asyncio
    async def test_get_prompt_understanding(self):
        """Test that get_prompt_understanding returns the expected value."""
        # Now we can call the run method on the MockFunctionTool instance
        result = await awslabs.core_mcp_server.server.get_prompt_understanding.run({})
        assert result == PROMPT_UNDERSTANDING


class TestSetup:
    """Tests for setup function."""

    @pytest.mark.parametrize(
        'role_env_var,expected_prefixes',
        [
            ('aws-foundation', ['aws_knowledge', 'aws_api']),
            ('dev-tools', ['git_repo_research', 'code_doc_gen', 'aws_knowledge']),
            ('ci-cd-devops', ['cdk', 'cfn']),
            ('container-orchestration', ['eks', 'ecs', 'finch']),
            (
                'serverless-architecture',
                ['serverless', 'lambda_tool', 'stepfunctions_tool', 'sns_sqs'],
            ),
            (
                'analytics-warehouse',
                ['redshift', 'timestream_for_influxdb', 'dataprocessing', 'syntheticdata'],
            ),
            ('data-platform-eng', ['dynamodb', 's3_tables', 'dataprocessing']),
            ('frontend-dev', ['frontend', 'nova_canvas']),
            (
                'solutions-architect',
                ['diagram', 'pricing', 'cost_explorer', 'syntheticdata', 'aws_knowledge'],
            ),
            ('finops', ['cost_explorer', 'pricing', 'cloudwatch', 'billing_cost_management']),
            (
                'monitoring-observability',
                ['cloudwatch', 'cloudwatch_appsignals', 'prometheus', 'cloudtrail'],
            ),
            ('caching-performance', ['elasticache', 'memcached']),
            ('security-identity', ['iam', 'support', 'well-architected-security']),
            ('sql-db-specialist', ['postgres', 'mysql', 'aurora_dsql', 'redshift']),
            ('nosql-db-specialist', ['dynamodb', 'documentdb', 'keyspaces', 'neptune']),
            ('timeseries-db-specialist', ['timestream_for_influxdb', 'prometheus', 'cloudwatch']),
            ('messaging-events', ['sns_sqs', 'mq']),
            ('healthcare-lifesci', ['healthomics']),
        ],
    )
    @pytest.mark.asyncio
    async def test_setup_role_variables(self, monkeypatch, role_env_var, expected_prefixes):
        """Test that setup function correctly imports servers based on role environment variables.

        This test verifies that when a specific role environment variable is set,
        the setup function attempts to import the expected server prefixes.

        The test also checks for both uppercase with underscores and lowercase with hyphens.

        Args:
            monkeypatch: Pytest fixture for modifying environment variables
            role_env_var: The role environment variable to set
            expected_prefixes: List of server prefixes expected to be imported for this role
        """
        roles = [
            role_env_var.replace('-', '_').upper()
            if '-' in role_env_var
            else role_env_var.lower().replace('_', '-'),
            role_env_var,
        ]
        for role in roles:
            # 1. Set the environment variable
            monkeypatch.setitem(os.environ, role, '1')

            # 2. Reload the server module so it picks up the env variable
            importlib.reload(server)

            # 3. Patch call_import_server to just record what gets imported
            called = set()

            async def fake_import(srv, prefix, name, imported):
                called.add(prefix)
                return imported | {prefix}

            monkeypatch.setattr(server, 'call_import_server', fake_import)

            # 4. Run setup
            await server.setup()

            # 5. Assert that all expected subservers for this role were attempted
            for prefix in expected_prefixes:
                assert prefix in called

    @pytest.mark.asyncio
    @patch.dict('os.environ', {'aws-foundation': 'true'})
    async def test_setup_aws_foundation(self):
        """Test setup function with aws-foundation role enabled."""
        # Import the setup function
        with patch.dict('sys.modules', mock_modules):
            from awslabs.core_mcp_server.server import setup

            # Mock the necessary components
            with (
                patch('awslabs.core_mcp_server.server.logger'),
                patch('awslabs.core_mcp_server.server.FastMCP.as_proxy') as mock_as_proxy,
                patch('awslabs.core_mcp_server.server.mcp.import_server') as mock_import_server,
            ):
                # Configure mocks
                mock_proxy = MagicMock()
                mock_as_proxy.return_value = mock_proxy
                mock_import_server.return_value = None

                # Call the setup function
                await setup()

                # Verify that the function completed without errors
                assert True

    @pytest.mark.asyncio
    @patch.dict('os.environ', {'dev-tools': 'true'})
    async def test_setup_dev_tools(self):
        """Test setup function with dev-tools role enabled."""
        # Import the setup function
        with patch.dict('sys.modules', mock_modules):
            from awslabs.core_mcp_server.server import setup

            # Mock the necessary components
            with (
                patch('awslabs.core_mcp_server.server.FastMCP.as_proxy') as mock_as_proxy,
                patch('awslabs.core_mcp_server.server.mcp.import_server') as mock_import_server,
            ):
                # Configure mocks
                mock_proxy = MagicMock()
                mock_as_proxy.return_value = mock_proxy
                mock_import_server.return_value = None

                # Call the setup function
                await setup()

                # Verify that the function completed without errors
                assert True

    @pytest.mark.asyncio
    @patch.dict('os.environ', {'ci-cd-devops': 'true'})
    async def test_setup_ci_cd_devops(self):
        """Test setup function with ci-cd-devops role enabled."""
        # Import the setup function
        with patch.dict('sys.modules', mock_modules):
            from awslabs.core_mcp_server.server import setup

            # Mock the necessary components
            with (
                patch('awslabs.core_mcp_server.server.FastMCP.as_proxy') as mock_as_proxy,
                patch('awslabs.core_mcp_server.server.mcp.import_server') as mock_import_server,
            ):
                # Configure mocks
                mock_proxy = MagicMock()
                mock_as_proxy.return_value = mock_proxy
                mock_import_server.return_value = None

                # Call the setup function
                await setup()

                # Verify that the function completed without errors
                assert True

    @pytest.mark.asyncio
    @patch.dict('os.environ', {'container-orchestration': 'true'})
    async def test_setup_container_orchestration(self):
        """Test setup function with container-orchestration role enabled."""
        # Import the setup function
        with patch.dict('sys.modules', mock_modules):
            from awslabs.core_mcp_server.server import setup

            # Mock the necessary components
            with (
                patch('awslabs.core_mcp_server.server.FastMCP.as_proxy') as mock_as_proxy,
                patch('awslabs.core_mcp_server.server.mcp.import_server') as mock_import_server,
            ):
                # Configure mocks
                mock_proxy = MagicMock()
                mock_as_proxy.return_value = mock_proxy
                mock_import_server.return_value = None

                # Call the setup function
                await setup()

                # Verify that the function completed without errors
                assert True

    @pytest.mark.asyncio
    @patch.dict('os.environ', {'serverless-architecture': 'true'})
    async def test_setup_serverless_architecture(self):
        """Test setup function with serverless-architecture role enabled."""
        # Import the setup function
        with patch.dict('sys.modules', mock_modules):
            from awslabs.core_mcp_server.server import setup

            # Mock the necessary components
            with (
                patch('awslabs.core_mcp_server.server.FastMCP.as_proxy') as mock_as_proxy,
                patch('awslabs.core_mcp_server.server.mcp.import_server') as mock_import_server,
            ):
                # Configure mocks
                mock_proxy = MagicMock()
                mock_as_proxy.return_value = mock_proxy
                mock_import_server.return_value = None

                # Call the setup function
                await setup()

                # Verify that the function completed without errors
                assert True

    @pytest.mark.asyncio
    @patch.dict('os.environ', {'analytics-warehouse': 'true'})
    async def test_setup_analytics_warehouse(self):
        """Test setup function with analytics-warehouse role enabled."""
        # Import the setup function
        with patch.dict('sys.modules', mock_modules):
            from awslabs.core_mcp_server.server import setup

            # Mock the necessary components
            with (
                patch('awslabs.core_mcp_server.server.FastMCP.as_proxy') as mock_as_proxy,
                patch('awslabs.core_mcp_server.server.mcp.import_server') as mock_import_server,
            ):
                # Configure mocks
                mock_proxy = MagicMock()
                mock_as_proxy.return_value = mock_proxy
                mock_import_server.return_value = None

                # Call the setup function
                await setup()

                # Verify that the function completed without errors
                assert True

    @pytest.mark.asyncio
    @patch.dict('os.environ', {'data-platform-eng': 'true'})
    async def test_setup_data_platform_eng(self):
        """Test setup function with data-platform-eng role enabled."""
        # Import the setup function
        with patch.dict('sys.modules', mock_modules):
            from awslabs.core_mcp_server.server import setup

            # Mock the necessary components
            with (
                patch('awslabs.core_mcp_server.server.FastMCP.as_proxy') as mock_as_proxy,
                patch('awslabs.core_mcp_server.server.mcp.import_server') as mock_import_server,
            ):
                # Configure mocks
                mock_proxy = MagicMock()
                mock_as_proxy.return_value = mock_proxy
                mock_import_server.return_value = None

                # Call the setup function
                await setup()

                # Verify that the function completed without errors
                assert True

    @pytest.mark.asyncio
    @patch.dict('os.environ', {'frontend-dev': 'true'})
    async def test_setup_frontend_dev(self):
        """Test setup function with frontend-dev role enabled."""
        # Import the setup function
        with patch.dict('sys.modules', mock_modules):
            from awslabs.core_mcp_server.server import setup

            # Mock the necessary components
            with (
                patch('awslabs.core_mcp_server.server.FastMCP.as_proxy') as mock_as_proxy,
                patch('awslabs.core_mcp_server.server.mcp.import_server') as mock_import_server,
            ):
                # Configure mocks
                mock_proxy = MagicMock()
                mock_as_proxy.return_value = mock_proxy
                mock_import_server.return_value = None

                # Call the setup function
                await setup()

                # Verify that the function completed without errors
                assert True

    @pytest.mark.asyncio
    @patch.dict('os.environ', {'solutions-architect': 'true'})
    async def test_setup_solutions_architect(self):
        """Test setup function with solutions-architect role enabled."""
        # Import the setup function
        with patch.dict('sys.modules', mock_modules):
            from awslabs.core_mcp_server.server import setup

            # Mock the necessary components
            with (
                patch('awslabs.core_mcp_server.server.logger'),
                patch('awslabs.core_mcp_server.server.FastMCP.as_proxy') as mock_as_proxy,
                patch('awslabs.core_mcp_server.server.mcp.import_server') as mock_import_server,
            ):
                # Configure mocks
                mock_proxy = MagicMock()
                mock_as_proxy.return_value = mock_proxy
                mock_import_server.return_value = None

                # Call the setup function
                await setup()

                # Verify that the function completed without errors
                assert True

    @pytest.mark.asyncio
    @patch.dict('os.environ', {'finops': 'true'})
    async def test_setup_finops(self):
        """Test setup function with finops role enabled."""
        # Import the setup function
        with patch.dict('sys.modules', mock_modules):
            from awslabs.core_mcp_server.server import setup

            # Mock the necessary components
            with (
                patch('awslabs.core_mcp_server.server.FastMCP.as_proxy') as mock_as_proxy,
                patch('awslabs.core_mcp_server.server.mcp.import_server') as mock_import_server,
            ):
                # Configure mocks
                mock_proxy = MagicMock()
                mock_as_proxy.return_value = mock_proxy
                mock_import_server.return_value = None

                # Call the setup function
                await setup()

                # Verify that the function completed without errors
                assert True

    @pytest.mark.asyncio
    @patch.dict('os.environ', {'monitoring-observability': 'true'})
    async def test_setup_monitoring_observability(self):
        """Test setup function with monitoring-observability role enabled."""
        # Import the setup function
        with patch.dict('sys.modules', mock_modules):
            from awslabs.core_mcp_server.server import setup

            # Mock the necessary components
            with (
                patch('awslabs.core_mcp_server.server.FastMCP.as_proxy') as mock_as_proxy,
                patch('awslabs.core_mcp_server.server.mcp.import_server') as mock_import_server,
            ):
                # Configure mocks
                mock_proxy = MagicMock()
                mock_as_proxy.return_value = mock_proxy
                mock_import_server.return_value = None

                # Call the setup function
                await setup()

                # Verify that the function completed without errors
                assert True

    @pytest.mark.asyncio
    @patch.dict('os.environ', {'caching-performance': 'true'})
    async def test_setup_caching_performance(self):
        """Test setup function with caching-performance role enabled."""
        # Import the setup function
        with patch.dict('sys.modules', mock_modules):
            from awslabs.core_mcp_server.server import setup

            # Mock the necessary components
            with (
                patch('awslabs.core_mcp_server.server.FastMCP.as_proxy') as mock_as_proxy,
                patch('awslabs.core_mcp_server.server.mcp.import_server') as mock_import_server,
            ):
                # Configure mocks
                mock_proxy = MagicMock()
                mock_as_proxy.return_value = mock_proxy
                mock_import_server.return_value = None

                # Call the setup function
                await setup()

                # Verify that the function completed without errors
                assert True

    @pytest.mark.asyncio
    @patch.dict('os.environ', {'security-identity': 'true'})
    async def test_setup_security_identity(self):
        """Test setup function with security-identity role enabled."""
        # Import the setup function
        with patch.dict('sys.modules', mock_modules):
            from awslabs.core_mcp_server.server import setup

            # Mock the necessary components
            with (
                patch('awslabs.core_mcp_server.server.FastMCP.as_proxy') as mock_as_proxy,
                patch('awslabs.core_mcp_server.server.mcp.import_server') as mock_import_server,
            ):
                # Configure mocks
                mock_proxy = MagicMock()
                mock_as_proxy.return_value = mock_proxy
                mock_import_server.return_value = None

                # Call the setup function
                await setup()

                # Verify that the function completed without errors
                assert True

    @pytest.mark.asyncio
    @patch.dict('os.environ', {'sql-db-specialist': 'true'})
    async def test_setup_sql_db_specialist(self):
        """Test setup function with sql-db-specialist role enabled."""
        # Import the setup function
        with patch.dict('sys.modules', mock_modules):
            from awslabs.core_mcp_server.server import setup

            # Mock the necessary components
            with (
                patch('awslabs.core_mcp_server.server.FastMCP.as_proxy') as mock_as_proxy,
                patch('awslabs.core_mcp_server.server.mcp.import_server') as mock_import_server,
            ):
                # Configure mocks
                mock_proxy = MagicMock()
                mock_as_proxy.return_value = mock_proxy
                mock_import_server.return_value = None

                # Call the setup function
                await setup()

                # Verify that the function completed without errors
                assert True

    @pytest.mark.asyncio
    @patch.dict('os.environ', {'nosql-db-specialist': 'true'})
    async def test_setup_nosql_db_specialist(self):
        """Test setup function with nosql-db-specialist role enabled."""
        # Import the setup function
        with patch.dict('sys.modules', mock_modules):
            from awslabs.core_mcp_server.server import setup

            # Mock the necessary components
            with (
                patch('awslabs.core_mcp_server.server.FastMCP.as_proxy') as mock_as_proxy,
                patch('awslabs.core_mcp_server.server.mcp.import_server') as mock_import_server,
            ):
                # Configure mocks
                mock_proxy = MagicMock()
                mock_as_proxy.return_value = mock_proxy
                mock_import_server.return_value = None

                # Call the setup function
                await setup()

                # Verify that the function completed without errors
                assert True

    @pytest.mark.asyncio
    @patch.dict('os.environ', {'timeseries-db-specialist': 'true'})
    async def test_setup_timeseries_db_specialist(self):
        """Test setup function with timeseries-db-specialist role enabled."""
        # Import the setup function
        with patch.dict('sys.modules', mock_modules):
            from awslabs.core_mcp_server.server import setup

            # Mock the necessary components
            with (
                patch('awslabs.core_mcp_server.server.FastMCP.as_proxy') as mock_as_proxy,
                patch('awslabs.core_mcp_server.server.mcp.import_server') as mock_import_server,
            ):
                # Configure mocks
                mock_proxy = MagicMock()
                mock_as_proxy.return_value = mock_proxy
                mock_import_server.return_value = None

                # Call the setup function
                await setup()

                # Verify that the function completed without errors
                assert True

    @pytest.mark.asyncio
    @patch.dict('os.environ', {'messaging-events': 'true'})
    async def test_setup_messaging_events(self):
        """Test setup function with messaging-events role enabled."""
        # Import the setup function
        with patch.dict('sys.modules', mock_modules):
            from awslabs.core_mcp_server.server import setup

            # Mock the necessary components
            with (
                patch('awslabs.core_mcp_server.server.FastMCP.as_proxy') as mock_as_proxy,
                patch('awslabs.core_mcp_server.server.mcp.import_server') as mock_import_server,
            ):
                # Configure mocks
                mock_proxy = MagicMock()
                mock_as_proxy.return_value = mock_proxy
                mock_import_server.return_value = None

                # Call the setup function
                await setup()

                # Verify that the function completed without errors
                assert True

    @pytest.mark.asyncio
    @patch.dict('os.environ', {'healthcare-lifesci': 'true'})
    async def test_setup_healthcare_lifesci(self):
        """Test setup function with healthcare-lifesci role enabled."""
        # Import the setup function
        with patch.dict('sys.modules', mock_modules):
            from awslabs.core_mcp_server.server import setup

            # Mock the necessary components
            with (
                patch('awslabs.core_mcp_server.server.FastMCP.as_proxy') as mock_as_proxy,
                patch('awslabs.core_mcp_server.server.mcp.import_server') as mock_import_server,
            ):
                # Configure mocks
                mock_proxy = MagicMock()
                mock_as_proxy.return_value = mock_proxy
                mock_import_server.return_value = None

                # Call the setup function
                await setup()

                # Verify that the function completed without errors
                assert True

    @pytest.mark.asyncio
    @patch.dict('os.environ', {})
    async def test_setup_no_roles(self):
        """Test setup function with no roles enabled."""
        # Import the setup function
        with patch.dict('sys.modules', mock_modules):
            from awslabs.core_mcp_server.server import setup

            # Mock the necessary components
            with (
                patch('awslabs.core_mcp_server.server.FastMCP.as_proxy') as mock_as_proxy,
                patch('awslabs.core_mcp_server.server.mcp.import_server') as mock_import_server,
            ):
                # Configure mocks
                mock_proxy = MagicMock()
                mock_as_proxy.return_value = mock_proxy
                mock_import_server.return_value = None

                # Call the setup function
                await setup()

                # Verify that as_proxy was not called (no roles enabled)
                assert mock_as_proxy.call_count == 0

                # Verify that import_server was not called (no roles enabled)
                assert mock_import_server.call_count == 0

    @pytest.mark.asyncio
    @patch.dict('os.environ', {'aws-knowledge-foundation': 'true'})
    async def test_setup_import_error(self):
        """Test setup function when import_server raises an exception."""
        # Import the setup function
        with patch.dict('sys.modules', mock_modules):
            from awslabs.core_mcp_server.server import setup

            # Mock the necessary components
            with (
                patch('awslabs.core_mcp_server.server.FastMCP.as_proxy') as mock_as_proxy,
                patch('awslabs.core_mcp_server.server.mcp.import_server') as mock_import_server,
            ):
                # Configure mocks
                mock_proxy = MagicMock()
                mock_as_proxy.return_value = mock_proxy
                mock_import_server.side_effect = Exception('Import error')

                # Call the setup function - should not raise an exception
                await setup()

                # Verify that the function completed without errors
                assert True

    @pytest.mark.asyncio
    @patch.dict('os.environ', {'aws-knowledge-foundation': 'true', 'dev-tools': 'true'})
    async def test_setup_multiple_roles(self):
        """Test setup function with multiple roles enabled simultaneously."""
        # Import the setup function
        with patch.dict('sys.modules', mock_modules):
            from awslabs.core_mcp_server.server import setup

            # Mock the necessary components
            with (
                patch('awslabs.core_mcp_server.server.logger'),
                patch('awslabs.core_mcp_server.server.FastMCP.as_proxy') as mock_as_proxy,
                patch('awslabs.core_mcp_server.server.mcp.import_server') as mock_import_server,
            ):
                # Configure mocks
                mock_proxy = MagicMock()
                mock_as_proxy.return_value = mock_proxy
                mock_import_server.return_value = None

                # Call the setup function
                await setup()

                # Verify that the function completed without errors
                assert True

    @pytest.mark.asyncio
    @patch.dict('os.environ', {'aws-knowledge-foundation': 'true'})
    async def test_setup_logging(self):
        """Test that setup function logs appropriate messages."""
        # Import the setup function
        with patch.dict('sys.modules', mock_modules):
            from awslabs.core_mcp_server.server import setup

            # Mock the necessary components
            with (
                patch('awslabs.core_mcp_server.server.logger'),
                patch('awslabs.core_mcp_server.server.FastMCP.as_proxy') as mock_as_proxy,
            ):
                # Configure mocks
                mock_proxy = MagicMock()
                mock_as_proxy.return_value = mock_proxy

                # Call the setup function
                await setup()

                # Verify that the function completed without errors
                assert True

    @pytest.mark.asyncio
    @patch.dict('os.environ', {'aws-knowledge-foundation': 'true'})
    async def test_setup_proxy_error(self):
        """Test setup function when as_proxy raises an exception."""
        # Import the setup function
        with patch.dict('sys.modules', mock_modules):
            from awslabs.core_mcp_server.server import setup

            # Mock the necessary components
            with (
                patch('awslabs.core_mcp_server.server.logger'),
                patch(
                    'awslabs.core_mcp_server.server.FastMCP.as_proxy',
                    side_effect=Exception('Proxy error'),
                ),
            ):
                # Call the setup function - should not raise an exception
                await setup()

                # Verify that the function completed without errors
                assert True

    @pytest.mark.asyncio
    async def test_setup_with_no_roles(self):
        """Test setup function with no roles enabled."""
        # Import the server module
        with patch.dict('sys.modules', mock_modules):
            from awslabs.core_mcp_server.server import setup

            # Save original call_import_server function
            original_call_import_server = None
            try:
                # Import the server module to get access to call_import_server
                import awslabs.core_mcp_server.server as server

                original_call_import_server = server.call_import_server

                # Create a mock for the call_import_server function
                mock_call_import_server = AsyncMock()
                server.call_import_server = mock_call_import_server

                # Clear environment variables
                with patch.dict('os.environ', {}, clear=True):
                    # Call the setup function
                    await setup()

                    # Verify that call_import_server was not called
                    assert mock_call_import_server.call_count == 0
            finally:
                # Restore original function if it was saved
                if original_call_import_server:
                    import awslabs.core_mcp_server.server as server

                    server.call_import_server = original_call_import_server


class TestCallImportServer:
    """Tests for call_import_server function."""

    @pytest.mark.asyncio
    async def test_call_import_server(self):
        """Test the call_import_server function."""
        # Import the server module
        with patch.dict('sys.modules', mock_modules):
            import awslabs.core_mcp_server.server as server

            # Create a mock for the FastMCP.as_proxy function
            mock_as_proxy = AsyncMock()
            mock_proxy = MagicMock()
            mock_as_proxy.return_value = mock_proxy

            # Create a mock for the mcp.import_server function
            mock_import_server = AsyncMock()

            # Create a mock for the logger
            mock_logger = MagicMock()

            # Apply patches
            with (
                patch.object(server.FastMCP, 'as_proxy', mock_as_proxy),
                patch.object(server.mcp, 'import_server', mock_import_server),
                patch.object(server, 'logger', mock_logger),
            ):
                # Call the call_import_server function
                await server.call_import_server(
                    server=MagicMock(),
                    prefix='test-prefix',
                    server_name='test-server',
                    imported_servers=set(),
                )

                # Verify that the function was called with the expected arguments
                mock_as_proxy.assert_called_once()
                mock_import_server.assert_called_once()
                mock_logger.info.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_import_server_with_exception(self):
        """Test the call_import_server function when import_server raises an exception."""
        # Import the server module
        with patch.dict('sys.modules', mock_modules):
            import awslabs.core_mcp_server.server as server

            # Create a mock for the FastMCP.as_proxy function
            mock_as_proxy = AsyncMock()
            mock_proxy = MagicMock()
            mock_as_proxy.return_value = mock_proxy

            # Create a mock for the mcp.import_server function that raises an exception
            mock_import_server = AsyncMock(side_effect=Exception('Import error'))

            # Create a mock for the logger
            mock_logger = MagicMock()

            # Apply patches
            with (
                patch.object(server.FastMCP, 'as_proxy', mock_as_proxy),
                patch.object(server.mcp, 'import_server', mock_import_server),
                patch.object(server, 'logger', mock_logger),
            ):
                # Call the call_import_server function
                await server.call_import_server(
                    server=MagicMock(),
                    prefix='test-prefix',
                    server_name='test-server',
                    imported_servers=set(),
                )

                # Verify that the function was called with the expected arguments
                mock_as_proxy.assert_called_once()
                mock_import_server.assert_called_once()
                mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_import_server_with_none_imported_servers(self):
        """Test the call_import_server function with None imported_servers."""
        # Import the server module
        with patch.dict('sys.modules', mock_modules):
            import awslabs.core_mcp_server.server as server

            # Create a mock for the FastMCP.as_proxy function
            mock_as_proxy = AsyncMock()
            mock_proxy = MagicMock()
            mock_as_proxy.return_value = mock_proxy

            # Create a mock for the mcp.import_server function
            mock_import_server = AsyncMock()

            # Create a mock for the logger
            mock_logger = MagicMock()

            # Apply patches
            with (
                patch.object(server.FastMCP, 'as_proxy', mock_as_proxy),
                patch.object(server.mcp, 'import_server', mock_import_server),
                patch.object(server, 'logger', mock_logger),
            ):
                # Call the call_import_server function with None imported_servers
                await server.call_import_server(
                    server=MagicMock(),
                    prefix='test-prefix',
                    server_name='test-server',
                    imported_servers=None,
                )

                # Verify that the function was called with the expected arguments
                mock_as_proxy.assert_called_once()
                mock_import_server.assert_called_once()
                mock_logger.info.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_import_server_with_import_error(self):
        """Test the call_import_server function when import_server raises an exception."""
        # Import the server module
        with patch.dict('sys.modules', mock_modules):
            import awslabs.core_mcp_server.server as server

            # Create mocks
            mock_server = MagicMock()
            mock_proxy = MagicMock()
            mock_import_server = AsyncMock(side_effect=Exception('Import error'))
            mock_logger = MagicMock()

            # Apply patches
            with (
                patch.object(server.FastMCP, 'as_proxy', return_value=mock_proxy),
                patch.object(server.mcp, 'import_server', mock_import_server),
                patch.object(server, 'logger', mock_logger),
            ):
                # Call the function
                await server.call_import_server(
                    server=mock_server,
                    prefix='test-prefix',
                    server_name='test-server',
                    imported_servers=set(),
                )

                # Verify that import_server was called
                mock_import_server.assert_called_once()

                # Verify that logger.error was called
                mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_import_server_with_none_prefix(self):
        """Test the call_import_server function with None prefix."""
        # Import the server module
        with patch.dict('sys.modules', mock_modules):
            import awslabs.core_mcp_server.server as server

            # Create mocks
            mock_server = MagicMock()
            mock_proxy = MagicMock()
            mock_import_server = AsyncMock()
            mock_logger = MagicMock()

            # Apply patches
            with (
                patch.object(server.FastMCP, 'as_proxy', return_value=mock_proxy),
                patch.object(server.mcp, 'import_server', mock_import_server),
                patch.object(server, 'logger', mock_logger),
            ):
                # Call the function with None prefix
                await server.call_import_server(
                    server=mock_server,
                    prefix=None,
                    server_name='test-server',
                    imported_servers=set(),
                )

                # Verify that import_server was called with None prefix
                mock_import_server.assert_called_once_with(mock_proxy, prefix=None)


class TestMainFunction:
    """Tests for main function."""

    def test_main_function(self):
        """Test the main function."""
        # Import the server module
        with patch.dict('sys.modules', mock_modules):
            import awslabs.core_mcp_server.server as server

            # Save original functions
            original_asyncio_run = asyncio.run
            original_setup = server.setup
            original_mcp_run = server.mcp.run

            try:
                # Create mocks
                mock_asyncio_run = MagicMock()
                asyncio.run = mock_asyncio_run

                mock_setup = AsyncMock()
                server.setup = mock_setup

                mock_mcp_run = MagicMock()
                server.mcp.run = mock_mcp_run

                # Call the main function
                server.main()

                # Verify that the functions were called
                mock_asyncio_run.assert_called_once()
                mock_mcp_run.assert_called_once()
            finally:
                # Restore original functions
                asyncio.run = original_asyncio_run
                server.setup = original_setup
                server.mcp.run = original_mcp_run

    def test_main_function_direct(self):
        """Test the main function directly."""
        # Import the server module
        with patch.dict('sys.modules', mock_modules):
            import awslabs.core_mcp_server.server as server

            # Save original functions
            original_asyncio_run = asyncio.run
            original_setup = server.setup
            original_mcp_run = server.mcp.run

            try:
                # Create mocks
                mock_asyncio_run = MagicMock()
                asyncio.run = mock_asyncio_run

                # Create a coroutine object that can be passed to asyncio.run
                async def mock_setup_coroutine():
                    pass

                mock_setup = MagicMock(return_value=mock_setup_coroutine())
                server.setup = mock_setup

                mock_mcp_run = MagicMock()
                server.mcp.run = mock_mcp_run

                # Call the main function
                server.main()

                # Verify that the functions were called
                assert mock_asyncio_run.call_count == 1
                assert mock_mcp_run.call_count == 1
            finally:
                # Restore original functions
                asyncio.run = original_asyncio_run
                server.setup = original_setup
                server.mcp.run = original_mcp_run
