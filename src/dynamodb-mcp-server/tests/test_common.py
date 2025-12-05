import pytest
from awslabs.dynamodb_mcp_server.common import (
    is_delete_table_operation,
    is_dynamodb_local,
    validate_delete_table_operation,
)
from awslabs.dynamodb_mcp_server.server import execute_dynamodb_command
from hypothesis import given, settings
from hypothesis import strategies as st
from unittest.mock import patch


@settings(max_examples=100)
@given(
    local_indicator=st.sampled_from(['localhost', '127.0.0.1']),
    protocol=st.sampled_from(['http://', 'https://', '']),
    port=st.one_of(st.none(), st.integers(min_value=1, max_value=65535)),
    path=st.one_of(
        st.none(),
        st.text(alphabet=st.characters(whitelist_categories=('L', 'N')), min_size=0, max_size=20),
    ),
    case_variant=st.sampled_from(['lower', 'upper', 'mixed']),
)
@pytest.mark.hypothesis
def test_property_local_endpoint_detection_comprehensive(
    local_indicator, protocol, port, path, case_variant
):
    """Property 4: Local endpoint detection is comprehensive.

    For any URL string containing "localhost", "127.0.0.1", or "0.0.0.0" (case-insensitive),
    the endpoint classifier should return True indicating DynamoDB Local.

    Validates: Requirements 3.1, 3.2, 3.3
    """
    # Apply case variant to local indicator
    if case_variant == 'upper':
        local_indicator = local_indicator.upper()
    elif case_variant == 'mixed':
        # Mix case for localhost (e.g., "LocalHost", "LOCALHOST", "lOcAlHoSt")
        if local_indicator == 'localhost':
            local_indicator = ''.join(
                c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(local_indicator)
            )

    # Build URL with various components
    url_parts = [protocol, local_indicator]

    if port is not None:
        url_parts.append(f':{port}')

    if path:
        url_parts.append(f'/{path}')

    endpoint_url = ''.join(url_parts)

    # Property: Any URL containing localhost, 127.0.0.1, or 0.0.0.0 should be detected as local
    result = is_dynamodb_local(endpoint_url)

    assert result is True, (
        f"Expected is_dynamodb_local('{endpoint_url}') to return True "
        f"because it contains '{local_indicator}', but got False"
    )


@settings(max_examples=100)
@given(
    endpoint_type=st.sampled_from(['none', 'empty', 'aws_region']),
    region=st.sampled_from(
        ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1', 'ca-central-1']
    ),
    protocol=st.sampled_from(['http://', 'https://']),
    service_pattern=st.sampled_from(['dynamodb', 'dynamodb-fips']),
)
@pytest.mark.hypothesis
def test_property_aws_endpoint_detection_correct(endpoint_type, region, protocol, service_pattern):
    """Property 5: AWS endpoint detection is correct.

    For any URL string containing AWS region patterns or when endpoint is None/empty,
    the endpoint classifier should return False indicating AWS DynamoDB.

    Validates: Requirements 3.4, 3.5
    """
    if endpoint_type == 'none':
        endpoint_url = None
    elif endpoint_type == 'empty':
        endpoint_url = ''
    else:  # aws_region
        # Generate AWS DynamoDB endpoint URL
        endpoint_url = f'{protocol}{service_pattern}.{region}.amazonaws.com'

    # Property: None, empty, or AWS region endpoints should be detected as AWS (not local)
    result = is_dynamodb_local(endpoint_url)

    assert result is False, (
        f'Expected is_dynamodb_local({repr(endpoint_url)}) to return False '
        f'for AWS endpoint, but got True'
    )


