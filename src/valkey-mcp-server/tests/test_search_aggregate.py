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
    _build_apply,
    _build_filter,
    _build_groupby,
    _build_limit,
    _build_sortby,
    aggregate,
)
from unittest.mock import AsyncMock, patch


pytestmark = pytest.mark.asyncio

MODULE = 'awslabs.valkey_mcp_server.tools.search_aggregate'


@pytest.fixture()
def mock_client():
    return AsyncMock()


@pytest.fixture(autouse=True)
def _patch_client(mock_client):
    with (
        patch(f'{MODULE}.get_client', return_value=mock_client),
        patch(f'{MODULE}.index_exists', AsyncMock(return_value=True)),
    ):
        yield


class TestPipelineBuilders:
    def test_groupby_count(self):
        args = _build_groupby(
            {
                'fields': ['@category'],
                'reducers': [{'function': 'COUNT', 'alias': 'cnt'}],
            }
        )
        assert args == ['GROUPBY', '1', '@category', 'REDUCE', 'COUNT', '0', 'AS', 'cnt']

    def test_groupby_avg(self):
        args = _build_groupby(
            {
                'fields': ['@cat'],
                'reducers': [{'function': 'AVG', 'field': '@price', 'alias': 'avg'}],
            }
        )
        assert 'REDUCE' in args
        assert 'AVG' in args
        assert '@price' in args

    def test_groupby_invalid_reducer(self):
        with pytest.raises(ValueError, match='Unknown REDUCE'):
            _build_groupby(
                {
                    'fields': ['@x'],
                    'reducers': [{'function': 'BOGUS'}],
                }
            )

    def test_sortby_dict_fields(self):
        args = _build_sortby(
            {
                'fields': [{'field': '@cnt', 'order': 'DESC'}],
            }
        )
        assert args == ['SORTBY', '2', '@cnt', 'DESC']

    def test_sortby_string_fields(self):
        args = _build_sortby({'fields': ['@name']})
        assert args == ['SORTBY', '2', '@name', 'ASC']

    def test_apply(self):
        assert _build_apply({'expression': '@x * 2', 'alias': 'doubled'}) == [
            'APPLY',
            '@x * 2',
            'AS',
            'doubled',
        ]

    def test_apply_missing_fields(self):
        with pytest.raises(ValueError, match='expression'):
            _build_apply({'alias': 'x'})

    def test_filter(self):
        assert _build_filter({'expression': '@cnt > 5'}) == ['FILTER', '@cnt > 5']

    def test_filter_missing_expression(self):
        with pytest.raises(ValueError, match='expression'):
            _build_filter({})

    def test_limit(self):
        assert _build_limit({'offset': 0, 'count': 10}) == ['LIMIT', '0', '10']

    def test_limit_defaults(self):
        assert _build_limit({}) == ['LIMIT', '0', '10']


