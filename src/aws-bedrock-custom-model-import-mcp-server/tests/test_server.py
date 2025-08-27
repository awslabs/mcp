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

"""Tests for the server."""

import pytest
from awslabs.aws_bedrock_custom_model_import_mcp_server.server import main
from unittest.mock import MagicMock, patch


class TestServer:
    """Tests for the server module."""

    @pytest.fixture
    def mock_fastmcp(self):
        """Fixture for mocking FastMCP."""
        mock_instance = MagicMock()
        mock_instance.run = MagicMock()
        mock_instance.prompt = MagicMock()
        mock = MagicMock()
        mock.return_value = mock_instance
        with patch('awslabs.aws_bedrock_custom_model_import_mcp_server.server.mcp', mock_instance):
            yield mock_instance

    @pytest.fixture
    def mock_bedrock_client(self):
        """Fixture for mocking BedrockModelImportClient."""
        with patch(
            'awslabs.aws_bedrock_custom_model_import_mcp_server.server.BedrockModelImportClient'
        ) as mock:
            mock_instance = mock.return_value
            yield mock, mock_instance

    @pytest.fixture
    def mock_config(self):
        """Fixture for mocking AppConfig."""
        mock = MagicMock()
        mock.aws_config.region = 'us-west-2'
        mock.aws_config.profile = None
        # Set up logging config with string values instead of MagicMock
        mock.logging_config.level = 'INFO'
        mock.logging_config.format = '{time} | {level} | {message}'
        with patch(
            'awslabs.aws_bedrock_custom_model_import_mcp_server.server.AppConfig'
        ) as config_mock:
            config_mock.from_env.return_value = mock
            yield config_mock, mock

    def test_initialization(self, mock_fastmcp, mock_bedrock_client, mock_config):
        """Test server initialization.

        This test verifies:
        1. Client initialization with correct configuration
        2. Service initialization with correct client
        3. Tool initialization and registration
        4. Prompt registration
        """
        mock_client_class, mock_client = mock_bedrock_client
        config_class, mock_config_instance = mock_config

        # Mock command line arguments
        test_args = ['--allow-write']
        with (
            # Mock command line arguments
            patch('sys.argv', ['server.py'] + test_args),
            # Mock logger to avoid actual logging
            patch('awslabs.aws_bedrock_custom_model_import_mcp_server.server.logger'),
            # Mock services
            patch(
                'awslabs.aws_bedrock_custom_model_import_mcp_server.server.ModelImportService'
            ) as mock_import_service,
            patch(
                'awslabs.aws_bedrock_custom_model_import_mcp_server.server.ImportedModelService'
            ) as mock_imported_service,
            # Mock tools
            patch(
                'awslabs.aws_bedrock_custom_model_import_mcp_server.server.CreateModelImportJob'
            ) as mock_create_job,
            patch(
                'awslabs.aws_bedrock_custom_model_import_mcp_server.server.GetModelImportJob'
            ) as mock_get_job,
            patch(
                'awslabs.aws_bedrock_custom_model_import_mcp_server.server.ListModelImportJobs'
            ) as mock_list_jobs,
            patch(
                'awslabs.aws_bedrock_custom_model_import_mcp_server.server.GetImportedModel'
            ) as mock_get_model,
            patch(
                'awslabs.aws_bedrock_custom_model_import_mcp_server.server.DeleteImportedModel'
            ) as mock_delete_model,
            patch(
                'awslabs.aws_bedrock_custom_model_import_mcp_server.server.ListImportedModels'
            ) as mock_list_models,
            patch(
                'awslabs.aws_bedrock_custom_model_import_mcp_server.server.Prompts'
            ) as mock_prompts,
            patch('awslabs.aws_bedrock_custom_model_import_mcp_server.server.mcp.run'),
        ):
            # Call the main function
            main()

            # Verify client initialization
            mock_client_class.assert_called_once_with(
                mock_config_instance.aws_config.region, mock_config_instance.aws_config.profile
            )

            # Verify service initialization
            mock_import_service.assert_called_once_with(mock_client, mock_config_instance)
            mock_imported_service.assert_called_once_with(mock_client, mock_config_instance)

            # Verify tool initialization
            mock_create_job.assert_called_once()
            mock_get_job.assert_called_once()
            mock_list_jobs.assert_called_once()
            mock_get_model.assert_called_once()
            mock_delete_model.assert_called_once()
            mock_list_models.assert_called_once()

            # Verify prompts initialization
            mock_prompts.assert_called_once_with(mock_fastmcp)

    def test_module_execution(self):
        """Test the module execution when run as __main__."""
        import inspect
        from awslabs.aws_bedrock_custom_model_import_mcp_server import server

        source = inspect.getsource(server)
        assert "if __name__ == '__main__':" in source
        assert 'main()' in source
