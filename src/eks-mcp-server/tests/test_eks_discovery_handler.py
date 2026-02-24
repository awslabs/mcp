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
# ruff: noqa: D101, D102, D103
"""Tests for the EKS Discovery Handler."""

import json
import pytest
from awslabs.eks_mcp_server.config import (
    AccountConfig,
    ClusterConfig,
    ClustersConfig,
    ConfigManager,
)
from awslabs.eks_mcp_server.eks_discovery_handler import (
    ClusterInfo,
    DiscoveryError,
    EKSDiscoveryHandler,
)
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from unittest.mock import MagicMock, patch


class TestParseErrorForGuidance:
    """Tests for the _parse_error_for_guidance method."""

    def test_parse_error_access_denied_list_clusters(self):
        """Test parsing AccessDeniedException for eks:ListClusters."""
        error = Exception(
            'An error occurred (AccessDeniedException) when calling the ListClusters operation: '
            'User: arn:aws:iam::123456789012:user/test is not authorized to perform: '
            'eks:ListClusters on resource: arn:aws:eks:us-west-2:123456789012:cluster/*'
        )

        error_type, guidance = EKSDiscoveryHandler._parse_error_for_guidance(
            error, '123456789012', 'us-west-2'
        )

        assert error_type == 'AccessDeniedException'
        assert 'Missing IAM permission: eks:ListClusters' in guidance
        assert 'Update the IAM role/user for account 123456789012' in guidance
        assert 'Example policy' in guidance

    def test_parse_error_access_denied_describe_cluster(self):
        """Test parsing AccessDeniedException for eks:DescribeCluster."""
        error = Exception(
            'An error occurred (AccessDeniedException) when calling the DescribeCluster operation: '
            'User is not authorized to perform: eks:DescribeCluster'
        )

        error_type, guidance = EKSDiscoveryHandler._parse_error_for_guidance(
            error, '123456789012', 'us-west-2'
        )

        assert error_type == 'AccessDeniedException'
        assert 'Missing IAM permission: eks:DescribeCluster' in guidance
        assert 'Update the IAM role/user for account 123456789012' in guidance

    def test_parse_error_access_denied_assume_role(self):
        """Test parsing AccessDeniedException for sts:AssumeRole."""
        error = Exception(
            'An error occurred (AccessDeniedException) when calling the AssumeRole operation: '
            'User is not authorized to perform: sts:AssumeRole'
        )

        error_type, guidance = EKSDiscoveryHandler._parse_error_for_guidance(
            error, '123456789012', 'us-west-2'
        )

        assert error_type == 'AccessDeniedException'
        assert 'Missing IAM permission: sts:AssumeRole' in guidance
        assert 'trust relationship' in guidance

    def test_parse_error_access_denied_generic(self):
        """Test parsing generic AccessDeniedException."""
        error = Exception('User is not authorized to perform this operation')

        error_type, guidance = EKSDiscoveryHandler._parse_error_for_guidance(
            error, '123456789012', 'us-west-2'
        )

        assert error_type == 'AccessDeniedException'
        assert 'Access denied in account 123456789012, region us-west-2' in guidance
        assert 'Verify IAM permissions for EKS operations' in guidance

    def test_parse_error_credential_error(self):
        """Test parsing credential errors."""
        error = Exception('Invalid credentials provided')

        error_type, guidance = EKSDiscoveryHandler._parse_error_for_guidance(
            error, '123456789012', 'us-west-2'
        )

        assert error_type == 'CredentialError'
        assert 'Invalid or missing AWS credentials for account 123456789012' in guidance
        assert 'Verify AWS credentials configuration' in guidance

    def test_parse_error_invalid_client_token(self):
        """Test parsing InvalidClientTokenId error."""
        error = Exception('InvalidClientTokenId: The security token included in the request is invalid')

        error_type, guidance = EKSDiscoveryHandler._parse_error_for_guidance(
            error, '123456789012', 'us-west-2'
        )

        assert error_type == 'CredentialError'
        assert 'Invalid or missing AWS credentials' in guidance

    def test_parse_error_service_exception(self):
        """Test parsing ServiceException."""
        error = Exception('ServiceException: An internal service error occurred')

        error_type, guidance = EKSDiscoveryHandler._parse_error_for_guidance(
            error, '123456789012', 'us-west-2'
        )

        assert error_type == 'ServiceException'
        assert 'AWS service error in us-west-2' in guidance
        assert 'typically temporary' in guidance

    def test_parse_error_internal_failure(self):
        """Test parsing InternalFailure error."""
        error = Exception('InternalFailure: The request processing has failed')

        error_type, guidance = EKSDiscoveryHandler._parse_error_for_guidance(
            error, '123456789012', 'us-west-2'
        )

        assert error_type == 'ServiceException'
        assert 'AWS service error' in guidance

    def test_parse_error_invalid_region(self):
        """Test parsing invalid region error."""
        error = Exception('InvalidRegion: The region specified is not valid')

        error_type, guidance = EKSDiscoveryHandler._parse_error_for_guidance(
            error, '123456789012', 'us-west-2'
        )

        assert error_type == 'RegionError'
        assert 'Invalid or unsupported region: us-west-2' in guidance
        assert 'Verify the region name is correct' in guidance

    def test_parse_error_generic_error(self):
        """Test parsing generic error."""
        error = Exception('Some unexpected error occurred')

        error_type, guidance = EKSDiscoveryHandler._parse_error_for_guidance(
            error, '123456789012', 'us-west-2'
        )

        assert error_type == 'Exception'
        assert 'Error in account 123456789012, region us-west-2' in guidance
        assert 'Some unexpected error occurred' in guidance


