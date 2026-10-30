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

"""Tests for how the compute-optimizer tool sends `account_ids` as `accountIds`.

The API takes a list of account ID strings. A bare ID such as 123456789012 is valid JSON
for a number, so it must be wrapped (and kept a string) rather than sent as an int.
"""

import pytest
from awslabs.billing_cost_management_mcp_server.tools import compute_optimizer_tools
from awslabs.billing_cost_management_mcp_server.tools.compute_optimizer_tools import (
    _build_request_params,
    get_ec2_instance_recommendations,
)
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    context = MagicMock()
    context.info = AsyncMock()
    context.error = AsyncMock()
    return context


def _build(account_ids):
    return _build_request_params(
        'get_ec2_instance_recommendations', None, account_ids, None, 'instanceArns'
    )


class TestAccountIdsParsing:
    """Shapes of account_ids and what is sent as accountIds."""

    @pytest.mark.parametrize(
        'account_ids,expected',
        [
            ('123456789012', ['123456789012']),
            (' 123456789012 ', ['123456789012']),
            ('012345678901', ['012345678901']),
            ('"123456789012"', ['123456789012']),
            ('[123456789012]', ['123456789012']),
            ('[12345678901]', ['12345678901']),
            ('[12345]', ['12345']),
            ('[-1]', ['-1']),
            ('["123456789012"]', ['123456789012']),
            ('[" 012345678901 "]', ['012345678901']),
            ('[]', []),
        ],
    )
    def test_account_ids_are_sent_as_a_list_of_strings(self, account_ids, expected):
        """A bare, quoted, or numeric ID is sent as a list of strings, digits unchanged."""
        params, error = _build(account_ids)

        assert error is None
        assert params['accountIds'] == expected

    @pytest.mark.parametrize(
        'account_ids',
        [
            '[111111111111, "222222222222"]',
            '111111111111,222222222222',
            '111111111111, 222222222222',
            '111111111111 222222222222',
        ],
    )
    def test_two_account_ids_get_the_one_per_request_error(self, account_ids):
        """Two IDs, as JSON or comma/space separated, are rejected before the call."""
        params, error = _build(account_ids)

        assert 'accountIds' not in params
        assert error is not None
        assert error['error_type'] == 'validation_error'
        assert error['data']['provided_account_ids'] == ['111111111111', '222222222222']

    @pytest.mark.parametrize(
        'account_ids', ['true', '1.5', 'null', '{"id": "123456789012"}', '[["123456789012"]]']
    )
    def test_non_id_account_ids_are_rejected(self, account_ids):
        """A value that is not an ID or a list of IDs is rejected before the call."""
        with pytest.raises(ValueError, match='account_ids'):
            _build(account_ids)


@pytest.mark.asyncio
class TestAccountIdsThroughTheTool:
    """account_ids end to end, through an operation and through the tool."""

    async def test_bare_account_id_reaches_the_client_as_a_string_list(self, mock_context):
        """The client gets accountIds=['<id>'] for a bare ID."""
        client = MagicMock()
        client.get_ec2_instance_recommendations.return_value = {'instanceRecommendations': []}

        result = await get_ec2_instance_recommendations(
            mock_context,
            client,
            max_items=1,
            filters=None,
            account_ids='123456789012',
            next_token=None,
        )

        assert result['status'] == 'success'
        sent = client.get_ec2_instance_recommendations.call_args[1]
        assert sent['accountIds'] == ['123456789012']

    async def test_tool_returns_validation_error_for_non_id(self, mock_context):
        """The tool returns a structured validation error instead of raising."""
        with (
            patch.object(compute_optimizer_tools, 'create_aws_client') as mock_create_client,
            patch.object(compute_optimizer_tools, 'get_context_logger') as mock_get_logger,
        ):
            mock_get_logger.return_value = AsyncMock()
            client = MagicMock()
            client.get_enrollment_status.return_value = {'status': 'Active'}
            mock_create_client.return_value = client

            result = await compute_optimizer_tools.compute_optimizer(
                mock_context, operation='get_ec2_instance_recommendations', account_ids='true'
            )

        assert result['status'] == 'error'
        assert result['error_type'] == 'validation_error'
        assert 'account_ids' in result['message']
        client.get_ec2_instance_recommendations.assert_not_called()