@settings(max_examples=100)
@given(
    prefix=st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z')), min_size=0, max_size=50
    ),
    case_variant=st.sampled_from(['lower', 'upper', 'mixed', 'original']),
    suffix=st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z')), min_size=0, max_size=50
    ),
    spacing=st.sampled_from(['', ' ', '  ', '\t']),
)
@pytest.mark.hypothesis
def test_property_delete_table_operation_detection(prefix, case_variant, suffix, spacing):
    """Test delete-table operation detection with various formats."""
    # Apply case variant to "delete-table"
    delete_table_text = 'delete-table'
    if case_variant == 'upper':
        delete_table_text = delete_table_text.upper()
    elif case_variant == 'mixed':
        # Mix case (e.g., "DeLeTe-TaBlE", "DELETE-table")
        delete_table_text = ''.join(
            c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(delete_table_text)
        )
    # 'original' and 'lower' keep it as lowercase

    # Build command with delete-table in various positions and formats
    command = f'{prefix}{spacing}{delete_table_text}{spacing}{suffix}'

    # Property: Any command containing "delete-table" should be detected
    result = is_delete_table_operation(command)

    assert result is True, (
        f"Expected is_delete_table_operation('{command}') to return True "
        f"because it contains 'delete-table', but got False"
    )


@settings(max_examples=100)
@given(
    # Generate delete-table commands with various formats
    prefix=st.sampled_from(['aws dynamodb ', 'aws dynamodb  ', 'AWS DYNAMODB ']),
    delete_variant=st.sampled_from(['delete-table', 'DELETE-TABLE', 'Delete-Table']),
    table_param=st.sampled_from(
        [
            ' --table-name MyTable',
            ' --table-name TestTable',
            ' --table-name "my-table"',
            ' --table-name my_table_123',
        ]
    ),
    extra_params=st.sampled_from(['', ' --region us-east-1', ' --no-cli-pager']),
    # Generate non-local endpoints (None, empty, or AWS endpoints)
    endpoint_type=st.sampled_from(['none', 'empty', 'aws_region']),
    region=st.sampled_from(['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1']),
)
@pytest.mark.hypothesis
def test_property_delete_table_rejection_without_local_endpoint(
    prefix, delete_variant, table_param, extra_params, endpoint_type, region
):
    """Property 1: Delete-table without local endpoints is rejected.

    For any delete-table command and any non-local endpoint (None, empty, or AWS endpoint),
    the validation function should reject the operation and return an error.

    Validates: Requirements 1.1, 1.2
    """
    # Build delete-table command
    command = f'{prefix}{delete_variant}{table_param}{extra_params}'

    # Build non-local endpoint
    if endpoint_type == 'none':
        endpoint_url = None
    elif endpoint_type == 'empty':
        endpoint_url = ''
    else:  # aws_region
        endpoint_url = f'https://dynamodb.{region}.amazonaws.com'

    # Property: Delete-table operations without local endpoints should be rejected
    is_allowed, error_message = validate_delete_table_operation(command, endpoint_url)

    # Verify operation is blocked
    assert is_allowed is False, (
        f"Expected delete-table command '{command}' with endpoint '{endpoint_url}' "
        f'to be rejected, but it was allowed'
    )

    # Verify error message is provided
    assert error_message is not None, (
        'Expected error message when blocking delete-table, but got None'
    )

    # Verify error message contains key information
    assert 'delete-table' in error_message.lower(), (
        f"Error message should mention 'delete-table': {error_message}"
    )
    assert 'dynamodb local' in error_message.lower(), (
        f"Error message should mention 'DynamoDB Local': {error_message}"
    )


