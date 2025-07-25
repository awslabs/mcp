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

"""Tests for create_instance tool."""

import pytest
from awslabs.rds_control_plane_mcp_server.tools.db_instance.create_instance import (
    create_db_instance,
)


class TestCreateInstance:
    """Test cases for create_db_instance function."""

    @pytest.mark.asyncio
    async def test_create_instance_readonly_mode(self, mock_rds_context_readonly):
        """Test instance creation in readonly mode."""
        result = await create_db_instance(
            db_instance_identifier='test-instance', db_instance_class='db.t3.micro', engine='mysql'
        )

        assert 'error' in result
        assert 'read-only mode' in result['error']

    @pytest.mark.asyncio
    async def test_create_cluster_instance_success(
        self, mock_rds_client, mock_rds_context_allowed
    ):
        """Test successful cluster instance creation."""
        mock_rds_client.create_db_instance.return_value = {
            'DBInstance': {
                'DBInstanceIdentifier': 'test-instance',
                'DBInstanceStatus': 'creating',
                'Engine': 'aurora-mysql',
                'DBInstanceClass': 'db.r5.large',
                'DBClusterIdentifier': 'test-cluster',
            }
        }

        result = await create_db_instance(
            db_instance_identifier='test-instance',
            db_instance_class='db.r5.large',
            engine='aurora-mysql',
            db_cluster_identifier='test-cluster',
        )

        assert result['message'] == 'DB instance test-instance has been created successfully.'
        assert 'formatted_instance' in result

    @pytest.mark.asyncio
    async def test_create_standalone_instance_success(
        self, mock_rds_client, mock_rds_context_allowed
    ):
        """Test successful standalone instance creation."""
        mock_rds_client.create_db_instance.return_value = {
            'DBInstance': {
                'DBInstanceIdentifier': 'test-instance',
                'DBInstanceStatus': 'creating',
                'Engine': 'mysql',
                'DBInstanceClass': 'db.t3.micro',
                'AllocatedStorage': 20,
            }
        }

        result = await create_db_instance(
            db_instance_identifier='test-instance',
            db_instance_class='db.t3.micro',
            engine='mysql',
            allocated_storage=20,
            master_username='admin',
        )

        assert result['message'] == 'DB instance test-instance has been created successfully.'

    @pytest.mark.asyncio
    async def test_create_standalone_instance_missing_credentials(
        self, mock_rds_client, mock_rds_context_allowed
    ):
        """Test standalone instance creation without credentials."""
        import json
        from botocore.exceptions import ClientError

        # Mock the RDS client to raise an error about missing MasterUsername
        mock_rds_client.create_db_instance.side_effect = ClientError(
            error_response={
                'Error': {
                    'Code': 'InvalidParameterValue',
                    'Message': 'The parameter MasterUsername must be provided and must not be blank.',
                }
            },
            operation_name='CreateDBInstance',
        )

        result = await create_db_instance(
            db_instance_identifier='test-instance',
            db_instance_class='db.t3.micro',
            engine='mysql',
            allocated_storage=20,
        )

        assert 'error' in result
        assert 'MasterUsername' in result['error_message']
