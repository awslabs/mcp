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
"""Configuration for pytest."""

import pytest
import pytest_asyncio
from awslabs.aws_documentation_mcp_server.server_utils import get_http_client


async def _close_and_clear_http_client():
    """Close the cached httpx client (if any) and clear the cache."""
    if get_http_client.cache_info().currsize:
        client = get_http_client()
        aclose = getattr(client, 'aclose', None)
        if aclose and callable(aclose):
            try:
                await aclose()
            except TypeError:
                pass  # mock objects can't be awaited
    get_http_client.cache_clear()


@pytest_asyncio.fixture(autouse=True)
async def _reset_http_client_cache():
    """Reset the cached httpx client between tests."""
    await _close_and_clear_http_client()
    yield
    await _close_and_clear_http_client()


def pytest_addoption(parser):
    """Add command-line options to pytest."""
    parser.addoption(
        '--run-live',
        action='store_true',
        default=False,
        help='Run tests that make live API calls',
    )


def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line('markers', 'live: mark test as making live API calls')


def pytest_collection_modifyitems(config, items):
    """Skip live tests unless --run-live is specified."""
    if not config.getoption('--run-live'):
        skip_live = pytest.mark.skip(reason='need --run-live option to run')
        for item in items:
            if 'live' in item.keywords:
                item.add_marker(skip_live)
