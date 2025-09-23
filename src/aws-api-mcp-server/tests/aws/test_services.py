import pytest
from awslabs.aws_api_mcp_server.core.aws.services import (
    extract_pagination_config,
    session,
)
from unittest.mock import patch


MAX_RESULTS = 6


@pytest.mark.parametrize(
    'max_result_config, max_result_param, expected_max_result',
    [
        (None, None, None),  # max result is not defined
        (10, None, 10),  # max result is defined in config but not as param
        (None, 6, 6),  # max result is defined as parameter and not in config
        (6, 10, 6),  # max result is defined in both places. In this case we take config param
    ],
)
def test_max_results(max_result_config, max_result_param, expected_max_result):
    """Test that max results are set correctly based on config and parameters."""
    parameters = {
        'PaginationConfig': {'MaxItems': max_result_config},
        'Foo': 'Bar',
    }
    updated_parameters, pagination_config = extract_pagination_config(parameters, max_result_param)
    max_results = pagination_config.get('MaxItems')
    assert max_results == expected_max_result
    assert updated_parameters.get('PaginationConfig') is None


@patch('os.environ.get')
@patch('botocore.httpsession.URLLib3Session.send')
def test_session_user_agent_in_boto_request(mock_send, mock_env):
    """Test that boto requests include the MCP user agent."""
    mock_env.side_effect = lambda key, default=None: {
        'AWS_ACCESS_KEY_ID': 'test',  # pragma: allowlist secret
        'AWS_SECRET_ACCESS_KEY': 'test',  # pragma: allowlist secret
    }.get(key, default)

    mock_response = type(
        'MockResponse',
        (),
        {
            'status_code': 200,
            'headers': {},
            'content': b'<GetCallerIdentityResponse><GetCallerIdentityResult></GetCallerIdentityResult></GetCallerIdentityResponse>',
        },
    )()
    mock_send.return_value = mock_response

    client = session.create_client('sts', region_name='us-east-1')
    client.get_caller_identity()

    user_agent = mock_send.call_args[0][0].headers.get('User-Agent', b'').decode()
    assert 'awslabs/mcp/AWS-API-MCP-server' in user_agent
    assert 'cli-customizations' in user_agent
