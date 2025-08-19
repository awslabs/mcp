"""Unit tests for CloudWatchLogSink."""

import pytest
from awslabs.aws_api_mcp_server.core.common.cloudwatch_logger import CloudWatchLogSink
from botocore.exceptions import ClientError
from unittest.mock import Mock, patch


@pytest.fixture
def mock_loguru():
    """Mock loguru logger."""
    with patch('awslabs.aws_api_mcp_server.core.common.cloudwatch_logger.logger') as mock_logger:
        yield mock_logger


@pytest.fixture
def mock_boto3_client():
    """Mock boto3 client for CloudWatch Logs."""
    with patch('awslabs.aws_api_mcp_server.core.common.cloudwatch_logger.boto3') as mock_boto3:
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        # Set up default return value for describe_log_streams
        mock_client.describe_log_streams.return_value = {'logStreams': []}
        yield mock_client


@pytest.fixture
def mock_credentials():
    """Mock AWS credentials."""
    from awslabs.aws_api_mcp_server.core.common.models import Credentials

    mock_creds = Credentials(
        access_key_id='test-access-key',  # pragma: allowlist secret
        secret_access_key='test-secret-key',  # pragma: allowlist secret
        session_token='test-session-token',  # pragma: allowlist secret
    )

    with patch(
        'awslabs.aws_api_mcp_server.core.common.cloudwatch_logger.get_local_credentials'
    ) as mock_get_creds:
        mock_get_creds.return_value = mock_creds
        yield mock_get_creds


@patch('time.time', return_value=1234567890)
def test_initialization(mock_time, mock_boto3_client, mock_loguru, mock_credentials):
    """Test CloudWatchLogSink initialization."""
    credentials = mock_credentials()
    mock_credentials.reset_mock()

    with patch('awslabs.aws_api_mcp_server.core.common.cloudwatch_logger.boto3') as mock_boto3:
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        mock_client.describe_log_streams.return_value = {'logStreams': []}

        sink = CloudWatchLogSink(log_group_name='/test/log-group', region_name='us-east-1')

    assert sink.log_group_name == '/test/log-group'
    assert sink.region_name == 'us-east-1'
    assert sink.log_stream_name == 'aws-api-mcp-server-1234567890'
    assert sink.sequence_token is None

    mock_boto3.client.assert_called_once_with(
        'logs',
        region_name='us-east-1',
        aws_access_key_id=credentials.access_key_id,
        aws_secret_access_key=credentials.secret_access_key,
        aws_session_token=credentials.session_token,
    )
    mock_credentials.assert_called_once()


@patch('time.time', return_value=1234567890)
def test_ensure_log_group_exists_already_exists(
    mock_time, mock_boto3_client, mock_loguru, mock_credentials
):
    """Test log group creation when it already exists."""
    with patch('awslabs.aws_api_mcp_server.core.common.cloudwatch_logger.boto3') as mock_boto3:
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        mock_client.describe_log_streams.return_value = {'logStreams': []}
        mock_client.create_log_group.side_effect = ClientError(
            {'Error': {'Code': 'ResourceAlreadyExistsException'}}, 'CreateLogGroup'
        )

        _ = CloudWatchLogSink(log_group_name='/test/log-group', region_name='us-east-1')

        mock_loguru.info.assert_called_once_with('Existing log group /test/log-group was found.')


@patch('time.time', return_value=1234567890)
def test_ensure_log_group_exists_access_denied(
    mock_time, mock_boto3_client, mock_loguru, mock_credentials
):
    """Test log group creation with access denied."""
    with patch('awslabs.aws_api_mcp_server.core.common.cloudwatch_logger.boto3') as mock_boto3:
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        mock_client.describe_log_streams.return_value = {'logStreams': []}
        mock_client.create_log_group.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException'}}, 'CreateLogGroup'
        )

        _ = CloudWatchLogSink(log_group_name='/test/log-group', region_name='us-east-1')

        mock_loguru.warning.assert_called_once_with(
            'Failed to create log group /test/log-group due to lack of permissions: AccessDeniedException'
        )


