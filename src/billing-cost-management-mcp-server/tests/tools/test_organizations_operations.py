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

"""Unit tests for the organizations_operations module."""

import boto3
import pytest
from awslabs.billing_cost_management_mcp_server.tools.organizations_operations import (
    describe_account,
    list_accounts,
)
from botocore.exceptions import ClientError
from botocore.stub import Stubber
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


CREATE_CLIENT_PATH = (
    'awslabs.billing_cost_management_mcp_server.tools.organizations_operations.create_aws_client'
)

JOINED = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
JOINED_ISO = '2024-01-15T12:00:00'

ACCOUNT = {
    'Id': '123456789012',
    'Arn': 'arn:aws:organizations::111111111111:account/o-exampleorgid/123456789012',
    'Email': 'linked-1@example.com',
    'Name': 'linked-1',
    'Status': 'ACTIVE',
    'JoinedMethod': 'INVITED',
    'JoinedTimestamp': JOINED,
}


@pytest.fixture
def mock_context():
    """Create a mock MCP context with async logging methods."""
    context = MagicMock()
    context.info = AsyncMock()
    context.warning = AsyncMock()
    context.error = AsyncMock()
    context.debug = AsyncMock()
    return context


def _client():
    """Return a real organizations client so the stub validates against the API model."""
    return boto3.Session(
        aws_access_key_id='a', aws_secret_access_key='b', region_name='us-east-1'
    ).client('organizations')


class TestListAccounts:
    """ListAccounts enumerates members and surfaces their join metadata."""

    @pytest.mark.asyncio
    async def test_default_page_size_is_the_api_maximum(self, mock_context):
        """The default page size is the API maximum (20) so the list arrives in fewer calls."""
        client = _client()
        stubber = Stubber(client)
        stubber.activate()
        stubber.add_response('list_accounts', {'Accounts': [ACCOUNT]}, {'MaxResults': 20})

        with patch(CREATE_CLIENT_PATH, return_value=client):
            result = await list_accounts(mock_context)

        stubber.assert_no_pending_responses()
        assert result['status'] == 'success'

    @pytest.mark.asyncio
    async def test_join_metadata_is_surfaced_and_timestamp_is_iso(self, mock_context):
        """JoinedMethod passes through and the datetime JoinedTimestamp becomes an ISO string."""
        client = _client()
        stubber = Stubber(client)
        stubber.activate()
        stubber.add_response('list_accounts', {'Accounts': [ACCOUNT]}, {'MaxResults': 20})

        with patch(CREATE_CLIENT_PATH, return_value=client):
            result = await list_accounts(mock_context)

        account = result['data']['accounts'][0]
        assert account['id'] == '123456789012'
        assert account['joined_method'] == 'INVITED'
        assert account['joined_timestamp'] == JOINED_ISO

    @pytest.mark.asyncio
    async def test_empty_organization_is_a_success_not_an_error(self, mock_context):
        """No rows is a real answer and must not be reported as a failure."""
        client = _client()
        stubber = Stubber(client)
        stubber.activate()
        stubber.add_response('list_accounts', {'Accounts': []}, {'MaxResults': 20})

        with patch(CREATE_CLIENT_PATH, return_value=client):
            result = await list_accounts(mock_context)

        assert result['status'] == 'success'
        assert result['data']['accounts'] == []

    @pytest.mark.asyncio
    async def test_pages_are_followed_with_the_next_token(self, mock_context):
        """A NextToken in the response drives a second request."""
        client = _client()
        stubber = Stubber(client)
        stubber.activate()
        stubber.add_response(
            'list_accounts',
            {'Accounts': [ACCOUNT], 'NextToken': 'page-2'},
            {'MaxResults': 20},
        )
        stubber.add_response(
            'list_accounts',
            {'Accounts': [{**ACCOUNT, 'Id': '222222222222'}]},
            {'MaxResults': 20, 'NextToken': 'page-2'},
        )

        with patch(CREATE_CLIENT_PATH, return_value=client):
            result = await list_accounts(mock_context)

        stubber.assert_no_pending_responses()
        assert len(result['data']['accounts']) == 2

    @pytest.mark.asyncio
    async def test_max_pages_stops_early_and_reports_more(self, mock_context):
        """Stopping at the page limit is reported rather than looking complete."""
        client = _client()
        stubber = Stubber(client)
        stubber.activate()
        stubber.add_response(
            'list_accounts',
            {'Accounts': [ACCOUNT], 'NextToken': 'page-2'},
            {'MaxResults': 20},
        )

        with patch(CREATE_CLIENT_PATH, return_value=client):
            result = await list_accounts(mock_context, max_pages=1)

        stubber.assert_no_pending_responses()
        assert result['data']['pagination']['has_more'] is True
        assert result['data']['pagination']['next_token'] == 'page-2'

    @pytest.mark.asyncio
    async def test_access_denied_is_surfaced_as_an_error(self, mock_context):
        """A denial (non-management caller) is reported as an error, never as no accounts."""
        error = ClientError(
            {
                'Error': {'Code': 'AccessDeniedException', 'Message': 'nope'},
                'ResponseMetadata': {'RequestId': 'req-1', 'HTTPStatusCode': 400},
            },
            'ListAccounts',
        )
        client = MagicMock()
        client.list_accounts.side_effect = error

        with patch(CREATE_CLIENT_PATH, return_value=client):
            result = await list_accounts(mock_context)

        assert result['status'] == 'error'
        assert result['error_type'] == 'AccessDeniedException'


class TestDescribeAccount:
    """DescribeAccount returns one account's join metadata."""

    @pytest.mark.asyncio
    async def test_account_id_is_sent_and_join_metadata_returned(self, mock_context):
        """The 12-digit AccountId is forwarded and the join metadata comes back formatted."""
        client = _client()
        stubber = Stubber(client)
        stubber.activate()
        stubber.add_response(
            'describe_account', {'Account': ACCOUNT}, {'AccountId': '123456789012'}
        )

        with patch(CREATE_CLIENT_PATH, return_value=client):
            result = await describe_account(mock_context, account_id='123456789012')

        stubber.assert_no_pending_responses()
        assert result['status'] == 'success'
        assert result['data']['account']['joined_timestamp'] == JOINED_ISO
        assert result['data']['account']['joined_method'] == 'INVITED'

    @pytest.mark.asyncio
    async def test_account_not_found_is_surfaced_as_an_error(self, mock_context):
        """A non-member account ID surfaces the service error, not an empty account."""
        error = ClientError(
            {
                'Error': {'Code': 'AccountNotFoundException', 'Message': 'unknown'},
                'ResponseMetadata': {'RequestId': 'req-2', 'HTTPStatusCode': 400},
            },
            'DescribeAccount',
        )
        client = MagicMock()
        client.describe_account.side_effect = error

        with patch(CREATE_CLIENT_PATH, return_value=client):
            result = await describe_account(mock_context, account_id='999999999999')

        assert result['status'] == 'error'
        assert result['error_type'] == 'AccountNotFoundException'