@settings(max_examples=100)
@given(
    # Generate delete-table commands with various formats
    prefix=st.sampled_from(['aws dynamodb ', 'aws dynamodb  ', 'AWS DYNAMODB ']),
    delete_variant=st.sampled_from(['delete-table', 'DELETE-TABLE', 'Delete-Table']),
    table_param=st.sampled_from(
        [
            ' --table-name MyTable',
            ' --table-name TestTable',
            ' --table-name "my-table"',
            ' --table-name my_table_123',
        ]
    ),
    extra_params=st.sampled_from(['', ' --region us-east-1', ' --no-cli-pager']),
    # Generate local endpoints
    local_indicator=st.sampled_from(['localhost', '127.0.0.1']),
    protocol=st.sampled_from(['http://', 'https://']),
    port=st.integers(min_value=1, max_value=65535),
    case_variant=st.sampled_from(['lower', 'upper', 'mixed']),
)
@pytest.mark.hypothesis
def test_property_delete_table_allowed_with_local_endpoint(
    prefix,
    delete_variant,
    table_param,
    extra_params,
    local_indicator,
    protocol,
    port,
    case_variant,
):
    """Test delete-table operations are allowed with local endpoints."""
    # Build delete-table command
    command = f'{prefix}{delete_variant}{table_param}{extra_params}'

    # Apply case variant to local indicator
    if case_variant == 'upper':
        local_indicator = local_indicator.upper()
    elif case_variant == 'mixed':
        # Mix case for localhost
        if local_indicator == 'localhost':
            local_indicator = ''.join(
                c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(local_indicator)
            )

    # Build local endpoint URL
    endpoint_url = f'{protocol}{local_indicator}:{port}'

    # Property: Delete-table operations with local endpoints should be allowed
    is_allowed, error_message = validate_delete_table_operation(command, endpoint_url)

    # Verify operation is allowed
    assert is_allowed is True, (
        f"Expected delete-table command '{command}' with local endpoint '{endpoint_url}' "
        f'to be allowed, but it was rejected with error: {error_message}'
    )

    # Verify no error message is provided when allowed
    assert error_message is None, (
        f'Expected no error message when allowing delete-table on local endpoint, '
        f'but got: {error_message}'
    )


@settings(max_examples=100)
@given(
    # Generate delete-table commands with various formats
    prefix=st.sampled_from(['aws dynamodb ', 'aws dynamodb  ', 'AWS DYNAMODB ']),
    delete_variant=st.sampled_from(['delete-table', 'DELETE-TABLE', 'Delete-Table']),
    table_param=st.sampled_from(
        [
            ' --table-name MyTable',
            ' --table-name TestTable',
            ' --table-name "my-table"',
            ' --table-name my_table_123',
        ]
    ),
    extra_params=st.sampled_from(['', ' --region us-east-1', ' --no-cli-pager']),
    # Generate non-local endpoints (None, empty, or AWS endpoints)
    endpoint_type=st.sampled_from(['none', 'empty', 'aws_region']),
    region=st.sampled_from(['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1']),
)
@pytest.mark.hypothesis
def test_property_error_message_completeness(
    prefix, delete_variant, table_param, extra_params, endpoint_type, region
):
    """Test error messages are complete and informative."""
    # Build delete-table command
    command = f'{prefix}{delete_variant}{table_param}{extra_params}'

    # Build non-local endpoint
    if endpoint_type == 'none':
        endpoint_url = None
    elif endpoint_type == 'empty':
        endpoint_url = ''
    else:  # aws_region
        endpoint_url = f'https://dynamodb.{region}.amazonaws.com'

    # Get validation result (should be blocked)
    is_allowed, error_message = validate_delete_table_operation(command, endpoint_url)

    # Verify operation is blocked (prerequisite for checking error message)
    assert is_allowed is False, (
        f"Expected delete-table to be blocked for endpoint '{endpoint_url}'"
    )

    # Verify error message exists
    assert error_message is not None, (
        'Expected error message when blocking delete-table, but got None'
    )

    # Convert to lowercase for case-insensitive checking
    error_lower = error_message.lower()

    has_local_requirement = 'dynamodb local' in error_lower and (
        'require' in error_lower or 'only' in error_lower or 'not allowed' in error_lower
    )

    assert has_local_requirement, (
        f'Error message should explain that delete-table requires DynamoDB Local. '
        f"Expected phrases like 'DynamoDB Local' with 'require'/'only'/'not allowed'. "
        f'Got: {error_message}'
    )

    has_endpoint_guidance = 'endpoint-url' in error_lower or 'endpoint url' in error_lower

    has_example_endpoint = 'localhost' in error_lower or '127.0.0.1' in error_lower

    assert has_endpoint_guidance, (
        f"Error message should mention 'endpoint-url' parameter. Got: {error_message}"
    )

    assert has_example_endpoint, (
        f'Error message should provide example endpoint (localhost or 127.0.0.1). '
        f'Got: {error_message}'
    )


