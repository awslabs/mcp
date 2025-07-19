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

"""Tests for write protection functionality."""

import awslabs.aws_fis_mcp_server.server as server_module
import pytest
from awslabs.aws_fis_mcp_server.server import (
    create_experiment_template,
    create_view,
    start_experiment,
)
from unittest.mock import AsyncMock, MagicMock, patch


class TestWriteProtection:
    """Test cases for write protection functionality."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Set up mocks for AWS clients."""
        self.mock_aws_fis = MagicMock()
        self.mock_resource_explorer = MagicMock()
        self.mock_context = AsyncMock()

        with (
            patch.object(server_module, 'aws_fis', self.mock_aws_fis),
            patch.object(server_module, 'resource_explorer', self.mock_resource_explorer),
            patch.object(server_module, 'allow_writes', False),  # Disable writes for testing
        ):
            yield

    @pytest.mark.asyncio
    async def test_start_experiment_write_protection(self):
        """Test write protection for start_experiment."""
        with pytest.raises(Exception, match='Write operations are disabled'):
            await start_experiment(self.mock_context, 'template-123', 'Test Experiment')

        # Verify error was logged to context
        self.mock_context.error.assert_called_once()
        error_call = self.mock_context.error.call_args[0][0]
        assert 'Write operations are disabled' in error_call
        assert '--allow-writes flag' in error_call

    @pytest.mark.asyncio
    async def test_create_experiment_template_write_protection(self):
        """Test write protection for create_experiment_template."""
        with pytest.raises(Exception, match='Write operations are disabled'):
            await create_experiment_template(
                self.mock_context,
                'client-token',
                'Test template',
                'arn:aws:iam::123456789012:role/test-role',
                'Test Template Name',
            )

        # Verify error was logged to context
        self.mock_context.error.assert_called_once()
        error_call = self.mock_context.error.call_args[0][0]
        assert 'Write operations are disabled' in error_call
        assert 'template creation' in error_call

    @pytest.mark.asyncio
    async def test_create_view_write_protection(self):
        """Test write protection for create_view."""
        with pytest.raises(Exception, match='Write operations are disabled'):
            await create_view(
                self.mock_context, 'resourcetype:EC2::Instance', 'test-view', 'Test View Name'
            )

        # Verify error was logged to context
        self.mock_context.error.assert_called_once()
        error_call = self.mock_context.error.call_args[0][0]
        assert 'Write operations are disabled' in error_call
        assert 'Resource Explorer view creation' in error_call


class TestWriteProtectionEnabled:
    """Test cases when write protection is disabled (writes allowed)."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Set up mocks for AWS clients with writes enabled."""
        self.mock_aws_fis = MagicMock()
        self.mock_resource_explorer = MagicMock()
        self.mock_context = AsyncMock()

        with (
            patch.object(server_module, 'aws_fis', self.mock_aws_fis),
            patch.object(server_module, 'resource_explorer', self.mock_resource_explorer),
            patch.object(server_module, 'allow_writes', True),  # Enable writes
        ):
            yield

    @pytest.mark.asyncio
    async def test_start_experiment_writes_enabled(self):
        """Test start_experiment works when writes are enabled."""
        self.mock_aws_fis.start_experiment.return_value = {
            'experiment': {'id': 'exp-123', 'state': {'status': 'pending'}}
        }

        result = await start_experiment(
            self.mock_context,
            'template-123',  # id
            'Test Experiment',  # name
            None,  # tags
            'run-all',  # action
        )

        # Should not raise exception and should call AWS
        assert result['experiment_id'] == 'exp-123'
        self.mock_aws_fis.start_experiment.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_experiment_template_writes_enabled(self):
        """Test create_experiment_template works when writes are enabled."""
        self.mock_aws_fis.create_experiment_template.return_value = {
            'experimentTemplate': {'id': 'template-123'}
        }

        result = await create_experiment_template(
            self.mock_context,
            'client-token',  # clientToken
            'Test template',  # description
            'arn:aws:iam::123456789012:role/test-role',  # role_arn
            'Test Template Name',  # name
            None,  # tags
            None,  # stop_conditions
            None,  # targets
            None,  # actions
            None,  # log_configuration
            None,  # experiment_options
            None,  # report_configuration
        )

        # Should not raise exception and should call AWS
        assert 'experimentTemplate' in result
        self.mock_aws_fis.create_experiment_template.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_view_writes_enabled(self):
        """Test create_view works when writes are enabled."""
        self.mock_resource_explorer.create_view.return_value = {
            'View': {
                'ViewArn': 'arn:aws:resource-explorer-2:us-east-1:123456789012:view/test-view'
            }
        }

        result = await create_view(
            self.mock_context,
            'resourcetype:EC2::Instance',  # query
            'test-view',  # view_name
            'Test View Name',  # name
            None,  # tags
            None,  # scope
            None,  # client_token
        )

        # Should not raise exception and should call AWS
        assert 'View' in result
        self.mock_resource_explorer.create_view.assert_called_once()
