# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for aggregate tool."""

import pytest
from awslabs.valkey_mcp_server.tools.search_aggregate import (
    _build_clause,
    _build_reducer,
    aggregate,
)
from glide_shared.commands.server_modules.ft_options.ft_aggregate_options import (
    FtAggregateApply,
    FtAggregateFilter,
    FtAggregateGroupBy,
    FtAggregateLimit,
    FtAggregateSortBy,
)
from glide_shared.exceptions import RequestError
from unittest.mock import AsyncMock, patch


pytestmark = pytest.mark.asyncio

MODULE = 'awslabs.valkey_mcp_server.tools.search_aggregate'


@pytest.fixture()
def mock_client():
    return AsyncMock()


@pytest.fixture(autouse=True)
def _patch(mock_client):
    with patch(f'{MODULE}.get_client', return_value=mock_client):
        yield


class TestBuildClause:
    def test_groupby(self):
        clause = _build_clause(
            {
                'type': 'GROUPBY',
                'fields': ['@category'],
                'reducers': [{'function': 'COUNT', 'alias': 'cnt'}],
            }
        )
        assert isinstance(clause, FtAggregateGroupBy)

    def test_sortby(self):
        clause = _build_clause(
            {
                'type': 'SORTBY',
                'fields': [{'field': '@cnt', 'order': 'DESC'}],
            }
        )
        assert isinstance(clause, FtAggregateSortBy)

    def test_apply(self):
        clause = _build_clause({'type': 'APPLY', 'expression': '@x * 2', 'alias': 'doubled'})
        assert isinstance(clause, FtAggregateApply)

    def test_apply_missing_fields(self):
        with pytest.raises(ValueError, match='expression'):
            _build_clause({'type': 'APPLY', 'alias': 'x'})

    def test_filter(self):
        clause = _build_clause({'type': 'FILTER', 'expression': '@cnt > 5'})
        assert isinstance(clause, FtAggregateFilter)

    def test_filter_missing_expression(self):
        with pytest.raises(ValueError, match='expression'):
            _build_clause({'type': 'FILTER'})

    def test_limit(self):
        clause = _build_clause({'type': 'LIMIT', 'offset': 0, 'count': 10})
        assert isinstance(clause, FtAggregateLimit)

    def test_unknown_type(self):
        with pytest.raises(ValueError, match='BOGUS'):
            _build_clause({'type': 'BOGUS'})


class TestBuildReducer:
    def test_count(self):
        r = _build_reducer({'function': 'COUNT', 'alias': 'cnt'})
        assert r.function == 'COUNT'
        assert r.name == 'cnt'

    def test_avg_with_field(self):
        r = _build_reducer({'function': 'AVG', 'field': '@price', 'alias': 'avg'})
        assert r.function == 'AVG'
        assert '@price' in r.args

    def test_invalid_function(self):
        with pytest.raises(ValueError, match='Unknown REDUCE'):
            _build_reducer({'function': 'BOGUS'})


class TestAggregate:
    async def test_basic_aggregate(self, mock_client):
        with patch(f'{MODULE}.ft') as mock_ft:
            mock_ft.aggregate = AsyncMock(
                return_value=[
                    {b'category': b'books', b'cnt': b'3'},
                    {b'category': b'electronics', b'cnt': b'2'},
                ]
            )
            result = await aggregate(
                index_name='idx',
                query='@price:[0 inf]',
                pipeline=[
                    {
                        'type': 'GROUPBY',
                        'fields': ['@category'],
                        'reducers': [{'function': 'COUNT', 'alias': 'cnt'}],
                    }
                ],
            )
        assert result['status'] == 'success'
        assert result['total'] == 2
        assert len(result['results']) == 2

    async def test_no_pipeline(self, mock_client):
        with patch(f'{MODULE}.ft') as mock_ft:
            mock_ft.aggregate = AsyncMock(return_value=[])
            result = await aggregate(index_name='idx', query='@f:[0 inf]')
        assert result['status'] == 'success'
        assert result['total'] == 0

    async def test_invalid_stage_type(self):
        result = await aggregate(
            index_name='idx', query='@f:[0 inf]', pipeline=[{'type': 'BOGUS'}]
        )
        assert result['status'] == 'error'
        assert 'BOGUS' in result['reason']

    async def test_command_error(self, mock_client):
        with patch(f'{MODULE}.ft') as mock_ft:
            mock_ft.aggregate = AsyncMock(side_effect=RequestError('bad'))
            result = await aggregate(index_name='idx', query='@f:[0 inf]')
        assert result['status'] == 'error'

    async def test_uses_load_all(self, mock_client):
        """Verify ft.aggregate is called with loadAll=True."""
        with patch(f'{MODULE}.ft') as mock_ft:
            mock_ft.aggregate = AsyncMock(return_value=[])
            await aggregate(
                index_name='idx',
                query='@price:[0 inf]',
                pipeline=[{'type': 'APPLY', 'expression': '@price * 1.1', 'alias': 'taxed'}],
            )
            call_kwargs = mock_ft.aggregate.call_args.kwargs
            assert call_kwargs['options'].loadAll is True