@patch('time.time', return_value=1234567890)
def test_ensure_log_group_exists_other_error(
    mock_time, mock_boto3_client, mock_loguru, mock_credentials
):
    """Test log group creation with other error."""
    with patch('awslabs.aws_api_mcp_server.core.common.cloudwatch_logger.boto3') as mock_boto3:
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        mock_client.describe_log_streams.return_value = {'logStreams': []}

        sink = CloudWatchLogSink(log_group_name='/test/log-group', region_name='us-east-1')

        mock_client.create_log_group.reset_mock()
        mock_client.create_log_group.side_effect = ClientError(
            {'Error': {'Code': 'ValidationException'}}, 'CreateLogGroup'
        )
        with pytest.raises(ClientError):
            sink._ensure_log_group_exists()


@patch('time.time', return_value=1234567890)
def test_ensure_log_stream_exists_success(mock_time, mock_boto3_client, mock_credentials):
    """Test successful log stream creation."""
    with patch('awslabs.aws_api_mcp_server.core.common.cloudwatch_logger.boto3') as mock_boto3:
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        mock_client.describe_log_streams.return_value = {'logStreams': []}

        _ = CloudWatchLogSink(log_group_name='/test/log-group', region_name='us-east-1')

        mock_client.create_log_stream.assert_called_once_with(
            logGroupName='/test/log-group', logStreamName='aws-api-mcp-server-1234567890'
        )


@patch('time.time', return_value=1234567890)
def test_ensure_log_stream_exists_already_exists(
    mock_time, mock_boto3_client, mock_loguru, mock_credentials
):
    """Test log stream creation when it already exists."""
    with patch('awslabs.aws_api_mcp_server.core.common.cloudwatch_logger.boto3') as mock_boto3:
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        mock_client.describe_log_streams.return_value = {'logStreams': []}
        mock_client.create_log_stream.side_effect = ClientError(
            {'Error': {'Code': 'ResourceAlreadyExistsException'}}, 'CreateLogStream'
        )

        _ = CloudWatchLogSink(log_group_name='/test/log-group', region_name='us-east-1')

        mock_loguru.debug.assert_called_once_with(
            'Existing log stream aws-api-mcp-server-1234567890 was found.'
        )


@patch('time.time', return_value=1234567890)
def test_ensure_log_stream_exists_access_denied(
    mock_time, mock_boto3_client, mock_loguru, mock_credentials
):
    """Test log stream creation with access denied."""
    with patch('awslabs.aws_api_mcp_server.core.common.cloudwatch_logger.boto3') as mock_boto3:
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        mock_client.describe_log_streams.return_value = {'logStreams': []}
        mock_client.create_log_stream.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException'}}, 'CreateLogStream'
        )

        _ = CloudWatchLogSink(log_group_name='/test/log-group', region_name='us-east-1')

        mock_loguru.warning.assert_called_once_with(
            'Failed to create log stream aws-api-mcp-server-1234567890 due to lack of permissions: AccessDeniedException'
        )


@patch('time.time', return_value=1234567890)
def test_refresh_sequence_token_success(mock_time, mock_boto3_client, mock_credentials):
    """Test successful sequence token refresh."""
    with patch('awslabs.aws_api_mcp_server.core.common.cloudwatch_logger.boto3') as mock_boto3:
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        mock_client.describe_log_streams.return_value = {
            'logStreams': [{'uploadSequenceToken': 'test-token'}]
        }
        mock_client.describe_log_streams.return_value = {
            'logStreams': [{'uploadSequenceToken': 'test-token'}]
        }

        sink = CloudWatchLogSink(log_group_name='/test/log-group', region_name='us-east-1')
        assert sink.sequence_token == 'test-token'
        mock_client.describe_log_streams.assert_called_once()


@patch('time.time', return_value=1234567890)
def test_write_success(mock_time, mock_boto3_client, mock_credentials):
    """Test successful log message writing."""
    with patch('awslabs.aws_api_mcp_server.core.common.cloudwatch_logger.boto3') as mock_boto3:
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        mock_client.describe_log_streams.return_value = {'logStreams': []}

        sink = CloudWatchLogSink(log_group_name='/test/log-group', region_name='us-east-1')

        with patch('time.time', return_value=1234567890.123):
            sink.write('Test log message')

        mock_client.put_log_events.assert_called_once_with(
            logGroupName='/test/log-group',
            logStreamName='aws-api-mcp-server-1234567890',
            logEvents=[{'timestamp': 1234567890123, 'message': 'Test log message'}],
        )


