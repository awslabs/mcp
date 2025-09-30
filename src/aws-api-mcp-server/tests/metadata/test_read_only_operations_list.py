import pytest
from awslabs.aws_api_mcp_server.core.metadata.read_only_operations_list import (
    DEFAULT_REQUEST_TIMEOUT,
    SERVICE_REFERENCE_URL,
    ReadOnlyOperations,
    ServiceReferenceUrlsByService,
)
from requests import Response
from unittest.mock import MagicMock, call, patch


TEST_SERVICE = 'testService'
TEST_URL = 'https://test-url.json'
TEST_READ_OPERATION = 'TestReadOperation'
TEST_READ_OPERATION_2 = 'TestReadOperation2'
TEST_WRITE_OPERATION = 'TestWriteOperation'


@pytest.fixture
def sample_service_reference_list_response():
    """Fixture providing a sample policy document."""
    return [{'service': TEST_SERVICE, 'url': TEST_URL}]


@pytest.fixture
def sample_service_reference_response():
    """Fixture providing a sample policy document."""
    return {
        'Name': TEST_SERVICE,
        'Actions': [
            {
                'Name': TEST_READ_OPERATION,
                'ActionConditionKeys': [],
                'Annotations': {
                    'Properties': {
                        'IsList': False,
                        'IsPermissionManagement': False,
                        'IsTaggingOnly': False,
                        'IsWrite': False,
                    }
                },
                'Resources': [{'Name': TEST_READ_OPERATION}],
            },
            {
                'Name': TEST_READ_OPERATION_2,
                'ActionConditionKeys': [],
                'Annotations': {
                    'Properties': {
                        'IsList': False,
                        'IsPermissionManagement': False,
                        'IsTaggingOnly': False,
                        'IsWrite': False,
                    }
                },
                'Resources': [{'Name': TEST_READ_OPERATION_2}],
            },
            {
                'Name': TEST_WRITE_OPERATION,
                'ActionConditionKeys': [],
                'Annotations': {
                    'Properties': {
                        'IsList': False,
                        'IsPermissionManagement': False,
                        'IsTaggingOnly': False,
                        'IsWrite': True,
                    }
                },
                'Resources': [{'Name': TEST_WRITE_OPERATION}],
            },
        ],
    }


@patch('requests.get')
def test_read_only_operations_initialization(
    mocked_requests_get, sample_service_reference_list_response
):
    """Test ReadOnlyOperations initialization."""
    mocked_service_reference_list_response = MagicMock(spec=Response)
    mocked_service_reference_list_response.json.return_value = (
        sample_service_reference_list_response
    )
    mocked_requests_get.return_value = mocked_service_reference_list_response

    operations = ReadOnlyOperations(ServiceReferenceUrlsByService())

    assert isinstance(operations, dict)
    mocked_requests_get.assert_called_once_with(
        SERVICE_REFERENCE_URL, timeout=DEFAULT_REQUEST_TIMEOUT
    )


@patch('requests.get')
def test_read_only_operations_has_method_missing_service(
    mocked_requests_get, sample_service_reference_list_response, sample_service_reference_response
):
    """Test the has method of ReadOnlyOperations when the provided service is missing."""
    mocked_service_reference_list_response = MagicMock(spec=Response)
    mocked_service_reference_list_response.json.return_value = (
        sample_service_reference_list_response
    )
    mocked_service_reference_response = MagicMock(spec=Response)
    mocked_service_reference_response.json.return_value = sample_service_reference_response
    mocked_requests_get.side_effect = [
        mocked_service_reference_list_response,
        mocked_service_reference_response,
    ]

    operations = ReadOnlyOperations(ServiceReferenceUrlsByService())

    assert isinstance(operations, dict)
    assert operations.has(TEST_SERVICE, TEST_READ_OPERATION)
    assert not operations.has(TEST_SERVICE, TEST_WRITE_OPERATION)
    mocked_requests_get.assert_has_calls(
        [
            call(SERVICE_REFERENCE_URL, timeout=DEFAULT_REQUEST_TIMEOUT),
            call(TEST_URL, timeout=DEFAULT_REQUEST_TIMEOUT),
        ],
        any_order=False,
    )


