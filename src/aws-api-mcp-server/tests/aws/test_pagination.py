import jmespath
from awslabs.aws_api_mcp_server.core.aws.pagination import build_result
from unittest.mock import MagicMock, Mock


def get_pages():
    """Return mock pages for paginated Lambda list functions."""
    lambda_list_functions_first_page = {
        'ResponseMetadata': {'HTTPStatusCode': 200},
        'Functions': [
            {
                'FunctionName': 'my-function-1',
                'FunctionArn': 'arn:aws:lambda:us-east-1:123456789012:function:my-function-1',
                'Runtime': 'nodejs20.x',
                'Role': 'arn:aws:iam::123456789012:role/some-role',
                'Handler': 'index.handler',
                'CodeSize': 194,
                'Description': '',
                'Timeout': 3,
                'MemorySize': 128,
                'LastModified': '2025-02-03T20:55:03.542+0000',
            }
        ],
        'NextToken': 'some-pagination-token',
    }

    lambda_list_functions_second_page = {
        'ResponseMetadata': {'HTTPStatusCode': 200},
        'Functions': [
            {
                'FunctionName': 'my-function-2',
                'FunctionArn': 'arn:aws:lambda:us-east-1:123456789012:function:my-function-2',
                'Runtime': 'nodejs20.x',
                'Role': 'arn:aws:iam::123456789012:role/some-role',
                'Handler': 'index.handler',
                'CodeSize': 194,
                'Description': '',
                'Timeout': 3,
                'MemorySize': 128,
                'LastModified': '2025-02-03T20:55:03.542+0000',
            }
        ],
    }

    return [lambda_list_functions_first_page, lambda_list_functions_second_page]


def test_build_result():
    """Test build_result combines paginated results correctly."""
    mock_paginator = Mock()
    mock_page_iter = MagicMock()

    mock_page_iter.__iter__.return_value = get_pages()
    mock_page_iter.result_keys = [jmespath.compile('Functions')]
    mock_paginator._pagination_cfg = {'output_token': 'NextToken'}
    mock_paginator.paginate.return_value = mock_page_iter

    result = build_result(
        paginator=mock_paginator,
        service_name='lambda',
        operation_name='ListFunctions',
        operation_parameters={},
        pagination_config={},
    )

    functions = result['Functions']

    assert len(functions) == 2
    assert functions[0].get('FunctionName') == 'my-function-1'
    assert functions[1].get('FunctionName') == 'my-function-2'
    assert (result.get('ResponseMetadata') or {}).get('HTTPStatusCode') == 200
    assert result.get('NextToken') is None


def test_build_result_with_client_side_filter():
    """Test build_result with MaxTokens on the first page and a client-side filter."""
    mock_paginator = Mock()
    mock_page_iter = MagicMock()

    mock_page_iter.__iter__.return_value = get_pages()
    mock_page_iter.result_keys = [jmespath.compile('Functions')]
    mock_page_iter.resume_token = None
    mock_paginator._pagination_cfg = {'output_token': 'NextToken'}
    mock_paginator.paginate.return_value = mock_page_iter

    result = build_result(
        paginator=mock_paginator,
        service_name='lambda',
        operation_name='ListFunctions',
        operation_parameters={},
        pagination_config={},
        client_side_filter=jmespath.compile('Functions[].FunctionName'),
    )

    assert result['Result'] == ['my-function-1', 'my-function-2']
    assert (result.get('ResponseMetadata') or {}).get('HTTPStatusCode') == 200
    assert result.get('pagination_token') is None


def test_build_result_with_max_results():
    """Test build_result with MaxItems in pagination config."""
    mock_paginator = Mock()
    mock_page_iter = MagicMock()

    mock_page_iter.__iter__.return_value = get_pages()
    mock_page_iter.result_keys = [jmespath.compile('Functions')]
    mock_page_iter.resume_token = None
    mock_paginator._pagination_cfg = {'output_token': 'NextToken'}
    mock_paginator.paginate.return_value = mock_page_iter

    result = build_result(
        paginator=mock_paginator,
        service_name='lambda',
        operation_name='ListFunctions',
        operation_parameters={},
        pagination_config={'MaxItems': 50},
    )

    functions = result['Functions']

    assert len(functions) == 2
    assert functions[0].get('FunctionName') == 'my-function-1'
    assert functions[1].get('FunctionName') == 'my-function-2'
    assert (result.get('ResponseMetadata') or {}).get('HTTPStatusCode') == 200
    assert result.get('pagination_token') is None