@settings(max_examples=100)
@given(
    # Generate various non-delete-table DynamoDB operations
    operation=st.sampled_from(
        [
            'query',
            'scan',
            'put-item',
            'get-item',
            'delete-item',
            'update-item',
            'batch-get-item',
            'batch-write-item',
            'create-table',
            'describe-table',
            'list-tables',
            'update-table',
        ]
    ),
    prefix=st.sampled_from(['aws dynamodb ', 'aws dynamodb  ', 'AWS DYNAMODB ']),
    table_param=st.sampled_from(
        [
            ' --table-name MyTable',
            ' --table-name TestTable',
            ' --table-name "my-table"',
            ' --table-name my_table_123',
            '',  # Some operations like list-tables don't require table name
        ]
    ),
    extra_params=st.sampled_from(['', ' --region us-east-1', ' --no-cli-pager']),
    # Generate any endpoint (local or AWS or None)
    endpoint_type=st.sampled_from(['none', 'empty', 'aws_region', 'localhost', 'ip_local']),
    region=st.sampled_from(['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1']),
    port=st.integers(min_value=1, max_value=65535),
)
@pytest.mark.hypothesis
def test_property_non_delete_table_operations_unrestricted(
    operation, prefix, table_param, extra_params, endpoint_type, region, port
):
    """Test non-delete-table operations are unrestricted."""
    # Build non-delete-table command
    command = f'{prefix}{operation}{table_param}{extra_params}'

    # Build endpoint based on type
    if endpoint_type == 'none':
        endpoint_url = None
    elif endpoint_type == 'empty':
        endpoint_url = ''
    elif endpoint_type == 'aws_region':
        endpoint_url = f'https://dynamodb.{region}.amazonaws.com'
    elif endpoint_type == 'localhost':
        endpoint_url = f'http://localhost:{port}'
    else:  # ip_local
        endpoint_url = f'http://127.0.0.1:{port}'

    # Property: Non-delete-table operations should be allowed regardless of endpoint
    is_allowed, error_message = validate_delete_table_operation(command, endpoint_url)

    # Verify operation is allowed
    assert is_allowed is True, (
        f"Expected non-delete-table command '{command}' with endpoint '{endpoint_url}' "
        f'to be allowed, but it was rejected with error: {error_message}'
    )

    # Verify no error message is provided when allowed
    assert error_message is None, (
        f'Expected no error message when allowing non-delete-table operation, '
        f'but got: {error_message}'
    )


# Integration tests for delete-table validation
@pytest.mark.asyncio
async def test_delete_table_blocked_on_aws_no_endpoint():
    """Test delete-table blocked on AWS DynamoDB (no endpoint).

    Validates: Requirements 1.1, 2.1, 2.2
    """
    result = await execute_dynamodb_command(
        command='aws dynamodb delete-table --table-name MyTable', endpoint_url=None
    )

    # The @handle_exceptions decorator returns errors as {'error': str(e)}
    assert isinstance(result, dict)
    assert 'error' in result
    error_msg = result['error']
    assert 'Delete-table operation is not allowed on AWS DynamoDB' in error_msg
    assert 'Table deletion can only be executed against DynamoDB Local' in error_msg
    assert 'To use DynamoDB Local, provide an endpoint-url parameter' in error_msg
    assert '--endpoint-url http://localhost:8000' in error_msg
    assert 'Current endpoint: AWS DynamoDB (default)' in error_msg


@pytest.mark.asyncio
async def test_delete_table_blocked_on_aws_endpoint():
    """Test delete-table blocked on AWS endpoint.

    Validates: Requirements 1.2, 2.1, 2.2
    """
    aws_endpoint = 'https://dynamodb.us-east-1.amazonaws.com'
    result = await execute_dynamodb_command(
        command='aws dynamodb delete-table --table-name MyTable', endpoint_url=aws_endpoint
    )

    # The @handle_exceptions decorator returns errors as {'error': str(e)}
    assert isinstance(result, dict)
    assert 'error' in result
    error_msg = result['error']
    assert 'Delete-table operation is not allowed on AWS DynamoDB' in error_msg
    assert 'Table deletion can only be executed against DynamoDB Local' in error_msg
    assert 'To use DynamoDB Local, provide an endpoint-url parameter' in error_msg
    assert f'Current endpoint: {aws_endpoint}' in error_msg


