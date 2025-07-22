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

"""Tests for failover_cluster tool."""

import json
import pytest
from awslabs.rds_control_plane_mcp_server.tools.db_cluster.failover_cluster import (
    failover_db_cluster,
)
from unittest.mock import patch


class TestFailoverCluster:
    """Test cases for failover_db_cluster function."""

    @pytest.mark.asyncio
    async def test_failover_cluster_readonly_mode(self, mock_rds_context_readonly):
        """Test cluster failover in readonly mode."""
        result = await failover_db_cluster(db_cluster_identifier='test-cluster')

        assert 'error' in result
        assert 'read-only mode' in result['error']

    @pytest.mark.asyncio
    async def test_failover_cluster_no_confirmation(self, mock_rds_context_allowed):
        """Test cluster failover without confirmation token."""
        result = await failover_db_cluster(db_cluster_identifier='test-cluster')

        assert result['requires_confirmation'] is True
        assert 'confirmation_token' in result

    @pytest.mark.asyncio
    async def test_failover_cluster_success(self, mock_rds_client, mock_rds_context_allowed):
        """Test successful cluster failover."""
        mock_rds_client.failover_db_cluster.return_value = {
            'DBCluster': {
                'DBClusterIdentifier': 'test-cluster',
                'Status': 'failing-over',
                'Engine': 'aurora-mysql',
            }
        }

        with patch(
            'awslabs.rds_control_plane_mcp_server.common.decorators.require_confirmation._pending_operations',
            {'valid-token': (
                'FailoverDBCluster',
                {'db_cluster_identifier': 'test-cluster'},
                9999999999,
            )}
        ):
            result = await failover_db_cluster(
                db_cluster_identifier='test-cluster',
                confirmation_token='valid-token',
            )

            assert (
                result['message'] == 'DB cluster test-cluster has been failed over successfully.'
            )

    @pytest.mark.asyncio
    async def test_failover_cluster_with_target(self, mock_rds_client, mock_rds_context_allowed):
        """Test cluster failover with target instance."""
        mock_rds_client.failover_db_cluster.return_value = {
            'DBCluster': {
                'DBClusterIdentifier': 'test-cluster',
                'Status': 'failing-over',
                'Engine': 'aurora-mysql',
            }
        }

        with patch(
            'awslabs.rds_control_plane_mcp_server.common.decorators.require_confirmation._pending_operations',
            {'valid-token': (
                'FailoverDBCluster',
                {
                    'db_cluster_identifier': 'test-cluster',
                    'target_db_instance_identifier': 'target-instance',
                },
                9999999999,
            )}
        ):
            result = await failover_db_cluster(
                db_cluster_identifier='test-cluster',
                target_db_instance_identifier='target-instance',
                confirmation_token='valid-token',
            )

            assert (
                result['message'] == 'DB cluster test-cluster has been failed over successfully.'
            )
