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

"""Tests for modify_instance tool."""

import json
import pytest
from awslabs.rds_control_plane_mcp_server.tools.db_instance.modify_instance import (
    modify_db_instance,
)


class TestModifyInstance:
    """Test cases for modify_db_instance function."""

    @pytest.mark.asyncio
    async def test_modify_instance_readonly_mode(self, mock_rds_context_readonly):
        """Test instance modification in readonly mode."""
        result = await modify_db_instance(
            db_instance_identifier='test-instance', allocated_storage=30
        )

        assert 'error' in result
        assert 'read-only mode' in result['error']

    @pytest.mark.asyncio
    async def test_modify_instance_success(self, mock_rds_client, mock_rds_context_allowed):
        """Test successful instance modification."""
        mock_rds_client.modify_db_instance.return_value = {
            'DBInstance': {
                'DBInstanceIdentifier': 'test-instance',
                'DBInstanceStatus': 'modifying',
                'Engine': 'mysql',
                'AllocatedStorage': 30,
            }
        }

        result = await modify_db_instance(
            db_instance_identifier='test-instance', allocated_storage=30, apply_immediately=True
        )

        assert result['message'] == 'DB instance test-instance has been modified successfully.'

    @pytest.mark.asyncio
    async def test_modify_instance_with_all_params(
        self, mock_rds_client, mock_rds_context_allowed
    ):
        """Test instance modification with all optional parameters."""
        instance_response = {
            'DBInstance': {
                'DBInstanceIdentifier': 'test-instance',
                'DBInstanceStatus': 'modifying',
                'Engine': 'mysql',
                'DBInstanceClass': 'db.t3.medium',
            }
        }
        mock_rds_client.modify_db_instance.return_value = instance_response

        result = await modify_db_instance(
            db_instance_identifier='test-instance',
            apply_immediately=True,
            allocated_storage=50,
            db_instance_class='db.t3.medium',
            storage_type='gp3',
            vpc_security_group_ids=['sg-123', 'sg-456'],
            backup_retention_period=14,
            multi_az=True,
            engine_version='8.0.35',
            allow_major_version_upgrade=True,
            publicly_accessible=False,
        )

        assert result['message'] == 'DB instance test-instance has been modified successfully.'

    @pytest.mark.asyncio
    async def test_modify_instance_minimal_params(self, mock_rds_client, mock_rds_context_allowed):
        """Test instance modification with minimal parameters."""
        instance_response = {
            'DBInstance': {
                'DBInstanceIdentifier': 'test-instance',
                'DBInstanceStatus': 'available',
                'Engine': 'mysql',
            }
        }
        mock_rds_client.modify_db_instance.return_value = instance_response

        result = await modify_db_instance(db_instance_identifier='test-instance')

        assert result['message'] == 'DB instance test-instance has been modified successfully.'