@pytest.mark.asyncio
async def test_delete_table_allowed_on_localhost():
    """Test delete-table allowed on localhost endpoint.

    Validates: Requirements 1.3
    """
    with patch('awslabs.dynamodb_mcp_server.server.call_aws') as mock_call_aws:
        mock_call_aws.return_value = {'TableDescription': {'TableName': 'MyTable'}}

        result = await execute_dynamodb_command(
            command='aws dynamodb delete-table --table-name MyTable',
            endpoint_url='http://localhost:8000',
        )

        # Should execute successfully
        assert result == {'TableDescription': {'TableName': 'MyTable'}}
        mock_call_aws.assert_called_once()

        # Verify the command includes the endpoint
        args, kwargs = mock_call_aws.call_args
        assert 'delete-table' in args[0]
        assert '--endpoint-url http://localhost:8000' in args[0]


@pytest.mark.asyncio
async def test_non_delete_operations_allowed_everywhere():
    """Test non-delete-table operations allowed everywhere.

    Validates: Requirements 4.2
    """
    # Test query operation without endpoint (AWS)
    with patch('awslabs.dynamodb_mcp_server.server.call_aws') as mock_call_aws:
        mock_call_aws.return_value = {'Items': []}

        result = await execute_dynamodb_command(
            command='aws dynamodb query --table-name MyTable --key-condition-expression "id = :id"',
            endpoint_url=None,
        )

        assert result == {'Items': []}
        mock_call_aws.assert_called_once()

    # Test scan operation with AWS endpoint
    with patch('awslabs.dynamodb_mcp_server.server.call_aws') as mock_call_aws:
        mock_call_aws.return_value = {'Items': [], 'Count': 0}

        result = await execute_dynamodb_command(
            command='aws dynamodb scan --table-name MyTable',
            endpoint_url='https://dynamodb.us-west-2.amazonaws.com',
        )

        assert result == {'Items': [], 'Count': 0}
        mock_call_aws.assert_called_once()

    # Test put-item operation with localhost endpoint
    with patch('awslabs.dynamodb_mcp_server.server.call_aws') as mock_call_aws:
        mock_call_aws.return_value = {}

        result = await execute_dynamodb_command(
            command='aws dynamodb put-item --table-name MyTable --item \'{"id":{"S":"123"}}\'',
            endpoint_url='http://localhost:8000',
        )

        assert result == {}
        mock_call_aws.assert_called_once()


@pytest.mark.asyncio
async def test_error_message_format_and_content():
    """Test error message format and content for blocked operations.

    Validates: Requirements 2.1, 2.2
    """
    # Test with no endpoint
    result = await execute_dynamodb_command(
        command='aws dynamodb delete-table --table-name TestTable', endpoint_url=None
    )

    # The @handle_exceptions decorator returns errors as {'error': str(e)}
    assert isinstance(result, dict)
    assert 'error' in result
    error_msg = result['error']

    # Check all required components are present
    required_components = [
        'Delete-table operation is not allowed on AWS DynamoDB',
        'Table deletion can only be executed against DynamoDB Local',
        'To use DynamoDB Local, provide an endpoint-url parameter',
        '--endpoint-url http://localhost:8000',
        'Current endpoint: AWS DynamoDB (default)',
    ]

    for component in required_components:
        assert component in error_msg, f'Missing required component: {component}'

    # Test with AWS endpoint
    aws_endpoint = 'https://dynamodb.eu-west-1.amazonaws.com'
    result = await execute_dynamodb_command(
        command='aws dynamodb delete-table --table-name TestTable', endpoint_url=aws_endpoint
    )

    # The @handle_exceptions decorator returns errors as {'error': str(e)}
    assert isinstance(result, dict)
    assert 'error' in result
    error_msg = result['error']

    # Check endpoint is correctly displayed
    assert f'Current endpoint: {aws_endpoint}' in error_msg
