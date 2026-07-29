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

"""Tests for generic regional fan-out utilities."""

import base64
import pytest
from awslabs.billing_cost_management_mcp_server.utilities.regional_fanout import (
    RegionalTokenError,
    collect_regional_pages,
    decode_regional_next_token,
    encode_regional_next_token,
    fan_out_regions,
    is_regional_next_token,
)
from botocore.exceptions import ClientError
from unittest.mock import AsyncMock, MagicMock


async def test_fan_out_regions_collects_ordered_outcomes():
    """Successes and errors preserve the caller's region order."""
    ctx = MagicMock()
    ctx.error = AsyncMock()

    async def worker(region, state):
        if state == 'miss':
            raise LookupError(region)
        if state == 'error':
            raise RuntimeError(region)
        return state.upper()

    result = await fan_out_regions(
        {'us-east-1': 'ok', 'us-west-2': 'miss', 'eu-west-1': 'error'},
        worker,
        ctx=ctx,
        operation='get_resource',
        service_name='Test Service',
        max_concurrency=2,
    )

    assert result.successes == {'us-east-1': 'OK'}
    assert list(result.errors) == ['us-west-2', 'eu-west-1']
    assert result.errors['us-west-2']['error_type'] == 'unknown_lookuperror'
    assert result.errors['eu-west-1']['error_type'] == 'unknown_runtimeerror'


async def test_fan_out_regions_rejects_invalid_concurrency():
    """A zero-sized semaphore is rejected rather than hanging."""
    ctx = MagicMock()

    async def worker(region, state):
        return state

    with pytest.raises(ValueError, match='at least 1'):
        await fan_out_regions(
            {'us-east-1': None},
            worker,
            ctx=ctx,
            operation='get_resource',
            service_name='Test Service',
            max_concurrency=0,
        )


async def test_collect_regional_pages_merges_items_tokens_and_outcomes():
    """Regional pages are merged, stamped, and retain every regional error."""
    ctx = MagicMock()
    ctx.error = AsyncMock()

    async def worker(region, state):
        if state == 'not_found':
            raise ClientError(
                {'Error': {'Code': 'ResourceNotFoundException', 'Message': region}},
                'ListResources',
            )
        if state == 'error':
            raise RuntimeError(region)
        if state == 'more':
            return [{'id': 'one', 'region': ''}], 'service-token'
        return [{'id': 'two', 'region': 'source-region'}], None

    result = await collect_regional_pages(
        {
            'us-east-1': 'more',
            'us-west-2': 'done',
            'eu-west-1': 'not_found',
            'ap-south-1': 'error',
        },
        worker,
        ctx=ctx,
        operation='list_resources',
        service_name='Test Service',
        max_concurrency=2,
    )

    assert result.items == [
        {'id': 'one', 'region': 'us-east-1'},
        {'id': 'two', 'region': 'us-west-2'},
    ]
    assert result.next_tokens == {'us-east-1': 'service-token'}
    assert result.successful_regions == ['us-east-1', 'us-west-2']
    assert result.errors['eu-west-1']['error_type'] == 'ResourceNotFoundException'
    assert result.errors['ap-south-1']['error_type'] == 'unknown_runtimeerror'
    assert result.errors['ap-south-1']['message'] == 'ap-south-1'


def test_regional_next_token_round_trip():
    """Regional token maps round-trip and omission initializes every region."""
    regions = ['us-east-1', 'us-west-2']
    token = encode_regional_next_token({'us-west-2': 'service-token'})

    assert decode_regional_next_token(token, regions) == {'us-west-2': 'service-token'}
    assert decode_regional_next_token(None, regions) == {
        'us-east-1': None,
        'us-west-2': None,
    }


def test_regional_next_token_rejects_unsupported_region():
    """Decoded state cannot resume a region outside the caller's allowlist."""
    token = encode_regional_next_token({'moon-1': 'service-token'})

    with pytest.raises(RegionalTokenError) as exc_info:
        decode_regional_next_token(token, ['us-east-1'])

    assert exc_info.value.reason == 'unsupported_regions'
    assert exc_info.value.details['regions'] == ['moon-1']


@pytest.mark.parametrize(
    ('token', 'expected'),
    [
        (encode_regional_next_token({'moon-1': 'service-token'}), True),
        (None, False),
        ('', False),
        ('native-service-token', False),
        (base64.b64encode(b'["not-a-map"]').decode(), False),
        (base64.b64encode(b'{}').decode(), False),
        (base64.b64encode(b'{"us-east-1": ""}').decode(), False),
    ],
)
def test_is_regional_next_token(token, expected):
    """Regional tokens are recognized without knowing which regions are expected."""
    assert is_regional_next_token(token) is expected
