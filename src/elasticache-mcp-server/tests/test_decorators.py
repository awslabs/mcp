"""Tests for ElastiCache MCP Server decorators."""

import pytest
from awslabs.elasticache_mcp_server.common.decorators import handle_exceptions


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'test_case',
    [
        {
            'name': 'success_no_args',
            'func': lambda: {'success': True},
            'args': [],
            'kwargs': {},
            'expected': {'success': True},
        },
        {
            'name': 'error_no_args',
            'func': lambda: (_ for _ in ()).throw(ValueError('Test error')),
            'args': [],
            'kwargs': {},
            'expected': {'error': 'Test error'},
        },
        {
            'name': 'success_with_args',
            'func': lambda arg1, arg2: {'arg1': arg1, 'arg2': arg2},
            'args': ['test'],
            'kwargs': {'arg2': 'value'},
            'expected': {'arg1': 'test', 'arg2': 'value'},
        },
        {
            'name': 'error_with_args',
            'func': lambda arg1, arg2=None: (_ for _ in ()).throw(ValueError('arg2 is required'))
            if arg2 is None
            else None,
            'args': ['test'],
            'kwargs': {},
            'expected': {'error': 'arg2 is required'},
        },
    ],
)
async def test_handle_exceptions(test_case):
    """Test handle_exceptions decorator with various scenarios."""

    @handle_exceptions
    async def test_func(*args, **kwargs):
        return test_case['func'](*args, **kwargs)

    result = await test_func(*test_case['args'], **test_case['kwargs'])
    assert result == test_case['expected']
