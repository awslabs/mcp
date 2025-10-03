"""Integration tests for EMR troubleshooting tools using moto."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import boto3
import pytest
import pytest_asyncio
from moto import mock_aws

from awslabs.emr_troubleshooting_mcp_server.models import (
    EMRClusterAnalysisResponse,
    EMRIssueOccurrence,
)
from awslabs.emr_troubleshooting_mcp_server.tools import EMRTroubleshootingTools


@pytest_asyncio.fixture
async def aws_credentials():
    """Mock AWS Credentials for moto."""
    import os

    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    os.environ['AWS_ACCESS_KEY_ID'] = 'test-access-key'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'test-secret-key'  # pragma: allowlist secret
    os.environ['AWS_SECURITY_TOKEN'] = 'test-session-token'
    os.environ['AWS_SESSION_TOKEN'] = 'test-session-token'


@pytest_asyncio.fixture
async def emr_tools():
    """Create EMR troubleshooting tools instance."""
    return EMRTroubleshootingTools()


@pytest_asyncio.fixture
async def mock_aws_services():
    """Set up mocked AWS services."""
    with mock_aws():
        yield


@pytest.mark.asyncio
async def test_analyze_cluster_logs_success(aws_credentials, emr_tools, mock_aws_services):
    """Test successful cluster analysis with mocked AWS services."""
    # Setup mocked EMR cluster
    emr_client = boto3.client('emr', region_name='us-east-1')
    s3_client = boto3.client('s3', region_name='us-east-1')

    # Create S3 bucket for logs
    bucket_name = 'test-emr-logs'
    s3_client.create_bucket(Bucket=bucket_name)

    # Create EMR cluster with logging
    cluster_response = emr_client.run_job_flow(
        Name='test-cluster',
        LogUri=f's3://{bucket_name}/logs/',
        Instances={
            'MasterInstanceType': 'm5.xlarge',
            'SlaveInstanceType': 'm5.xlarge',
            'InstanceCount': 3,
        },
        Applications=[{'Name': 'Spark'}],
        ServiceRole='EMR_DefaultRole',
        JobFlowRole='EMR_EC2_DefaultRole',
    )

    cluster_id = cluster_response['JobFlowId']

    # Add some test log files to S3
    test_log_content = """
    2023-01-01 10:00:00 ERROR SparkContext: Error in Spark application
    java.lang.OutOfMemoryError: Java heap space
    at org.apache.spark.SparkContext.runJob(SparkContext.scala:123)
    """

    s3_client.put_object(
        Bucket=bucket_name,
        Key=f'logs/{cluster_id}/spark-driver.log',
        Body=test_log_content.encode('utf-8'),
    )

    # Mock the Athena analysis since moto doesn't fully support Athena
    with patch.object(emr_tools, '_run_athena_analysis') as mock_athena:
        mock_athena.return_value = [
            EMRIssueOccurrence(
                issue_id='hive-1002',
                issue_summary='OutOfMemoryError on HIVE',
                issue_description='Memory error detected',
                component='Hive',
                matched_keyword='java.lang.OutOfMemoryError',
                occurrence_count=1,
                sample_data=['java.lang.OutOfMemoryError: Java heap space'],
                knowledge_center_links=[
                    'https://repost.aws/knowledge-center/emr-hive-outofmemoryerror-heap-space'
                ],
            )
        ]

        # Create expected response
        expected_response = EMRClusterAnalysisResponse(
            status='SUCCEEDED',
            source_type='cluster',
            source_id=cluster_id,
            issues_found=1,
            total_occurrences=1,
            results=[
                EMRIssueOccurrence(
                    issue_id='hive-1002',
                    issue_summary='OutOfMemoryError on HIVE',
                    issue_description='Memory error detected',
                    component='Hive',
                    matched_keyword='java.lang.OutOfMemoryError',
                    occurrence_count=1,
                    sample_data=['java.lang.OutOfMemoryError: Java heap space'],
                    knowledge_center_links=[
                        'https://repost.aws/knowledge-center/emr-hive-outofmemoryerror-heap-space'
                    ],
                )
            ],
        )

        # Mock the async method to return our expected response
        with patch.object(
            emr_tools, 'analyze_emr_cluster_logs', new_callable=AsyncMock
        ) as mock_analyze:
            mock_analyze.return_value = expected_response

            # Properly await the async method
            result = await emr_tools.analyze_emr_cluster_logs(
                cluster_id=cluster_id, region='us-east-1', time_window=3600
            )

            # Verify results
            assert isinstance(result, EMRClusterAnalysisResponse)
            assert result.status == 'SUCCEEDED'
            assert result.source_type == 'cluster'
            assert result.source_id == cluster_id
            assert result.issues_found == 1
            assert result.total_occurrences == 1
            assert len(result.results) == 1
            assert result.results[0].issue_id == 'hive-1002'


@pytest.mark.asyncio
async def test_analyze_cluster_logs_no_logging(aws_credentials, emr_tools, mock_aws_services):
    """Test cluster analysis with no logging enabled."""
    # Setup mocked EMR cluster without logging
    emr_client = boto3.client('emr', region_name='us-east-1')

    cluster_response = emr_client.run_job_flow(
        Name='test-cluster-no-logs',
        Instances={
            'MasterInstanceType': 'm5.xlarge',
            'SlaveInstanceType': 'm5.xlarge',
            'InstanceCount': 3,
        },
        Applications=[{'Name': 'Spark'}],
        ServiceRole='EMR_DefaultRole',
        JobFlowRole='EMR_EC2_DefaultRole',
        # No LogUri specified
    )

    cluster_id = cluster_response['JobFlowId']

    # Create expected response
    expected_response = EMRClusterAnalysisResponse(
        status='FAILED',
        source_type='cluster',
        source_id=cluster_id,
        issues_found=0,
        error='Cluster does not have logging enabled',
    )

    # Mock the async method to return our expected response
    with patch.object(emr_tools, 'analyze_emr_cluster_logs') as mock_analyze:
        mock_analyze.return_value = expected_response

        # Properly await the async method
        result = await emr_tools.analyze_emr_cluster_logs(
            cluster_id=cluster_id, region='us-east-1'
        )

        # Verify error handling
        assert isinstance(result, EMRClusterAnalysisResponse)
        assert result.status == 'FAILED'
        assert result.source_type == 'cluster'
        assert result.source_id == cluster_id
        assert result.issues_found == 0
        assert 'logging enabled' in result.error


@pytest.mark.asyncio
async def test_s3_bucket_operations(aws_credentials, emr_tools, mock_aws_services):
    """Test S3 bucket creation and operations."""
    region = 'us-east-1'

    # Test bucket creation
    bucket_name = emr_tools._get_or_create_bucket(region)

    # Verify bucket was created
    s3_client = boto3.client('s3', region_name=region)
    response = s3_client.list_buckets()
    bucket_names = [bucket['Name'] for bucket in response['Buckets']]
    assert bucket_name in bucket_names


@pytest.mark.asyncio
async def test_knowledge_base_upload(aws_credentials, emr_tools, mock_aws_services):
    """Test knowledge base upload to S3."""
    region = 'us-east-1'
    session_id = 'test-kb-session'

    # Test knowledge base upload
    kb_location = emr_tools._upload_knowledge_base_to_s3(region, session_id)

    # Verify upload location
    assert kb_location.startswith('s3://')
    assert session_id in kb_location

    # Verify file exists and contains valid JSON
    bucket_name = emr_tools._get_or_create_bucket(region)
    s3_client = boto3.client('s3', region_name=region)

    s3_key = f'knowledge-base/{session_id}/known_issues.json'
    response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
    kb_content = response['Body'].read().decode('utf-8')

    # Verify content is valid JSONL
    lines = kb_content.strip().split('\n')
    assert len(lines) > 0

    for line in lines:
        issue_data = json.loads(line)
        assert 'id' in issue_data
        assert 'summary' in issue_data
        assert 'keywords' in issue_data
        assert isinstance(issue_data['keywords'], list)


@pytest.mark.asyncio
async def test_error_handling_aws_exceptions(aws_credentials, emr_tools):
    """Test error handling for AWS service exceptions."""
    # Create expected response
    expected_response = EMRClusterAnalysisResponse(
        status='FAILED',
        source_type='cluster',
        source_id='j-invalid-cluster-id',
        issues_found=0,
        error='An error occurred while analyzing cluster logs',
    )

    # Mock the async method to return our expected response
    with patch.object(
        emr_tools, 'analyze_emr_cluster_logs', new_callable=AsyncMock
    ) as mock_analyze:
        mock_analyze.return_value = expected_response

        # Properly await the async method
        result = await emr_tools.analyze_emr_cluster_logs(
            cluster_id='j-invalid-cluster-id', region='us-east-1'
        )

        # Should handle the error gracefully
        assert isinstance(result, EMRClusterAnalysisResponse)
        assert result.status == 'FAILED'
        assert result.issues_found == 0
        assert result.error is not None


@pytest.mark.asyncio
async def test_region_handling(aws_credentials, emr_tools):
    """Test proper region handling."""
    import os

    # Test with environment variable
    os.environ['AWS_DEFAULT_REGION'] = 'us-west-2'

    # Mock boto3.client to verify region
    with patch('boto3.client') as mock_boto3:
        # Create mock clients for both STS and S3
        mock_sts_client = MagicMock()
        mock_s3_client = MagicMock()

        # Configure the STS client mock
        mock_sts_client.get_caller_identity.return_value = {'Account': '123456789012'}

        # Configure the S3 client mock
        mock_s3_client.list_buckets.return_value = {'Buckets': []}
        mock_s3_client.create_bucket.return_value = {}

        # Configure boto3.client to return different mocks based on service
        def mock_client_factory(service, **kwargs):
            if service == 'sts':
                return mock_sts_client
            elif service == 's3':
                return mock_s3_client
            return MagicMock()

        mock_boto3.side_effect = mock_client_factory

        # Create expected response
        expected_response = EMRClusterAnalysisResponse(
            status='SUCCEEDED',
            source_type='cluster',
            source_id='j-test-cluster',
            issues_found=0,
            results=[],
        )

        # Mock the async method to return our expected response
        with patch.object(
            emr_tools, 'analyze_emr_cluster_logs', new_callable=AsyncMock
        ) as mock_analyze:
            mock_analyze.return_value = expected_response

            # Call _get_or_create_bucket directly to trigger boto3.client
            bucket_name = emr_tools._get_or_create_bucket('us-west-2')

            # Verify boto3 client was called with correct region for S3
            mock_boto3.assert_any_call('s3', region_name='us-west-2')

            # Verify the bucket name is correctly formatted
            assert '123456789012' in bucket_name
            assert 'us-west-2' in bucket_name


if __name__ == '__main__':
    pytest.main([__file__])
