import pytest
from awslabs.aws_mcp_server.core.metadata.read_only_operations_list import (
    READONLY_POLICY_ARN,
    ReadOnlyOperations,
    get_read_only_operations,
    get_readonly_policy_document,
)
from unittest.mock import MagicMock, patch


@pytest.fixture
def sample_policy_document():
    """Fixture providing a sample policy document."""
    return {
        'Statement': [
            {
                'Effect': 'Allow',
                'Action': [
                    'ec2:Describe*',
                    'ec2:Get*',
                    's3:Get*',
                    's3:List*',
                    'dynamodb:DescribeTable',
                    'lambda:GetFunction',
                ],
            },
            {
                'Effect': 'Allow',
                'Action': [
                    'cloudwatch:Describe*',
                    'cloudwatch:Get*',
                    'cloudwatch:List*',
                ],
            },
        ]
    }


@pytest.fixture
def sample_read_only_operations():
    """Fixture providing a sample ReadOnlyOperations instance."""
    operations = ReadOnlyOperations(policy_version='v1')
    operations['ec2'] = ['Describe*', 'Get*']
    operations['s3'] = ['Get*', 'List*']
    operations['dynamodb'] = ['DescribeTable']
    operations['lambda'] = ['GetFunction']
    operations['cloudwatch'] = ['Describe*', 'Get*', 'List*']
    return operations


def test_read_only_operations_initialization():
    """Test ReadOnlyOperations initialization and version retrieval."""
    operations = ReadOnlyOperations(policy_version='v1')

    assert operations.version == 'v1'
    assert isinstance(operations, dict)
    assert 'metadata' in operations
    assert operations['metadata']['policy_version'] == 'v1'


def test_read_only_operations_has_method(sample_read_only_operations):
    """Test the has method of ReadOnlyOperations."""
    operations = sample_read_only_operations

    # Test exact match
    assert operations.has('dynamodb', 'DescribeTable')
    assert operations.has('lambda', 'GetFunction')

    # Test wildcard match
    assert operations.has('ec2', 'DescribeInstances')
    assert operations.has('s3', 'GetObject')
    assert operations.has('cloudwatch', 'ListMetrics')

    # Test non-matching operation
    assert not operations.has('ec2', 'RunInstances')
    assert not operations.has('s3', 'PutObject')

    # Test non-existing service
    assert not operations.has('iam', 'GetRole')


def test_read_only_operations_has_method_with_action_as_asterik():
    """Test the has method return true if policy had a * for actions."""
    operations = ReadOnlyOperations(policy_version='v1')
    operations['*'] = ['*']
    assert operations.has('random-service', 'random-operation')


def test_read_only_operations_has_method_with_empty_service():
    """Test the has method when service is not in the operations dict."""
    operations = ReadOnlyOperations(policy_version='v1')
    assert operations.has('ec2', 'DescribeInstances') is False


@patch('boto3.client')
def test_get_readonly_policy_document(mock_boto3_client, sample_policy_document):
    """Test get_readonly_policy_document function."""
    # Setup mock responses
    mock_iam_client = MagicMock()
    mock_boto3_client.return_value = mock_iam_client

    mock_iam_client.get_policy.return_value = {'Policy': {'DefaultVersionId': 'v1'}}

    mock_iam_client.get_policy_version.return_value = {
        'PolicyVersion': {'Document': sample_policy_document}
    }

    # Call the function
    version, document = get_readonly_policy_document()

    # Verify the results
    assert version == 'v1'
    assert document == sample_policy_document

    # Verify the boto3 calls
    mock_boto3_client.assert_called_once_with('iam')
    mock_iam_client.get_policy.assert_called_once_with(PolicyArn=READONLY_POLICY_ARN)
    mock_iam_client.get_policy_version.assert_called_once_with(
        PolicyArn=READONLY_POLICY_ARN, VersionId='v1'
    )


@patch('boto3.client')
def test_get_readonly_policy_document_error(mock_boto3_client):
    """Test get_readonly_policy_document function when an error occurs."""
    # Setup mock to raise an exception
    mock_iam_client = MagicMock()
    mock_boto3_client.return_value = mock_iam_client
    mock_iam_client.get_policy.side_effect = Exception('Access denied')

    # Verify that the function raises a RuntimeError
    with pytest.raises(RuntimeError) as excinfo:
        get_readonly_policy_document()

    # Verify the error message
    assert 'Could not read ReadOnly operations from ReadOnly policy document' in str(excinfo.value)


@patch(
    'awslabs.aws_mcp_server.core.metadata.read_only_operations_list.get_readonly_policy_document'
)
def test_get_read_only_operations(mock_get_policy, sample_policy_document):
    """Test get_read_only_operations function."""
    # Setup mock response
    mock_get_policy.return_value = ('v1', sample_policy_document)

    # Call the function
    operations = get_read_only_operations()

    # Verify the result is a ReadOnlyOperations instance
    assert isinstance(operations, ReadOnlyOperations)
    assert operations.version == 'v1'

    # Verify the operations are correctly parsed from the policy document
    assert 'ec2' in operations
    assert 'Describe*' in operations['ec2']
    assert 'Get*' in operations['ec2']

    assert 's3' in operations
    assert 'Get*' in operations['s3']
    assert 'List*' in operations['s3']

    assert 'dynamodb' in operations
    assert 'DescribeTable' in operations['dynamodb']

    assert 'lambda' in operations
    assert 'GetFunction' in operations['lambda']

    assert 'cloudwatch' in operations
    assert 'Describe*' in operations['cloudwatch']
    assert 'Get*' in operations['cloudwatch']
    assert 'List*' in operations['cloudwatch']


@patch(
    'awslabs.aws_mcp_server.core.metadata.read_only_operations_list.get_readonly_policy_document'
)
def test_get_read_only_operations_with_asterik_as_action(mock_get_policy):
    """Test get_read_only_operation sets asterik for service when action is just asterik."""
    sample_policy_document = {
        'Statement': [
            {
                'Effect': 'Allow',
                'Action': [
                    'cloudwatch:Describe*',
                    'cloudwatch:Get*',
                    'cloudwatch:List*',
                ],
            },
            {
                'Effect': 'Allow',
                'Action': [
                    '*',
                ],
            },
        ]
    }

    mock_get_policy.return_value = ('v1', sample_policy_document)

    # Call the function
    operations = get_read_only_operations()

    assert operations.has('random-service', 'random-operation')
