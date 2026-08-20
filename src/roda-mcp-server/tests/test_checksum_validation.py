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

"""Tests for checksum validation in fetch_datasets().

fetch_datasets() downloads the NDJSON registry file and a separate SHA-256
checksum file, then validates integrity before parsing. If the checksum doesn't
match, it retries up to 2 times (to handle brief CDN propagation windows where
the data and checksum are momentarily out of sync).

These tests mock the HTTP layer (no network calls) and verify:
1. Happy path: checksum matches on first try → datasets returned.
2. Failure path: checksum never matches after all retries → raises ChecksumValidationError.
3. Unavailable path: checksum file fetch fails (e.g., 404) → exception propagates.

Run: uv run python -m pytest tests/test_checksum_validation.py -v
"""

import awslabs.roda_mcp_server.server as server_module
import hashlib
import pytest
from awslabs.roda_mcp_server.server import ChecksumValidationError, fetch_datasets
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the dataset cache before and after each test.

    Without this, a successful test would populate the cache, and subsequent
    tests would return cached data without ever hitting the mocked HTTP layer.
    """
    server_module._datasets_cache = None
    server_module._cache_timestamp = None
    yield
    server_module._datasets_cache = None
    server_module._cache_timestamp = None


@pytest.mark.asyncio
async def test_checksum_validation_success():
    """Checksum matches on first attempt — datasets are parsed and returned."""
    # Create sample content and compute its real SHA-256
    ndjson_content = '{"Slug": "test-dataset", "Name": "Test Dataset"}\n'
    content_bytes = ndjson_content.encode('utf-8')
    expected_checksum = hashlib.sha256(content_bytes).hexdigest()

    # Mock the NDJSON download response
    mock_ndjson_response = MagicMock()
    mock_ndjson_response.content = content_bytes
    mock_ndjson_response.text = ndjson_content
    mock_ndjson_response.raise_for_status = MagicMock()

    # Mock the checksum file response (matches the content)
    mock_checksum_response = MagicMock()
    mock_checksum_response.text = f'{expected_checksum}  index.ndjson\n'
    mock_checksum_response.raise_for_status = MagicMock()

    # Patch where httpx is looked up (in the server module, not the httpx package)
    with patch('awslabs.roda_mcp_server.server.httpx.AsyncClient') as mock_client:
        mock_get = AsyncMock(side_effect=[mock_ndjson_response, mock_checksum_response])
        mock_client.return_value.__aenter__.return_value.get = mock_get

        datasets = await fetch_datasets()

        assert len(datasets) == 1
        assert datasets[0]['Slug'] == 'test-dataset'


@pytest.mark.asyncio
async def test_checksum_validation_failure():
    """Checksum never matches after all retries — raises ChecksumValidationError.

    The implementation retries up to 2 times (3 total attempts), sleeping 3s
    between each. We mock asyncio.sleep so the test doesn't actually wait.
    Each attempt makes 2 HTTP calls (NDJSON + checksum), so we need 6 mocked responses.
    """
    ndjson_content = '{"Slug": "test-dataset", "Name": "Test Dataset"}\n'
    content_bytes = ndjson_content.encode('utf-8')
    wrong_checksum = '0' * 64  # Will never match the real SHA-256

    mock_ndjson_response = MagicMock()
    mock_ndjson_response.content = content_bytes
    mock_ndjson_response.text = ndjson_content
    mock_ndjson_response.raise_for_status = MagicMock()

    mock_checksum_response = MagicMock()
    mock_checksum_response.text = f'{wrong_checksum}  index.ndjson\n'
    mock_checksum_response.raise_for_status = MagicMock()

    with patch('awslabs.roda_mcp_server.server.httpx.AsyncClient') as mock_client:
        # 3 attempts × 2 calls each = 6 mock responses
        mock_get = AsyncMock(
            side_effect=[
                mock_ndjson_response,
                mock_checksum_response,  # attempt 1
                mock_ndjson_response,
                mock_checksum_response,  # attempt 2 (retry)
                mock_ndjson_response,
                mock_checksum_response,  # attempt 3 (retry)
            ]
        )
        mock_client.return_value.__aenter__.return_value.get = mock_get

        # Patch sleep so the test doesn't wait 3s between retries
        with patch('asyncio.sleep', new_callable=AsyncMock):
            with pytest.raises(ChecksumValidationError) as exc_info:
                await fetch_datasets()

        assert 'Checksum validation failed' in str(exc_info.value)
        assert wrong_checksum in str(exc_info.value)


@pytest.mark.asyncio
async def test_checksum_unavailable_raises_exception():
    """Checksum file fetch fails (e.g., 404) — retries are exhausted then error propagates.

    Network and HTTP errors are now retried. If all attempts fail, the last
    error is re-raised to the caller.
    """
    import httpx as real_httpx

    ndjson_content = '{"Slug": "test-dataset", "Name": "Test Dataset"}\n'
    content_bytes = ndjson_content.encode('utf-8')

    # NDJSON download succeeds
    mock_ndjson_response = MagicMock()
    mock_ndjson_response.content = content_bytes
    mock_ndjson_response.text = ndjson_content
    mock_ndjson_response.raise_for_status = MagicMock()

    # Checksum fetch fails with HTTP 404
    http_error = real_httpx.HTTPStatusError(
        '404 Not Found',
        request=MagicMock(),
        response=MagicMock(status_code=404),
    )
    mock_checksum_response = MagicMock()
    mock_checksum_response.raise_for_status = MagicMock(side_effect=http_error)

    with patch('awslabs.roda_mcp_server.server.httpx.AsyncClient') as mock_client:
        # 3 attempts: each attempt fetches NDJSON successfully then fails on checksum
        mock_get = AsyncMock(
            side_effect=[
                mock_ndjson_response,
                mock_checksum_response,  # attempt 1
                mock_ndjson_response,
                mock_checksum_response,  # attempt 2
                mock_ndjson_response,
                mock_checksum_response,  # attempt 3
            ]
        )
        mock_client.return_value.__aenter__.return_value.get = mock_get

        with patch('asyncio.sleep', new_callable=AsyncMock):
            with pytest.raises(real_httpx.HTTPStatusError):
                await fetch_datasets()