class TestListEksClusters:
    """Tests for the list_eks_clusters method."""

    @pytest.fixture
    def mock_mcp(self):
        """Create a mock MCP server instance."""
        mcp = MagicMock()
        mcp.tool = lambda name: lambda func: func
        return mcp

    @pytest.fixture
    def handler(self, mock_mcp):
        """Create an EKSDiscoveryHandler instance."""
        return EKSDiscoveryHandler(mock_mcp)

    @pytest.fixture
    def mock_context(self):
        """Create a mock context."""
        ctx = MagicMock(spec=Context)
        ctx.request_id = 'test-request-id'
        return ctx

    async def test_list_eks_clusters_no_config(self, handler, mock_context):
        """Test list_eks_clusters when no configuration is loaded."""
        # Clear configuration
        ConfigManager._config = None

        result = await handler.list_eks_clusters(mock_context, validate=False)

        assert result.isError is True
        assert len(result.content) == 1
        assert 'No cluster configuration loaded' in result.content[0].text

    async def test_list_eks_clusters_explicit_clusters(self, handler, mock_context):
        """Test list_eks_clusters with explicitly configured clusters."""
        # Setup configuration
        account_config = AccountConfig(
            account_id='123456789012', regions=['us-west-2'], profile='test-profile'
        )
        cluster = ClusterConfig(
            name='test-cluster',
            region='us-west-2',
            account_id='123456789012',
            description='Test cluster',
        )
        config = ClustersConfig(accounts=[account_config], clusters=[cluster])
        ConfigManager._config = config

        result = await handler.list_eks_clusters(mock_context, validate=False)

        assert result.isError is False
        assert len(result.content) == 2

        # Check response text
        response_text = result.content[0].text
        assert 'Found 1 EKS clusters' in response_text
        assert 'configured' in response_text

        # Check JSON data
        data_json = result.content[1].text
        data = json.loads(data_json)
        assert data['count'] == 1
        assert len(data['clusters']) == 1
        assert data['clusters'][0]['name'] == 'test-cluster'
        assert data['clusters'][0]['region'] == 'us-west-2'
        assert data['clusters'][0]['account_id'] == '123456789012'
        assert data['clusters'][0]['access_method'] == 'profile'

    async def test_list_eks_clusters_with_validation(self, handler, mock_context):
        """Test list_eks_clusters with validation enabled."""
        # Setup configuration
        account_config = AccountConfig(
            account_id='123456789012', regions=['us-west-2'], profile='test-profile'
        )
        cluster = ClusterConfig(
            name='test-cluster',
            region='us-west-2',
            account_id='123456789012',
            description='Test cluster',
        )
        config = ClustersConfig(accounts=[account_config], clusters=[cluster])
        ConfigManager._config = config

        # Mock EKS client
        mock_eks_client = MagicMock()
        mock_eks_client.describe_cluster.return_value = {
            'cluster': {'status': 'ACTIVE', 'version': '1.28'}
        }

        with patch(
            'awslabs.eks_mcp_server.aws_helper.AwsHelper.create_boto3_client_for_cluster',
            return_value=mock_eks_client,
        ):
            result = await handler.list_eks_clusters(mock_context, validate=True)

        assert result.isError is False

        # Check JSON data includes status and version
        data_json = result.content[1].text
        data = json.loads(data_json)
        assert data['clusters'][0]['status'] == 'ACTIVE'
        assert data['clusters'][0]['version'] == '1.28'

    async def test_list_eks_clusters_validation_skipped_for_validated(self, handler, mock_context):
        """Test that validation is skipped for already validated clusters."""
        # Setup configuration with already validated cluster
        account_config = AccountConfig(
            account_id='123456789012', regions=['us-west-2'], profile='test-profile'
        )
        cluster = ClusterConfig(
            name='test-cluster',
            region='us-west-2',
            account_id='123456789012',
            description='Test cluster',
            validated=True,  # Already validated
        )
        config = ClustersConfig(accounts=[account_config], clusters=[cluster])
        ConfigManager._config = config

        # Mock EKS client (should not be called)
        mock_eks_client = MagicMock()

        with patch(
            'awslabs.eks_mcp_server.aws_helper.AwsHelper.create_boto3_client_for_cluster',
            return_value=mock_eks_client,
        ):
            result = await handler.list_eks_clusters(mock_context, validate=True)

        assert result.isError is False
        # Verify describe_cluster was not called
        mock_eks_client.describe_cluster.assert_not_called()

    async def test_list_eks_clusters_validation_error(self, handler, mock_context):
        """Test list_eks_clusters when validation fails."""
        # Setup configuration
        account_config = AccountConfig(
            account_id='123456789012', regions=['us-west-2'], profile='test-profile'
        )
        cluster = ClusterConfig(
            name='test-cluster',
            region='us-west-2',
            account_id='123456789012',
            description='Test cluster',
        )
        config = ClustersConfig(accounts=[account_config], clusters=[cluster])
        ConfigManager._config = config

        # Mock EKS client to raise an error
        mock_eks_client = MagicMock()
        mock_eks_client.describe_cluster.side_effect = Exception(
            'AccessDeniedException: User is not authorized to perform: eks:DescribeCluster'
        )

        with patch(
            'awslabs.eks_mcp_server.aws_helper.AwsHelper.create_boto3_client_for_cluster',
            return_value=mock_eks_client,
        ):
            result = await handler.list_eks_clusters(mock_context, validate=True)

        assert result.isError is False  # Still returns success with error in status

        # Check JSON data shows error in status
        data_json = result.content[1].text
        data = json.loads(data_json)
        assert 'AccessDeniedException' in data['clusters'][0]['status']

    async def test_list_eks_clusters_account_not_found(self, handler, mock_context):
        """Test list_eks_clusters when account is not found for a cluster."""
        # Setup configuration with one account, but cluster references different account
        account_config = AccountConfig(account_id='123456789012', regions=['us-west-2'])
        cluster = ClusterConfig(
            name='test-cluster',
            region='us-west-2',
            account_id='999999999999',  # Non-existent account
            description='Test cluster',
        )
        config = ClustersConfig(accounts=[account_config], clusters=[cluster])
        ConfigManager._config = config

        result = await handler.list_eks_clusters(mock_context, validate=False)

        assert result.isError is False

        # Check that no clusters are returned (account not found)
        data_json = result.content[1].text
        data = json.loads(data_json)
        assert data['count'] == 0

    async def test_list_eks_clusters_general_exception(self, handler, mock_context):
        """Test list_eks_clusters when a general exception occurs."""
        # Setup configuration
        account_config = AccountConfig(
            account_id='123456789012', regions=['us-west-2'], profile='test-profile'
        )
        config = ClustersConfig(accounts=[account_config])
        ConfigManager._config = config

        # Mock list_clusters to raise an exception
        with patch.object(ConfigManager, 'has_explicit_clusters', side_effect=Exception('Test error')):
            result = await handler.list_eks_clusters(mock_context, validate=False)

        assert result.isError is True
        assert 'Failed to list EKS clusters' in result.content[0].text
        assert 'Test error' in result.content[0].text

    async def test_list_eks_clusters_discovered_clusters(self, handler, mock_context):
        """Test list_eks_clusters with discovered clusters."""
        # Setup configuration with account but no explicit clusters
        account_config = AccountConfig(account_id='123456789012', regions=['us-west-2'])
        config = ClustersConfig(accounts=[account_config])
        ConfigManager._config = config

        # Add a discovered cluster
        cluster = ClusterConfig(
            name='discovered-cluster',
            region='us-west-2',
            account_id='123456789012',
            description='Auto-discovered',
            validated=True,
        )
        ConfigManager._discovered_clusters = [cluster]

        result = await handler.list_eks_clusters(mock_context, validate=False)

        assert result.isError is False

        # Check response text indicates discovered mode
        response_text = result.content[0].text
        assert 'Found 1 EKS clusters' in response_text
        assert 'discovered' in response_text

        # Check JSON data
        data_json = result.content[1].text
        data = json.loads(data_json)
        assert data['count'] == 1
        assert data['clusters'][0]['name'] == 'discovered-cluster'


