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

"""Tests for delete_instance tool."""

import json
import pytest
from awslabs.rds_control_plane_mcp_server.tools.db_instance.delete_instance import (
    delete_db_instance,
)
from unittest.mock import patch


class TestDeleteInstance:
    """Test cases for delete_db_instance function."""

    @pytest.mark.asyncio
    async def test_delete_instance_readonly_mode(self, mock_rds_context_readonly):
        """Test instance deletion in readonly mode."""
        result = await delete_db_instance(
            db_instance_identifier='test-instance', skip_final_snapshot=True
        )

        assert 'error' in result
        assert 'read-only mode' in result['error']

    @pytest.mark.asyncio
    async def test_delete_instance_no_confirmation(self, mock_rds_context_allowed):
        """Test instance deletion without confirmation token."""
        result = await delete_db_instance(
            db_instance_identifier='test-instance', skip_final_snapshot=True
        )

        assert result['requires_confirmation'] is True
        assert 'confirmation_token' in result
        assert 'WARNING' in result['warning']

    @pytest.mark.asyncio
    async def test_delete_instance_with_valid_token(
        self, mock_rds_client, mock_rds_context_allowed
    ):
        """Test instance deletion with valid confirmation token."""
        mock_rds_client.delete_db_instance.return_value = {
            'DBInstance': {
                'DBInstanceIdentifier': 'test-instance',
                'DBInstanceStatus': 'deleting',
                'Engine': 'mysql',
            }
        }

        with patch(
            'awslabs.rds_control_plane_mcp_server.common.decorators.require_confirmation._pending_operations',
            {'valid-token': (
                'DeleteDBInstance',
                {'db_instance_identifier': 'test-instance', 'skip_final_snapshot': True},
                9999999999,
            )}
        ):
            result = await delete_db_instance(
                db_instance_identifier='test-instance',
                skip_final_snapshot=True,
                confirmation_token='valid-token',
            )

            assert result['message'] == 'DB instance test-instance has been deleted successfully.'

    @pytest.mark.asyncio
    async def test_delete_instance_invalid_token(self, mock_rds_context_allowed):
        """Test instance deletion with invalid confirmation token."""
        result = await delete_db_instance(
            db_instance_identifier='test-instance',
            skip_final_snapshot=True,
            confirmation_token='invalid-token',
        )

        assert 'error' in result
        assert 'Invalid or expired confirmation token' in result['error']