@patch('time.time', return_value=1234567890)
def test_write_with_sequence_token(mock_time, mock_boto3_client, mock_credentials):
    """Test writing with sequence token."""
    with patch('awslabs.aws_api_mcp_server.core.common.cloudwatch_logger.boto3') as mock_boto3:
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        mock_client.describe_log_streams.return_value = {'logStreams': []}

        sink = CloudWatchLogSink(log_group_name='/test/log-group', region_name='us-east-1')

        sink.sequence_token = 'test-token'

        with patch('time.time', return_value=1234567890.123):
            sink.write('Test log message')

        mock_client.put_log_events.assert_called_once_with(
            logGroupName='/test/log-group',
            logStreamName='aws-api-mcp-server-1234567890',
            logEvents=[{'timestamp': 1234567890123, 'message': 'Test log message'}],
            sequenceToken='test-token',
        )


@patch('time.time', return_value=1234567890)
def test_write_invalid_sequence_token_retry(mock_time, mock_boto3_client, mock_credentials):
    """Test writing with invalid sequence token and retry."""
    with patch('awslabs.aws_api_mcp_server.core.common.cloudwatch_logger.boto3') as mock_boto3:
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        mock_client.describe_log_streams.return_value = {'logStreams': []}

        sink = CloudWatchLogSink(log_group_name='/test/log-group', region_name='us-east-1')

        sink.sequence_token = 'invalid-token'

        # First call fails with InvalidSequenceTokenException
        mock_client.put_log_events.side_effect = [
            ClientError({'Error': {'Code': 'InvalidSequenceTokenException'}}, 'PutLogEvents'),
            {'nextSequenceToken': 'new-token'},  # Second call succeeds
        ]

        with patch.object(sink, '_refresh_sequence_token'):
            sink.sequence_token = 'refreshed-token'

            with patch('time.time', return_value=1234567890.123):
                sink.write('Test log message')

        assert sink.sequence_token == 'new-token'
        assert mock_client.put_log_events.call_count == 2


@patch('time.time', return_value=1234567890)
def test_write_data_already_accepted(mock_time, mock_boto3_client, mock_credentials):
    """Test writing when data is already accepted."""
    with patch('awslabs.aws_api_mcp_server.core.common.cloudwatch_logger.boto3') as mock_boto3:
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        mock_client.describe_log_streams.return_value = {'logStreams': []}

        sink = CloudWatchLogSink(log_group_name='/test/log-group', region_name='us-east-1')

        sink.sequence_token = 'test-token'

        mock_client.put_log_events.side_effect = ClientError(
            {'Error': {'Code': 'DataAlreadyAcceptedException'}}, 'PutLogEvents'
        )

        with patch.object(sink, '_refresh_sequence_token') as mock_refresh:
            with patch('time.time', return_value=1234567890.123):
                sink.write('Test log message')

        mock_refresh.assert_called_once()


@patch('time.time', return_value=1234567890)
def test_write_other_error(mock_time, mock_boto3_client, mock_credentials):
    """Test writing with other error."""
    with patch('awslabs.aws_api_mcp_server.core.common.cloudwatch_logger.boto3') as mock_boto3:
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        mock_client.describe_log_streams.return_value = {'logStreams': []}

        sink = CloudWatchLogSink(log_group_name='/test/log-group', region_name='us-east-1')

        mock_client.put_log_events.side_effect = ClientError(
            {'Error': {'Code': 'ServiceUnavailableException'}}, 'PutLogEvents'
        )

        with patch('time.time', return_value=1234567890.123):
            with pytest.raises(ClientError):
                sink.write('Test log message')


@patch('time.time', return_value=1234567890)
def test_thread_safety(mock_time, mock_boto3_client, mock_credentials):
    """Test thread safety of the sink."""
    import queue
    import threading

    with patch('awslabs.aws_api_mcp_server.core.common.cloudwatch_logger.boto3') as mock_boto3:
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client
        mock_client.describe_log_streams.return_value = {'logStreams': []}

        sink = CloudWatchLogSink(log_group_name='/test/log-group', region_name='us-east-1')

    results = queue.Queue()

    def write_message(msg):
        try:
            sink.write(msg)
            results.put(('success', msg))
        except Exception as e:
            results.put(('error', str(e)))

    # Create multiple threads writing simultaneously
    threads = []
    for i in range(5):
        thread = threading.Thread(target=write_message, args=(f'Message {i}',))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Check that all writes were successful
    for _ in range(5):
        status, msg = results.get()
        assert status == 'success'

    # Verify that put_log_events was called 5 times
    assert mock_client.put_log_events.call_count == 5
