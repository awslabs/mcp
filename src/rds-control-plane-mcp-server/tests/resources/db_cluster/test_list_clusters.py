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

"""Tests for list_clusters resource."""

import pytest
from awslabs.rds_control_plane_mcp_server.resources.db_cluster.list_clusters import (
    ClusterSummary,
    list_clusters,
)
from botocore.exceptions import ClientError
from typing import Any
from unittest.mock import MagicMock


class TestListClusters:
    """Test list_clusters function."""

    @pytest.mark.asyncio
    async def test_success(self, mock_rds_client):
        """Test successful cluster list retrieval."""
        mock_paginator = MagicMock()
        mock_rds_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                'DBClusters': [
                    {
                        'DBClusterIdentifier': 'test-cluster-1',
                        'Status': 'available',
                        'Engine': 'aurora-mysql',
                        'MultiAZ': True,
                    },
                    {
                        'DBClusterIdentifier': 'test-cluster-2',
                        'Status': 'available',
                        'Engine': 'aurora-postgresql',
                        'MultiAZ': False,
                    },
                ]
            }
        ]

        result = await list_clusters()

        assert result.count == 2
        assert len(result.clusters) == 2
        assert result.clusters[0].cluster_id == 'test-cluster-1'
        assert result.clusters[1].cluster_id == 'test-cluster-2'

    @pytest.mark.asyncio
    async def test_empty_response(self, mock_rds_client):
        """Test handling of empty cluster response."""
        mock_paginator = MagicMock()
        mock_rds_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'DBClusters': []}]

        result = await list_clusters()

        assert result.count == 0
        assert len(result.clusters) == 0

    @pytest.mark.asyncio
    async def test_calls_api_with_correct_parameters(self, mock_rds_client):
        """Test API is called with correct parameters."""
        mock_paginator = MagicMock()
        mock_rds_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{'DBClusters': []}]

        await list_clusters()

        mock_rds_client.get_paginator.assert_called_once_with('describe_db_clusters')
        mock_paginator.paginate.assert_called_once_with(PaginationConfig={'MaxItems': 100})

    @pytest.mark.asyncio
    async def test_client_error(self, mock_rds_client):
        """Test error propagation from RDS client."""
        error_response = {
            'Error': {'Code': 'InvalidParameterCombination', 'Message': 'Invalid parameter'}
        }
        mock_rds_client.get_paginator.side_effect = ClientError(
            error_response, 'DescribeDBClusters'
        )

        result = await list_clusters()

        # The decorator returns dict error response instead of raising
        assert isinstance(result, dict)
        assert result['error_code'] == 'InvalidParameterCombination'


class TestClusterSummary:
    """Test ClusterSummary model."""

    def test_from_db_cluster_typedef(self):
        """Test model creation from AWS API response."""
        api_response: Any = {
            'DBClusterIdentifier': 'test-cluster',
            'DBClusterArn': 'arn:aws:rds:us-east-1:123456789012:cluster:test-cluster',
            'DbClusterResourceId': 'cluster-ABCDEFGHIJKLMNOPQRSTUVWXYZ',
            'Status': 'available',
            'Engine': 'aurora-mysql',
            'EngineVersion': '5.7.12',
            'AvailabilityZones': ['us-east-1a', 'us-east-1b'],
            'MultiAZ': True,
            'TagList': [{'Key': 'Environment', 'Value': 'Production'}],
        }

        cluster = ClusterSummary.from_DBClusterTypeDef(api_response)

        assert cluster.cluster_id == 'test-cluster'
        assert cluster.db_cluster_arn == 'arn:aws:rds:us-east-1:123456789012:cluster:test-cluster'
        assert cluster.db_cluster_resource_id == 'cluster-ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        assert cluster.status == 'available'
        assert cluster.engine == 'aurora-mysql'
        assert cluster.engine_version == '5.7.12'
        assert cluster.availability_zones == ['us-east-1a', 'us-east-1b']
        assert cluster.multi_az is True
        assert cluster.tag_list['Environment'] == 'Production'

    def test_handles_missing_fields(self):
        """Test model handles missing API response fields."""
        api_response: Any = {
            'DBClusterIdentifier': 'test-cluster',
            'Status': 'available',
            'Engine': 'aurora-mysql',
        }

        cluster = ClusterSummary.from_DBClusterTypeDef(api_response)

        assert cluster.cluster_id == 'test-cluster'
        assert cluster.db_cluster_arn is None
        assert cluster.db_cluster_resource_id is None
        assert cluster.engine_version is None
        assert cluster.availability_zones == []
        assert cluster.multi_az is False
        assert cluster.tag_list == {}

    def test_handles_empty_tag_list(self):
        """Test model handles empty tag list."""
        api_response: Any = {
            'DBClusterIdentifier': 'test-cluster',
            'Status': 'available',
            'Engine': 'aurora-mysql',
            'TagList': [],
        }

        cluster = ClusterSummary.from_DBClusterTypeDef(api_response)

        assert cluster.tag_list == {}
