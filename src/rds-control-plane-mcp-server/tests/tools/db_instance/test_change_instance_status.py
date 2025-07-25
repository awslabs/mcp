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

"""Tests for change_instance_status tool."""

import json
import pytest
from awslabs.rds_control_plane_mcp_server.tools.db_instance.change_instance_status import (
    change_instance_status,
)


class TestChangeInstanceStatus:
    """Test cases for change_instance_status function."""

    @pytest.mark.asyncio
    async def test_status_instance_readonly_mode(self, mock_rds_context_readonly):
        """Test instance status in readonly mode."""
        result = await change_instance_status(
            db_instance_identifier='test-instance', action='start'
        )

        assert 'error' in result
        assert 'read-only mode' in result['error']

    @pytest.mark.asyncio
    async def test_status_instance_requires_confirmation(self, mock_rds_context_allowed):
        """Test that instance status change requires confirmation."""
        result = await change_instance_status(
            db_instance_identifier='test-instance', action='start'
        )

        assert result['requires_confirmation'] is True
        assert 'confirmation_token' in result

    @pytest.mark.asyncio
    async def test_invalid_action(self, mock_rds_context_allowed):
        """Test invalid action returns error."""
        # Manually add a pending operation to simulate the confirmation flow
        from awslabs.rds_control_plane_mcp_server.common.decorators.require_confirmation import _pending_operations
        import time

        # Add a fake pending operation
        token = 'test-token'
        _pending_operations[token] = (
            'ChangeDBInstanceStatus',
            {'db_instance_identifier': 'test-instance', 'action': 'invalid'},
            time.time() + 300,
        )

        result = await change_instance_status(
            db_instance_identifier='test-instance',
            action='invalid',
            confirmation_token=token,
        )

        assert 'error' in result
        assert 'Invalid action' in result['error']

    @pytest.mark.asyncio
    async def test_start_instance_success(self, mock_rds_client, mock_rds_context_allowed):
        """Test successful instance start."""
        from awslabs.rds_control_plane_mcp_server.common.decorators.require_confirmation import _pending_operations
        import time

        mock_rds_client.start_db_instance.return_value = {
            'DBInstance': {'DBInstanceIdentifier': 'test-instance', 'DBInstanceStatus': 'starting'}
        }

        # Add a fake pending operation
        token = 'test-token'
        _pending_operations[token] = (
            'ChangeDBInstanceStatus',
            {'db_instance_identifier': 'test-instance', 'action': 'start'},
            time.time() + 300,
        )

        result = await change_instance_status(
            db_instance_identifier='test-instance', action='start', confirmation_token=token
        )

        assert 'DB instance test-instance has been started successfully' in result['message']

    @pytest.mark.asyncio
    async def test_stop_instance_success(self, mock_rds_client, mock_rds_context_allowed):
        """Test successful instance stop."""
        from awslabs.rds_control_plane_mcp_server.common.decorators.require_confirmation import _pending_operations
        import time

        mock_rds_client.stop_db_instance.return_value = {
            'DBInstance': {'DBInstanceIdentifier': 'test-instance', 'DBInstanceStatus': 'stopping'}
        }

        # Add a fake pending operation
        token = 'test-token'
        _pending_operations[token] = (
            'ChangeDBInstanceStatus',
            {'db_instance_identifier': 'test-instance', 'action': 'stop'},
            time.time() + 300,
        )

        result = await change_instance_status(
            db_instance_identifier='test-instance', action='stop', confirmation_token=token
        )

        assert 'DB instance test-instance has been stopped successfully' in result['message']

    @pytest.mark.asyncio
    async def test_reboot_instance_success(self, mock_rds_client, mock_rds_context_allowed):
        """Test successful instance reboot."""
        from awslabs.rds_control_plane_mcp_server.common.decorators.require_confirmation import _pending_operations
        import time

        mock_rds_client.reboot_db_instance.return_value = {
            'DBInstance': {
                'DBInstanceIdentifier': 'test-instance',
                'DBInstanceStatus': 'rebooting',
            }
        }

        # Add a fake pending operation
        token = 'test-token'
        _pending_operations[token] = (
            'ChangeDBInstanceStatus',
            {'db_instance_identifier': 'test-instance', 'action': 'reboot'},
            time.time() + 300,
        )

        result = await change_instance_status(
            db_instance_identifier='test-instance', action='reboot', confirmation_token=token
        )

        assert 'DB instance test-instance has been rebooted successfully' in result['message']

    @pytest.mark.asyncio
    async def test_reboot_with_failover(self, mock_rds_client, mock_rds_context_allowed):
        """Test reboot with force failover."""
        from awslabs.rds_control_plane_mcp_server.common.decorators.require_confirmation import _pending_operations
        import time

        mock_rds_client.reboot_db_instance.return_value = {
            'DBInstance': {
                'DBInstanceIdentifier': 'test-instance',
                'DBInstanceStatus': 'rebooting',
            }
        }

        # Add a fake pending operation
        token = 'test-token'
        _pending_operations[token] = (
            'ChangeDBInstanceStatus',
            {
                'db_instance_identifier': 'test-instance',
                'action': 'reboot',
                'force_failover': True,
            },
            time.time() + 300,
        )

        result = await change_instance_status(
            db_instance_identifier='test-instance',
            action='reboot',
            force_failover=True,
            confirmation_token=token,
        )

        assert 'DB instance test-instance has been rebooted successfully' in result['message']
