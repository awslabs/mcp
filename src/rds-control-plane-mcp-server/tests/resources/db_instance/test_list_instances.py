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

"""Tests for list_instances resource."""

import pytest
from awslabs.rds_control_plane_mcp_server.resources.db_instance.list_instances import (
    InstanceSummary,
    list_instances,
)
from typing import Any
from unittest.mock import MagicMock


class TestListInstances:
    """Test list_instances function."""

    @pytest.mark.asyncio
    async def test_success(self, mock_rds_client):
        """Test successful instance list retrieval."""
        mock_paginator = MagicMock()
        mock_rds_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                'DBInstances': [
                    {
                        'DBInstanceIdentifier': 'test-instance-1',
                        'DBInstanceStatus': 'available',
                        'Engine': 'aurora-mysql',
                        'DBInstanceClass': 'db.r5.large',
                        'MultiAZ': False,
                        'PubliclyAccessible': False,
                    },
                    {
                        'DBInstanceIdentifier': 'test-instance-2',
                        'DBInstanceStatus': 'available',
                        'Engine': 'mysql',
                        'DBInstanceClass': 'db.t3.medium',
                        'MultiAZ': False,
                        'PubliclyAccessible': False,
                    },
                ]
            }
        ]

        result = await list_instances()

        assert result.count == 2
        assert len(result.instances) == 2
        assert result.instances[0].instance_id == 'test-instance-1'
        assert result.instances[1].instance_id == 'test-instance-2'
        assert result.resource_uri == 'aws-rds://db-instance'

    @pytest.mark.asyncio
    async def test_empty_response(self, mock_rds_client):
        """Test handling of empty instance response."""
        mock_paginator = MagicMock()
        mock_rds_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'DBInstances': []}]

        result = await list_instances()

        assert result.count == 0
        assert len(result.instances) == 0
        assert result.resource_uri == 'aws-rds://db-instance'

    @pytest.mark.asyncio
    async def test_calls_api_with_correct_parameters(self, mock_rds_client):
        """Test API is called with correct parameters."""
        mock_paginator = MagicMock()
        mock_rds_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'DBInstances': []}]

        await list_instances()

        mock_rds_client.get_paginator.assert_called_once_with('describe_db_instances')
        mock_paginator.paginate.assert_called_once_with(PaginationConfig={'MaxItems': 100})


class TestInstanceSummary:
    """Test InstanceSummary model."""

    def test_from_db_instance_typedef(self):
        """Test model creation from AWS API response."""
        api_response: Any = {
            'DBInstanceIdentifier': 'test-instance',
            'DbiResourceId': 'db-ABCDEFGHIJKLMNOPQRSTUVWXYZ',
            'DBInstanceStatus': 'available',
            'Engine': 'mysql',
            'EngineVersion': '8.0.23',
            'DBInstanceClass': 'db.t3.medium',
            'AvailabilityZone': 'us-east-1a',
            'MultiAZ': True,
            'PubliclyAccessible': False,
            'DBClusterIdentifier': 'test-cluster',
            'TagList': [{'Key': 'Environment', 'Value': 'Production'}],
        }

        instance = InstanceSummary.from_DBInstanceTypeDef(api_response)

        assert instance.instance_id == 'test-instance'
        assert instance.dbi_resource_id == 'db-ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        assert instance.status == 'available'
        assert instance.engine == 'mysql'
        assert instance.engine_version == '8.0.23'
        assert instance.instance_class == 'db.t3.medium'
        assert instance.availability_zone == 'us-east-1a'
        assert instance.multi_az is True
        assert instance.publicly_accessible is False
        assert instance.db_cluster == 'test-cluster'
        assert instance.tag_list['Environment'] == 'Production'

    def test_handles_missing_fields(self):
        """Test model handles missing API response fields."""
        api_response: Any = {
            'DBInstanceIdentifier': 'test-instance',
            'DBInstanceStatus': 'available',
            'Engine': 'mysql',
            'DBInstanceClass': 'db.t3.medium',
        }

        instance = InstanceSummary.from_DBInstanceTypeDef(api_response)

        assert instance.instance_id == 'test-instance'
        assert instance.dbi_resource_id is None
        assert instance.engine_version == ''
        assert instance.availability_zone is None
        assert instance.multi_az is False
        assert instance.publicly_accessible is False
        assert instance.db_cluster is None
        assert instance.tag_list == {}

    def test_handles_empty_tag_list(self):
        """Test model handles empty tag list."""
        api_response: Any = {
            'DBInstanceIdentifier': 'test-instance',
            'DBInstanceStatus': 'available',
            'Engine': 'mysql',
            'DBInstanceClass': 'db.t3.medium',
            'TagList': [],
        }

        instance = InstanceSummary.from_DBInstanceTypeDef(api_response)

        assert instance.tag_list == {}
