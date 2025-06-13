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

"""Tests for the BEDROCK_KB_FORCE_OVERRIDE environment variable configuration."""

import importlib
import os
import pytest
from unittest.mock import patch


class TestBedrockKbForceOverrideConfig:
    """Tests for the BEDROCK_KB_FORCE_OVERRIDE environment variable configuration."""

    def setup_method(self):
        """Clean up environment variables before each test."""
        if 'BEDROCK_KB_ID' in os.environ:
            del os.environ['BEDROCK_KB_ID']
        if 'BEDROCK_KB_FORCE_OVERRIDE' in os.environ:
            del os.environ['BEDROCK_KB_FORCE_OVERRIDE']

    def teardown_method(self):
        """Clean up environment variables after each test."""
        if 'BEDROCK_KB_ID' in os.environ:
            del os.environ['BEDROCK_KB_ID']
        if 'BEDROCK_KB_FORCE_OVERRIDE' in os.environ:
            del os.environ['BEDROCK_KB_FORCE_OVERRIDE']

    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.get_bedrock_agent_runtime_client')
    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.get_bedrock_agent_client')
    def test_bedrock_kb_force_override_default_false(self, mock_agent_client, mock_runtime_client):
        """Test that the BEDROCK_KB_FORCE_OVERRIDE is False by default when no env var is set."""
        # Force reload the module to reset the global variables
        import awslabs.bedrock_kb_retrieval_mcp_server.server
        importlib.reload(awslabs.bedrock_kb_retrieval_mcp_server.server)

        # Verify that the default value is False when the env var is not set
        assert awslabs.bedrock_kb_retrieval_mcp_server.server.kb_force_override is False

    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.get_bedrock_agent_runtime_client')
    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.get_bedrock_agent_client')
    def test_bedrock_kb_force_override_enabled_with_true(self, mock_agent_client, mock_runtime_client):
        """Test that the BEDROCK_KB_FORCE_OVERRIDE is enabled when set to 'true'."""
        # Set both environment variables
        os.environ['BEDROCK_KB_ID'] = 'EXAMPLEKBID'
        os.environ['BEDROCK_KB_FORCE_OVERRIDE'] = 'true'

        # Force reload the module to pick up the new environment variables
        import awslabs.bedrock_kb_retrieval_mcp_server.server
        importlib.reload(awslabs.bedrock_kb_retrieval_mcp_server.server)

        # Verify that the force override is enabled
        assert awslabs.bedrock_kb_retrieval_mcp_server.server.kb_force_override is True

    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.get_bedrock_agent_runtime_client')
    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.get_bedrock_agent_client')
    def test_bedrock_kb_force_override_various_true_values(self, mock_agent_client, mock_runtime_client):
        """Test that BEDROCK_KB_FORCE_OVERRIDE accepts various true values."""
        true_values = ['true', '1', 'yes', 'on', 'TRUE', 'True', 'YES', 'ON']
        
        for true_value in true_values:
            # Set the environment variables
            os.environ['BEDROCK_KB_ID'] = 'EXAMPLEKBID'
            os.environ['BEDROCK_KB_FORCE_OVERRIDE'] = true_value

            # Force reload the module to pick up the new environment variables
            import awslabs.bedrock_kb_retrieval_mcp_server.server
            importlib.reload(awslabs.bedrock_kb_retrieval_mcp_server.server)

            # Verify that the force override is enabled
            assert awslabs.bedrock_kb_retrieval_mcp_server.server.kb_force_override is True, f"Failed for value: {true_value}"
            
            # Clean up for next iteration
            del os.environ['BEDROCK_KB_ID']
            del os.environ['BEDROCK_KB_FORCE_OVERRIDE']

    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.get_bedrock_agent_runtime_client')
    @patch('awslabs.bedrock_kb_retrieval_mcp_server.server.get_bedrock_agent_client')
    def test_bedrock_kb_force_override_disabled_with_invalid_value(self, mock_agent_client, mock_runtime_client):
        """Test that force override remains disabled with invalid values."""
        # Set the environment variable to an invalid value
        os.environ['BEDROCK_KB_FORCE_OVERRIDE'] = 'invalid'

        # Force reload the module to pick up the new environment variable
        import awslabs.bedrock_kb_retrieval_mcp_server.server
        importlib.reload(awslabs.bedrock_kb_retrieval_mcp_server.server)

        # Verify that the force override remains False
        assert awslabs.bedrock_kb_retrieval_mcp_server.server.kb_force_override is False