@patch('requests.get')
def test_read_only_operations_has_method_second_call_for_service_queries_local_cache(
    mocked_requests_get, sample_service_reference_list_response, sample_service_reference_response
):
    """Test the has method of ReadOnlyOperations when the provided service is available."""
    mocked_service_reference_list_response = MagicMock(spec=Response)
    mocked_service_reference_list_response.json.return_value = (
        sample_service_reference_list_response
    )
    mocked_service_reference_response = MagicMock(spec=Response)
    mocked_service_reference_response.json.return_value = sample_service_reference_response
    mocked_requests_get.side_effect = [
        mocked_service_reference_list_response,
        mocked_service_reference_response,
    ]

    operations = ReadOnlyOperations(ServiceReferenceUrlsByService())

    assert isinstance(operations, dict)
    # First call for a service, should get data from service reference API
    assert operations.has(TEST_SERVICE, TEST_READ_OPERATION)
    # Second call for the same service, should lookup data from local cache
    assert operations.has(TEST_SERVICE, TEST_READ_OPERATION_2)
    mocked_requests_get.assert_has_calls(
        [
            call(SERVICE_REFERENCE_URL, timeout=DEFAULT_REQUEST_TIMEOUT),
            call(TEST_URL, timeout=DEFAULT_REQUEST_TIMEOUT),
        ],
        any_order=False,
    )
    assert mocked_requests_get.call_count == 2


@patch('requests.get')
def test_read_only_operations_has_method_error(
    mocked_requests_get, sample_service_reference_list_response
):
    """Test the has method of ReadOnlyOperations when the service reference API call throws an error."""
    mocked_response = MagicMock(spec=Response)
    mocked_response.json.return_value = sample_service_reference_list_response
    mocked_requests_get.side_effect = [
        mocked_response,
        RuntimeError('Error while calling service reference API'),
    ]

    operations = ReadOnlyOperations(ServiceReferenceUrlsByService())

    assert isinstance(operations, dict)
    with pytest.raises(RuntimeError):
        operations.has(TEST_SERVICE, TEST_READ_OPERATION)
    mocked_requests_get.assert_has_calls(
        [
            call(SERVICE_REFERENCE_URL, timeout=DEFAULT_REQUEST_TIMEOUT),
            call(TEST_URL, timeout=DEFAULT_REQUEST_TIMEOUT),
        ],
        any_order=False,
    )


@patch('requests.get')
def test_service_reference_urls_by_service_error(mocked_requests_get):
    """Test ServiceReferenceUrlsByService initialization when the service reference API call throws an error."""
    mocked_requests_get.side_effect = RuntimeError('Error while calling service reference API')

    with pytest.raises(RuntimeError):
        ServiceReferenceUrlsByService()
    mocked_requests_get.assert_has_calls(
        [call(SERVICE_REFERENCE_URL, timeout=DEFAULT_REQUEST_TIMEOUT)], any_order=False
    )


def test_read_only_operations_has_method_custom_operation():
    """Test the has method of ReadOnlyOperations with custom operations."""
    operations = ReadOnlyOperations({})
    assert operations.has('s3', 'ls')
    assert operations.has('logs', 'start-live-tail')
    assert not operations.has('s3', 'sync')


def test_read_only_operations_has_method_operation_from_metadata():
    """Test the has method of ReadOnlyOperations with operations defined in api metadata."""
    operations = ReadOnlyOperations({})
    assert operations.has('s3', 'ListBuckets')
    assert operations.has('lambda', 'ListAliases')
    assert operations.has('rds', 'DescribeDBSnapshotAttributes')
    assert not operations.has('s3', 'DeleteObject')
    assert not operations.has('lambda', 'CreateAlias')
    assert not operations.has('rds', 'CreateDBSecurityGroup')


def test_read_only_operations_overrides():
    """Test the has method of ReadOnlyOperations with overrides."""
    operations = ReadOnlyOperations({})
    assert not operations.has('sts', 'AssumeRole')
    assert not operations.has('sts', 'AssumeRoleWithWebIdentity')
    assert not operations.has('sts', 'AssumeRoleWithSAML')
    assert not operations.has('sts', 'GetSessionToken')
    assert not operations.has('sts', 'GetFederationToken')
    assert not operations.has('sts', 'AssumeRoot')
    assert not operations.has('iam', 'CreateAccessKey')
    assert not operations.has('cognito-identity', 'GetCredentialsForIdentity')
    assert not operations.has('cognito-identity', 'GetOpenIdToken')
    assert not operations.has('sso', 'GetRoleCredentials')