class TestAggregate:
    async def test_basic_aggregate(self, mock_client):
        mock_client.custom_command = AsyncMock(
            return_value=[
                {b'category': b'books', b'cnt': b'3'},
                {b'category': b'electronics', b'cnt': b'2'},
            ]
        )
        result = await aggregate(
            index_name='idx',
            query='@f:[0 inf]',
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
        mock_client.custom_command = AsyncMock(return_value=[])
        result = await aggregate(
            index_name='idx',
            query='@f:[0 inf]',
        )
        assert result['status'] == 'success'
        assert result['total'] == 0

    async def test_invalid_stage_type(self):
        result = await aggregate(
            index_name='idx', query='@f:[0 inf]', pipeline=[{'type': 'BOGUS'}]
        )
        assert result['status'] == 'error'
        assert 'BOGUS' in result['reason']

    async def test_apply_and_limit(self, mock_client):
        mock_client.custom_command = AsyncMock(return_value=[{b'val': b'42'}])
        result = await aggregate(
            index_name='idx',
            query='@f:[0 inf]',
            pipeline=[
                {
                    'type': 'GROUPBY',
                    'fields': ['@x'],
                    'reducers': [{'function': 'SUM', 'field': '@v', 'alias': 'val'}],
                },
                {'type': 'APPLY', 'expression': '@val * 2', 'alias': 'doubled'},
                {'type': 'LIMIT', 'offset': 0, 'count': 1},
            ],
        )
        assert result['status'] == 'success'
        cmd = mock_client.custom_command.call_args[0][0]
        assert 'APPLY' in cmd
        assert 'LIMIT' in cmd

    async def test_command_error(self, mock_client):
        from glide_shared.exceptions import RequestError

        mock_client.custom_command = AsyncMock(side_effect=RequestError('bad'))
        result = await aggregate(
            index_name='idx',
        )
        assert result['status'] == 'error'

    async def test_load_includes_groupby_fields(self, mock_client):
        mock_client.custom_command = AsyncMock(return_value=[])
        await aggregate(
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
        cmd = mock_client.custom_command.call_args[0][0]
        load_idx = cmd.index('LOAD')
        load_fields = cmd[load_idx + 2 : cmd.index('GROUPBY')]
        assert '@category' in load_fields

    async def test_load_includes_reducer_fields(self, mock_client):
        mock_client.custom_command = AsyncMock(return_value=[])
        await aggregate(
            index_name='idx',
            query='@price:[0 inf]',
            pipeline=[
                {
                    'type': 'GROUPBY',
                    'fields': ['@cat'],
                    'reducers': [{'function': 'AVG', 'field': '@price', 'alias': 'avg'}],
                }
            ],
        )
        cmd = mock_client.custom_command.call_args[0][0]
        assert '@price' in cmd
        assert '@cat' in cmd

    async def test_load_includes_apply_fields(self, mock_client):
        mock_client.custom_command = AsyncMock(return_value=[])
        await aggregate(
            index_name='idx',
            query='@price:[0 inf]',
            pipeline=[{'type': 'APPLY', 'expression': '@price * 1.1', 'alias': 'taxed'}],
        )
        cmd = mock_client.custom_command.call_args[0][0]
        assert '@price' in cmd

    async def test_load_includes_filter_fields(self, mock_client):
        mock_client.custom_command = AsyncMock(return_value=[])
        await aggregate(
            index_name='idx',
            query='@price:[0 inf]',
            pipeline=[{'type': 'FILTER', 'expression': '@price > 50'}],
        )
        cmd = mock_client.custom_command.call_args[0][0]
        assert '@price' in cmd

    async def test_load_skips_pipeline_aliases(self, mock_client):
        mock_client.custom_command = AsyncMock(return_value=[])
        await aggregate(
            index_name='idx',
            query='@price:[0 inf]',
            pipeline=[
                {
                    'type': 'GROUPBY',
                    'fields': ['@cat'],
                    'reducers': [{'function': 'AVG', 'field': '@price', 'alias': 'avg_price'}],
                },
                {'type': 'APPLY', 'expression': '@avg_price * 1.1', 'alias': 'taxed'},
            ],
        )
        cmd = mock_client.custom_command.call_args[0][0]
        load_idx = cmd.index('LOAD')
        load_count = int(cmd[load_idx + 1])
        load_fields = cmd[load_idx + 2 : load_idx + 2 + load_count]
        assert '@avg_price' not in load_fields

    async def test_load_includes_sortby_fields(self, mock_client):
        mock_client.custom_command = AsyncMock(return_value=[])
        await aggregate(
            index_name='idx',
            query='@price:[0 inf]',
            pipeline=[
                {'type': 'SORTBY', 'fields': [{'field': '@price', 'order': 'DESC'}]},
            ],
        )
        cmd = mock_client.custom_command.call_args[0][0]
        assert '@price' in cmd

    async def test_wildcard_query_rejected(self):
        result = await aggregate(index_name='idx', query='*')
        assert result['status'] == 'error'
        assert 'not supported' in result['reason']
