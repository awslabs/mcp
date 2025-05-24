"""Tests for the ECR utility module."""

import boto3
import pytest_asyncio
from awslabs.finch_mcp_server.consts import STATUS_ERROR, STATUS_SUCCESS
from awslabs.finch_mcp_server.utils.ecr import create_ecr_repository
from botocore.exceptions import ClientError
from moto import mock_aws
from unittest.mock import patch


@pytest_asyncio.fixture
async def aws_credentials():
    """Mock AWS Credentials for moto."""
    import os

    os.environ['AWS_DEFAULT_REGION'] = 'us-west-2'


@pytest_asyncio.fixture
async def ecr_client(aws_credentials):
    """ECR client."""
    with mock_aws():
        yield boto3.client('ecr', region_name='us-west-2')


class TestCreateEcrRepository:
    """Tests for the create_ecr_repository function."""

    def test_repository_already_exists(self, ecr_client):
        """Test handling of existing repository."""
        region = 'us-west-2'
        app_name = 'test-repo'
        ecr_client.create_repository(
            repositoryName=app_name,
            imageScanningConfiguration={'scanOnPush': True},
            imageTagMutability='IMMUTABLE',
        )

        result = create_ecr_repository(
            app_name=app_name,
            region=region,
        )

        assert result['status'] == STATUS_SUCCESS
        assert 'already exists' in result['message']

    def test_repository_creation_success(self, ecr_client):
        """Test successful repository creation."""
        region = 'us-west-2'
        app_name = 'test-repo'

        result = create_ecr_repository(
            app_name=app_name,
            region=region,
        )

        assert result['status'] == STATUS_SUCCESS
        assert 'Successfully created' in result['message']

        response = ecr_client.describe_repositories(repositoryNames=[app_name])
        assert len(response['repositories']) == 1
        assert response['repositories'][0]['repositoryName'] == app_name

    @patch('boto3.client')
    def test_describe_error_not_repository_not_found(self, mock_boto3_client, ecr_client):
        """Test handling of describe error that is not RepositoryNotFoundException."""
        mock_ecr_client = mock_boto3_client.return_value
        error_response = {
            'Error': {'Code': 'AccessDeniedException', 'Message': 'User is not authorized'}
        }
        mock_ecr_client.describe_repositories.side_effect = ClientError(
            error_response, 'DescribeRepositories'
        )

        result = create_ecr_repository(app_name='test-repo', region='us-west-2')

        assert result['status'] == STATUS_ERROR
        assert 'Error checking ECR repository' in result['message']

    @patch('boto3.client')
    def test_create_repository_failure(self, mock_boto3_client, ecr_client):
        """Test handling of repository creation failure."""
        mock_ecr_client = mock_boto3_client.return_value

        describe_error = {
            'Error': {
                'Code': 'RepositoryNotFoundException',
                'Message': "The repository with name 'test-repo' does not exist",
            }
        }
        mock_ecr_client.describe_repositories.side_effect = ClientError(
            describe_error, 'DescribeRepositories'
        )

        create_error = {
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': 'User is not authorized to create repository',
            }
        }
        mock_ecr_client.create_repository.side_effect = ClientError(
            create_error, 'CreateRepository'
        )

        result = create_ecr_repository(app_name='test-repo', region='us-west-2')

        assert result['status'] == STATUS_ERROR
        assert 'Failed to create ECR repository' in result['message']
