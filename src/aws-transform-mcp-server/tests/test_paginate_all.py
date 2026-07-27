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

"""Tests for paginate_all helper."""
# ruff: noqa: D101, D102, D103

import pytest
from awslabs.aws_transform_mcp_server.transform_api_client import paginate_all
from unittest.mock import AsyncMock, patch


_MOD = 'awslabs.aws_transform_mcp_server.transform_api_client'


class TestPaginateAll:
    @pytest.mark.asyncio
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    async def test_single_page(self, mock_fes):
        mock_fes.return_value = {'agents': [{'name': 'a1'}]}
        result = await paginate_all('ListAgents', {}, 'agents')
        assert result == {'agents': [{'name': 'a1'}]}
        assert mock_fes.call_count == 1

    @pytest.mark.asyncio
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    async def test_multiple_pages(self, mock_fes):
        mock_fes.side_effect = [
            {'agents': [{'name': 'a1'}], 'nextToken': 'tok1'},
            {'agents': [{'name': 'a2'}], 'nextToken': 'tok2'},
            {'agents': [{'name': 'a3'}]},
        ]
        result = await paginate_all('ListAgents', {}, 'agents')
        assert result == {'agents': [{'name': 'a1'}, {'name': 'a2'}, {'name': 'a3'}]}
        assert mock_fes.call_count == 3
        assert mock_fes.call_args_list[1][0][1]['nextToken'] == 'tok1'
        assert mock_fes.call_args_list[2][0][1]['nextToken'] == 'tok2'

    @pytest.mark.asyncio
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    async def test_empty_response(self, mock_fes):
        mock_fes.return_value = {'agents': []}
        result = await paginate_all('ListAgents', {}, 'agents')
        assert result == {'agents': []}

    @pytest.mark.asyncio
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    async def test_custom_token_key(self, mock_fes):
        mock_fes.side_effect = [
            {'worklogs': [{'id': 'w1'}], 'outputToken': 'tok1'},
            {'worklogs': [{'id': 'w2'}]},
        ]
        result = await paginate_all('ListWorklogs', {}, 'worklogs', token_key='outputToken')
        assert result == {'worklogs': [{'id': 'w1'}, {'id': 'w2'}]}
        assert mock_fes.call_count == 2

    @pytest.mark.asyncio
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    async def test_does_not_mutate_body(self, mock_fes):
        mock_fes.side_effect = [
            {'agents': [{'name': 'a1'}], 'nextToken': 'tok1'},
            {'agents': [{'name': 'a2'}]},
        ]
        body = {'agentFilter': {'agentTypeFilter': {'agentType': 'ORCHESTRATOR_AGENT'}}}
        await paginate_all('ListAgents', body, 'agents')
        assert 'nextToken' not in body

    @pytest.mark.asyncio
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    async def test_non_dict_response_stops_first_page(self, mock_fes):
        mock_fes.return_value = None
        result = await paginate_all('ListAgents', {}, 'agents')
        assert result == {'agents': []}

    @pytest.mark.asyncio
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    async def test_non_dict_response_returns_partial_on_later_page(self, mock_fes):
        mock_fes.side_effect = [
            {'agents': [{'name': 'a1'}], 'nextToken': 'tok1'},
            None,
        ]
        result = await paginate_all('ListAgents', {}, 'agents')
        assert result == {'agents': [{'name': 'a1'}]}

    @pytest.mark.asyncio
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    async def test_exception_on_page_two_propagates(self, mock_fes):
        mock_fes.side_effect = [
            {'agents': [{'name': 'a1'}], 'nextToken': 'tok1'},
            RuntimeError('FES unavailable'),
        ]
        with pytest.raises(RuntimeError, match='FES unavailable'):
            await paginate_all('ListAgents', {}, 'agents')

    @pytest.mark.asyncio
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    async def test_hits_max_pages_safety_limit(self, mock_fes):
        mock_fes.return_value = {'agents': [{'name': 'a'}], 'nextToken': 'always'}
        result = await paginate_all('ListAgents', {}, 'agents')
        from awslabs.aws_transform_mcp_server.transform_api_client import _MAX_PAGES

        assert len(result['agents']) == _MAX_PAGES
        assert mock_fes.call_count == _MAX_PAGES

    # ── extra_list_keys / scalar_keys (ListArtifacts-shaped responses) ────

    @pytest.mark.asyncio
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    async def test_extra_list_keys_aggregated_across_pages(self, mock_fes):
        mock_fes.side_effect = [
            {
                'artifacts': [{'id': 'a1'}],
                'folders': ['f1/'],
                'assets': [{'assetKey': 'k1'}],
                'nextToken': 'tok1',
            },
            {
                'artifacts': [{'id': 'a2'}],
                'folders': ['f2/'],
                'assets': [{'assetKey': 'k2'}],
            },
        ]
        result = await paginate_all(
            'ListArtifacts',
            {},
            'artifacts',
            extra_list_keys=('folders', 'assets'),
        )
        assert result['artifacts'] == [{'id': 'a1'}, {'id': 'a2'}]
        assert result['folders'] == ['f1/', 'f2/']
        assert result['assets'] == [{'assetKey': 'k1'}, {'assetKey': 'k2'}]

    @pytest.mark.asyncio
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    async def test_extra_list_keys_missing_on_some_pages_are_treated_as_empty(self, mock_fes):
        mock_fes.side_effect = [
            {'artifacts': [{'id': 'a1'}], 'folders': ['f1/'], 'nextToken': 'tok'},
            {'artifacts': [{'id': 'a2'}]},  # no folders/assets on page 2
        ]
        result = await paginate_all(
            'ListArtifacts',
            {},
            'artifacts',
            extra_list_keys=('folders', 'assets'),
        )
        assert result['folders'] == ['f1/']
        assert result['assets'] == []

    @pytest.mark.asyncio
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    async def test_scalar_keys_taken_from_first_page_only(self, mock_fes):
        mock_fes.side_effect = [
            {'artifacts': [{'id': 'a1'}], 'connectorId': 'conn-A', 'nextToken': 'tok'},
            {'artifacts': [{'id': 'a2'}], 'connectorId': 'conn-B'},  # ignored
        ]
        result = await paginate_all(
            'ListArtifacts',
            {},
            'artifacts',
            scalar_keys=('connectorId',),
        )
        assert result['connectorId'] == 'conn-A'

    @pytest.mark.asyncio
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    async def test_scalar_keys_absent_when_not_in_response(self, mock_fes):
        mock_fes.return_value = {'artifacts': []}  # no connectorId at all
        result = await paginate_all(
            'ListArtifacts',
            {},
            'artifacts',
            scalar_keys=('connectorId',),
        )
        assert 'connectorId' not in result

    @pytest.mark.asyncio
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    async def test_scalar_keys_null_value_skipped(self, mock_fes):
        mock_fes.return_value = {'artifacts': [], 'connectorId': None}
        result = await paginate_all(
            'ListArtifacts',
            {},
            'artifacts',
            scalar_keys=('connectorId',),
        )
        assert 'connectorId' not in result

    @pytest.mark.asyncio
    @patch(f'{_MOD}.call_transform_api', new_callable=AsyncMock)
    async def test_backward_compatible_shape_without_extras(self, mock_fes):
        """No extras / scalars → output shape matches the pre-change contract."""
        mock_fes.return_value = {'agents': [{'name': 'a1'}]}
        result = await paginate_all('ListAgents', {}, 'agents')
        assert result == {'agents': [{'name': 'a1'}]}
        assert '_truncated' not in result
