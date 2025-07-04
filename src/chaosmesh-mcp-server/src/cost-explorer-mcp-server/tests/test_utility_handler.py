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

"""Simple tests for utility_handler module."""

import pytest
from awslabs.cost_explorer_mcp_server.utility_handler import get_today_date
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_get_today_date():
    """Test get_today_date returns current date in correct format."""
    with patch('awslabs.cost_explorer_mcp_server.utility_handler.datetime') as mock_dt:
        # Mock datetime to return fixed date
        mock_now = datetime(2025, 6, 20, 15, 30, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = mock_now

        ctx = MagicMock()
        result = await get_today_date(ctx)

        assert result == {'today_date_UTC': '2025-06-20', 'current_month': '2025-06'}
        mock_dt.now.assert_called_once_with(timezone.utc)


@pytest.mark.asyncio
async def test_get_today_date_real():
    """Test get_today_date with real datetime (integration test)."""
    ctx = MagicMock()
    result = await get_today_date(ctx)

    # Verify structure
    assert 'today_date_UTC' in result
    assert 'current_month' in result

    # Verify format (YYYY-MM-DD and YYYY-MM)
    assert len(result['today_date_UTC']) == 10
    assert len(result['current_month']) == 7
    assert result['today_date_UTC'].count('-') == 2
    assert result['current_month'].count('-') == 1
