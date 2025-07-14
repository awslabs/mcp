import pytest
from awslabs.aws_api_mcp_server.core.aws.services import (
    extract_pagination_config,
)


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
