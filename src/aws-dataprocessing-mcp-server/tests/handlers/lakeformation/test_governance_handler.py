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

import unittest
from awslabs.aws_dataprocessing_mcp_server.handlers.lakeformation.governance_handler import (
    GovernanceHandler,
)
from mcp.server.fastmcp import Context
from unittest.mock import AsyncMock, MagicMock, patch


class TestGovernanceHandler(unittest.TestCase):
    """Test cases for the GovernanceHandler class.

    This test class contains unit tests for AWS Lake Formation governance operations
    including permissions management, data lake settings, and resource management.
    """

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mcp = MagicMock()
        # Set a default region for boto3 clients in tests
        import os

        os.environ['AWS_REGION'] = 'us-east-1'
        self.handler = GovernanceHandler(self.mcp)
        self.ctx = Context(request_id='test_request_id')

    @patch(
        'awslabs.aws_dataprocessing_mcp_server.core.lakeformation.governance_manager.GovernanceManager.list_permissions'
    )
    async def test_manage_aws_lakeformation_permissions_list(self, mock_list_permissions):
        """Test listing Lake Formation permissions."""
        mock_list_permissions.return_value = AsyncMock()
        await self.handler.manage_aws_lakeformation_permissions(
            self.ctx, operation='list-permissions'
        )
        mock_list_permissions.assert_called_once()

    @patch(
        'awslabs.aws_dataprocessing_mcp_server.core.lakeformation.governance_manager.GovernanceManager.batch_get_effective_permissions_for_path'
    )
    async def test_manage_aws_lakeformation_permissions_batch_get(self, mock_batch_get):
        """Test batch getting effective permissions for a resource path."""
        mock_batch_get.return_value = AsyncMock()
        await self.handler.manage_aws_lakeformation_permissions(
            self.ctx,
            operation='batch-get-effective-permissions-for-path',
            resource_path='s3:///test-bucket',
        )
        mock_batch_get.assert_called_once()

    @patch(
        'awslabs.aws_dataprocessing_mcp_server.core.lakeformation.governance_manager.GovernanceManager.get_data_lake_settings'
    )
    async def test_manage_aws_lakeformation_datalakesettings(self, mock_get_data_lake_settings):
        """Test getting Lake Formation data lake settings."""
        mock_get_data_lake_settings.return_value = AsyncMock()
        await self.handler.manage_aws_lakeformation_datalakesettings(
            self.ctx, operation='get-data-lake-settings'
        )
        mock_get_data_lake_settings.assert_called_once()

    @patch(
        'awslabs.aws_dataprocessing_mcp_server.core.lakeformation.governance_manager.GovernanceManager.list_resources'
    )
    async def test_manage_aws_lakeformation_resources_list(self, mock_list_resources):
        """Test listing Lake Formation resources."""
        mock_list_resources.return_value = AsyncMock()
        await self.handler.manage_aws_lakeformation_resources(self.ctx, operation='list-resources')
        mock_list_resources.assert_called_once()

    @patch(
        'awslabs.aws_dataprocessing_mcp_server.core.lakeformation.governance_manager.GovernanceManager.describe_resource'
    )
    async def test_manage_aws_lakeformation_resources_describe(self, mock_describe_resource):
        """Test describing a specific Lake Formation resource."""
        mock_describe_resource.return_value = AsyncMock()
        await self.handler.manage_aws_lakeformation_resources(
            self.ctx, operation='describe-resource', resource_arn='arn:aws:s3:::test-bucket'
        )
        mock_describe_resource.assert_called_once()

    @patch(
        'awslabs.aws_dataprocessing_mcp_server.core.lakeformation.governance_manager.GovernanceManager.list_permissions'
    )
    async def test_manage_aws_lakeformation_permissions_list_pagination(
        self, mock_list_permissions
    ):
        """Test listing Lake Formation permissions with pagination handling."""
        # Mock the API to return two pages of results
        mock_list_permissions.side_effect = [
            AsyncMock(
                return_value={
                    'PrincipalResourcePermissions': [{'id': 'perm1'}],
                    'NextToken': 'token1',
                }
            ),
            AsyncMock(
                return_value={'PrincipalResourcePermissions': [{'id': 'perm2'}], 'NextToken': None}
            ),
        ]

        result = await self.handler.manage_aws_lakeformation_permissions(
            self.ctx, operation='list-permissions'
        )

        self.assertEqual(len(result.permissions), 2)
        self.assertEqual(result.permissions[0]['id'], 'perm1')
        self.assertEqual(result.permissions[1]['id'], 'perm2')
        self.assertIsNone(result.next_token)
        mock_list_permissions.assert_called()

    @patch(
        'awslabs.aws_dataprocessing_mcp_server.core.lakeformation.governance_manager.GovernanceManager.list_resources'
    )
    async def test_manage_aws_lakeformation_resources_list_pagination(self, mock_list_resources):
        """Test listing Lake Formation resources with pagination handling."""
        # Mock the API to return two pages of results
        mock_list_resources.side_effect = [
            AsyncMock(return_value={'ResourceInfoList': [{'arn': 'arn1'}], 'NextToken': 'token1'}),
            AsyncMock(return_value={'ResourceInfoList': [{'arn': 'arn2'}], 'NextToken': None}),
        ]

        result = await self.handler.manage_aws_lakeformation_resources(
            self.ctx, operation='list-resources'
        )

        self.assertEqual(len(result.resources), 2)
        self.assertEqual(result.resources[0]['arn'], 'arn1')
        self.assertEqual(result.resources[1]['arn'], 'arn2')
        self.assertIsNone(result.next_token)
        mock_list_resources.assert_called()


if __name__ == '__main__':
    unittest.main()
