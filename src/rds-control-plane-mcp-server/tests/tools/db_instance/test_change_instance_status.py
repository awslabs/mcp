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

        result_dict = json.loads(result)
        assert 'error' in result_dict
        assert 'read-only mode' in result_dict['error']

    @pytest.mark.asyncio
    async def test_status_instance_requires_confirmation(self, mock_rds_context_allowed):
        """Test that instance status change requires confirmation."""
        result = await change_instance_status(
            db_instance_identifier='test-instance', action='start'
        )

        result_dict = json.loads(result)
        assert result_dict['requires_confirmation'] is True
        assert 'confirmation_token' in result_dict

    @pytest.mark.asyncio
    async def test_invalid_action(self, mock_rds_context_allowed):
        """Test invalid action returns error."""
        from unittest.mock import patch

        with patch(
            'awslabs.rds_control_plane_mcp_server.common.confirmation.get_pending_operation'
        ) as mock_get:
            mock_get.return_value = (
                'change_instance_status',
                {'db_instance_identifier': 'test-instance', 'action': 'invalid'},
                123456,
            )

            result = await change_instance_status(
                db_instance_identifier='test-instance',
                action='invalid',
                confirmation_token='token',
            )

            assert 'error' in result
            assert 'Invalid action' in result['error']

    @pytest.mark.asyncio
    async def test_start_instance_success(self, mock_rds_client, mock_rds_context_allowed):
        """Test successful instance start."""
        from unittest.mock import patch

        mock_rds_client.start_db_instance.return_value = {
            'DBInstance': {'DBInstanceIdentifier': 'test-instance', 'DBInstanceStatus': 'starting'}
        }

        mock_get = patch(
            'awslabs.rds_control_plane_mcp_server.common.confirmation.get_pending_operation'
        ).start()
        mock_remove = patch(
            'awslabs.rds_control_plane_mcp_server.common.confirmation.remove_pending_operation'
        ).start()
        try:
            mock_get.return_value = (
                'change_instance_status',
                {'db_instance_identifier': 'test-instance', 'action': 'start'},
                123456,
            )

            result = await change_instance_status(
                db_instance_identifier='test-instance', action='start', confirmation_token='token'
            )

            assert 'DB instance test-instance has been started successfully' in result['message']
        finally:
            mock_get.stop()
            mock_remove.stop()

    @pytest.mark.asyncio
    async def test_stop_instance_success(self, mock_rds_client, mock_rds_context_allowed):
        """Test successful instance stop."""
        from unittest.mock import patch

        mock_rds_client.stop_db_instance.return_value = {
            'DBInstance': {'DBInstanceIdentifier': 'test-instance', 'DBInstanceStatus': 'stopping'}
        }

        mock_get = patch(
            'awslabs.rds_control_plane_mcp_server.common.confirmation.get_pending_operation'
        ).start()
        mock_remove = patch(
            'awslabs.rds_control_plane_mcp_server.common.confirmation.remove_pending_operation'
        ).start()
        try:
            mock_get.return_value = (
                'change_instance_status',
                {'db_instance_identifier': 'test-instance', 'action': 'stop'},
                123456,
            )

            result = await change_instance_status(
                db_instance_identifier='test-instance', action='stop', confirmation_token='token'
            )

            assert 'DB instance test-instance has been stopped successfully' in result['message']
        finally:
            mock_get.stop()
            mock_remove.stop()

    @pytest.mark.asyncio
    async def test_reboot_instance_success(self, mock_rds_client, mock_rds_context_allowed):
        """Test successful instance reboot."""
        from unittest.mock import patch

        mock_rds_client.reboot_db_instance.return_value = {
            'DBInstance': {
                'DBInstanceIdentifier': 'test-instance',
                'DBInstanceStatus': 'rebooting',
            }
        }

        mock_get = patch(
            'awslabs.rds_control_plane_mcp_server.common.confirmation.get_pending_operation'
        ).start()
        mock_remove = patch(
            'awslabs.rds_control_plane_mcp_server.common.confirmation.remove_pending_operation'
        ).start()
        try:
            mock_get.return_value = (
                'change_instance_status',
                {'db_instance_identifier': 'test-instance', 'action': 'reboot'},
                123456,
            )

            result = await change_instance_status(
                db_instance_identifier='test-instance', action='reboot', confirmation_token='token'
            )

            assert 'DB instance test-instance has been rebooted successfully' in result['message']
        finally:
            mock_get.stop()
            mock_remove.stop()

    @pytest.mark.asyncio
    async def test_reboot_with_failover(self, mock_rds_client, mock_rds_context_allowed):
        """Test reboot with force failover."""
        from unittest.mock import patch

        mock_rds_client.reboot_db_instance.return_value = {
            'DBInstance': {
                'DBInstanceIdentifier': 'test-instance',
                'DBInstanceStatus': 'rebooting',
            }
        }

        mock_get = patch(
            'awslabs.rds_control_plane_mcp_server.common.confirmation.get_pending_operation'
        ).start()
        mock_remove = patch(
            'awslabs.rds_control_plane_mcp_server.common.confirmation.remove_pending_operation'
        ).start()
        try:
            mock_get.return_value = (
                'change_instance_status',
                {
                    'db_instance_identifier': 'test-instance',
                    'action': 'reboot',
                    'force_failover': True,
                },
                123456,
            )

            result = await change_instance_status(
                db_instance_identifier='test-instance',
                action='reboot',
                force_failover=True,
                confirmation_token='token',
            )

            assert 'DB instance test-instance has been rebooted successfully' in result['message']
        finally:
            mock_get.stop()
            mock_remove.stop()