class TestDiscoverClustersAtStartup:
    """Tests for the discover_clusters_at_startup method."""

    def test_discover_clusters_at_startup_with_errors(self):
        """Test discover_clusters_at_startup with some errors."""
        # Setup configuration with multiple accounts/regions
        account_config = AccountConfig(
            account_id='123456789012', regions=['us-west-2', 'us-east-1'], profile='test-profile'
        )
        config = ClustersConfig(accounts=[account_config])
        ConfigManager._config = config

        # Mock EKS client
        mock_eks_client_west = MagicMock()
        mock_eks_client_west.list_clusters.return_value = {'clusters': ['cluster-1', 'cluster-2']}

        mock_eks_client_east = MagicMock()
        mock_eks_client_east.list_clusters.side_effect = Exception('AccessDenied')

        def mock_create_client(account_id, region_name, service_name):
            if region_name == 'us-west-2':
                return mock_eks_client_west
            elif region_name == 'us-east-1':
                return mock_eks_client_east

        with patch(
            'awslabs.eks_mcp_server.aws_helper.AwsHelper.create_boto3_client_for_account_region',
            side_effect=mock_create_client,
        ):
            clusters = EKSDiscoveryHandler.discover_clusters_at_startup()

        # Should have 2 clusters from us-west-2
        assert len(clusters) == 2
        assert clusters[0].name == 'cluster-1'
        assert clusters[0].region == 'us-west-2'
        assert clusters[1].name == 'cluster-2'
        assert clusters[1].region == 'us-west-2'
