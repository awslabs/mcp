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

"""Tests for change_cluster_status tool."""

import json
import pytest
from awslabs.rds_control_plane_mcp_server.tools.db_cluster.change_cluster_status import (
    change_cluster_status,
)
from unittest.mock import patch


class TestChangeClusterStatus:
    """Test cases for change_cluster_status function."""

    @pytest.mark.asyncio
    async def test_status_cluster_readonly_mode(self, mock_rds_context_readonly):
        """Test cluster status change in readonly mode."""
        result = await change_cluster_status(db_cluster_identifier='test-cluster', action='start')

        result_dict = json.loads(result)
        assert 'error' in result_dict
        assert 'read-only mode' in result_dict['error']

    @pytest.mark.asyncio
    async def test_status_cluster_requires_confirmation(self, mock_rds_context_allowed):
        """Test that cluster status change requires confirmation."""
        result = await change_cluster_status(db_cluster_identifier='test-cluster', action='start')

        result_dict = json.loads(result)
        assert result_dict['requires_confirmation'] is True
        assert 'confirmation_token' in result_dict

    @pytest.mark.asyncio
    async def test_invalid_action(self, mock_rds_context_allowed):
        """Test invalid action returns error."""
        with patch(
            'awslabs.rds_control_plane_mcp_server.common.confirmation.get_pending_operation'
        ) as mock_get:
            mock_get.return_value = (
                'change_cluster_status',
                {'db_cluster_identifier': 'test-cluster', 'action': 'invalid'},
                123456,
            )

            result = await change_cluster_status(
                db_cluster_identifier='test-cluster', action='invalid', confirmation_token='token'
            )

            assert 'error' in result
            assert 'Invalid action' in result['error']

    @pytest.mark.asyncio
    async def test_start_cluster_success(self, mock_rds_client, mock_rds_context_allowed):
        """Test successful cluster start."""
        mock_rds_client.start_db_cluster.return_value = {
            'DBCluster': {'DBClusterIdentifier': 'test-cluster', 'Status': 'starting'}
        }

        mock_get = patch(
            'awslabs.rds_control_plane_mcp_server.common.confirmation.get_pending_operation'
        ).start()
        mock_remove = patch(
            'awslabs.rds_control_plane_mcp_server.common.confirmation.remove_pending_operation'
        ).start()
        try:
            mock_get.return_value = (
                'change_cluster_status',
                {'db_cluster_identifier': 'test-cluster', 'action': 'start'},
                123456,
            )

            result = await change_cluster_status(
                db_cluster_identifier='test-cluster', action='start', confirmation_token='token'
            )

            assert 'DB cluster test-cluster has been started successfully' in result['message']
        finally:
            mock_get.stop()
            mock_remove.stop()

    @pytest.mark.asyncio
    async def test_stop_cluster_success(self, mock_rds_client, mock_rds_context_allowed):
        """Test successful cluster stop."""
        mock_rds_client.stop_db_cluster.return_value = {
            'DBCluster': {'DBClusterIdentifier': 'test-cluster', 'Status': 'stopping'}
        }

        with (
            patch(
                'awslabs.rds_control_plane_mcp_server.common.confirmation.get_pending_operation'
            ) as mock_get,
            patch(
                'awslabs.rds_control_plane_mcp_server.common.confirmation.remove_pending_operation'
            ),
        ):
            mock_get.return_value = (
                'change_cluster_status',
                {'db_cluster_identifier': 'test-cluster', 'action': 'stop'},
                123456,
            )

            result = await change_cluster_status(
                db_cluster_identifier='test-cluster', action='stop', confirmation_token='token'
            )

            assert 'DB cluster test-cluster has been stopped successfully' in result['message']

    @pytest.mark.asyncio
    async def test_reboot_cluster_success(self, mock_rds_client, mock_rds_context_allowed):
        """Test successful cluster reboot."""
        mock_rds_client.reboot_db_cluster.return_value = {
            'DBCluster': {'DBClusterIdentifier': 'test-cluster', 'Status': 'rebooting'}
        }

        mock_get = patch(
            'awslabs.rds_control_plane_mcp_server.common.confirmation.get_pending_operation'
        ).start()
        mock_remove = patch(
            'awslabs.rds_control_plane_mcp_server.common.confirmation.remove_pending_operation'
        ).start()
        try:
            mock_get.return_value = (
                'change_cluster_status',
                {'db_cluster_identifier': 'test-cluster', 'action': 'reboot'},
                123456,
            )

            result = await change_cluster_status(
                db_cluster_identifier='test-cluster', action='reboot', confirmation_token='token'
            )

            assert 'DB cluster test-cluster has been rebooted successfully' in result['message']
        finally:
            mock_get.stop()
            mock_remove.stop()

    @pytest.mark.asyncio
    async def test_invalid_confirmation_token(self, mock_rds_context_allowed):
        """Test invalid confirmation token."""
        with patch(
            'awslabs.rds_control_plane_mcp_server.common.confirmation.get_pending_operation'
        ) as mock_get:
            mock_get.return_value = None

            result = await change_cluster_status(
                db_cluster_identifier='test-cluster',
                action='start',
                confirmation_token='invalid-token',
            )

            result_dict = json.loads(result) if isinstance(result, str) else result
            assert 'error' in result_dict
            assert 'Invalid or expired confirmation token' in result_dict['error']

    @pytest.mark.asyncio
    async def test_case_insensitive_actions(self, mock_rds_client, mock_rds_context_allowed):
        """Test that actions are case insensitive."""
        mock_rds_client.start_db_cluster.return_value = {
            'DBCluster': {'DBClusterIdentifier': 'test-cluster', 'Status': 'starting'}
        }

        with (
            patch(
                'awslabs.rds_control_plane_mcp_server.common.confirmation.get_pending_operation'
            ) as mock_get,
            patch(
                'awslabs.rds_control_plane_mcp_server.common.confirmation.remove_pending_operation'
            ),
        ):
            mock_get.return_value = (
                'change_cluster_status',
                {'db_cluster_identifier': 'test-cluster', 'action': 'START'},
                123456,
            )

            result = await change_cluster_status(
                db_cluster_identifier='test-cluster', action='START', confirmation_token='token'
            )

            assert 'DB cluster test-cluster has been started successfully' in result['message']
