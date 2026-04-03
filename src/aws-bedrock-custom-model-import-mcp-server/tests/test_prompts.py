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

"""Tests for the prompts."""

import pytest
from awslabs.aws_bedrock_custom_model_import_mcp_server.prompts import Prompts
from unittest.mock import MagicMock


class TestPrompts:
    """Tests for the Prompts class."""

    @pytest.fixture
    def mock_mcp(self):
        """Fixture for mocking FastMCP."""
        mock = MagicMock()
        return mock

    @pytest.fixture
    def prompts(self, mock_mcp):
        """Fixture for creating a Prompts instance with mocked FastMCP."""
        return Prompts(mock_mcp)

    def test_initialization(self, mock_mcp):
        """Test prompt initialization and registration."""
        # Create prompts instance
        Prompts(mock_mcp)

        assert mock_mcp.prompt.call_count == 6

    def test_create_model_import_job(self, prompts):
        """Test create_model_import_job prompt."""
        result = prompts.create_model_import_job()
        assert 'create_model_import_job' in result

    def test_list_model_import_jobs(self, prompts):
        """Test list_model_import_jobs prompt."""
        result = prompts.list_model_import_jobs()
        assert 'list_model_import_jobs' in result

    def test_list_imported_models(self, prompts):
        """Test list_imported_models prompt."""
        result = prompts.list_imported_models()
        assert 'list_imported_models' in result

    def test_get_model_import_job(self, prompts):
        """Test get_model_import_job prompt."""
        result = prompts.get_model_import_job()
        assert 'get_model_import_job' in result

    def test_get_imported_model(self, prompts):
        """Test get_imported_model prompt."""
        result = prompts.get_imported_model()
        assert 'get_imported_model' in result

    def test_delete_imported_model(self, prompts):
        """Test delete_imported_model prompt."""
        result = prompts.delete_imported_model()
        assert 'delete_imported_model' in result
