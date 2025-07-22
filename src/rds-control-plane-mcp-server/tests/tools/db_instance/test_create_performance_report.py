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

"""Tests for create_performance_report tool."""

import pytest
from awslabs.rds_control_plane_mcp_server.tools.db_instance.create_performance_report import (
    _parse_datetime,
    _validate_time_range,
    create_performance_report,
)
from datetime import datetime


class TestCreatePerformanceReport:
    """Test cases for create_performance_report function."""

    @pytest.mark.asyncio
    async def test_create_report_readonly_mode(self, mock_rds_context_readonly):
        """Test performance report creation in readonly mode."""
        result = await create_performance_report(dbi_resource_identifier='db-instance-1')

        assert 'error' in result
        assert 'read-only mode' in result['error']

    @pytest.mark.asyncio
    async def test_create_report_success(self, mock_pi_client, mock_rds_context_allowed):
        """Test successful performance report creation."""
        mock_pi_client.create_performance_analysis_report.return_value = {
            'AnalysisReportId': 'report-123'
        }

        result = await create_performance_report(
            dbi_resource_identifier='db-instance-1',
            start_time='2024-01-01T10:00:00Z',
            end_time='2024-01-01T11:00:00Z',
        )

        assert 'report-123' in result
        assert 'db-instance-1' in result
        mock_pi_client.create_performance_analysis_report.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_report_with_default_times(
        self, mock_pi_client, mock_rds_context_allowed
    ):
        """Test performance report creation with default time range."""
        mock_pi_client.create_performance_analysis_report.return_value = {
            'AnalysisReportId': 'report-456'
        }

        result = await create_performance_report(dbi_resource_identifier='db-instance-1')

        assert 'report-456' in result
        mock_pi_client.create_performance_analysis_report.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_report_no_report_id(self, mock_pi_client, mock_rds_context_allowed):
        """Test performance report creation when no report ID returned."""
        mock_pi_client.create_performance_analysis_report.return_value = {}

        result = await create_performance_report(dbi_resource_identifier='db-instance-1')

        assert 'error' in result
        assert 'Failed to create performance report' in result['error_message']


class TestTimeUtilities:
    """Test time utility functions."""

    def test_parse_datetime_with_z(self):
        """Test parsing ISO datetime with Z suffix."""
        result = _parse_datetime('2024-01-01T12:00:00Z', 5)
        expected = datetime(
            2024, 1, 1, 12, 0, 0, tzinfo=datetime.fromisoformat('2024-01-01T12:00:00+00:00').tzinfo
        )
        assert result == expected

    def test_parse_datetime_without_z(self):
        """Test parsing ISO datetime without Z suffix."""
        result = _parse_datetime('2024-01-01T12:00:00+00:00', 5)
        expected = datetime(
            2024, 1, 1, 12, 0, 0, tzinfo=datetime.fromisoformat('2024-01-01T12:00:00+00:00').tzinfo
        )
        assert result == expected

    def test_parse_datetime_with_default(self):
        """Test parsing with default value when None is provided."""
        result = _parse_datetime(None, 5)

        assert isinstance(result, datetime)
        # Should be roughly 5 days ago
        now = datetime.now()
        assert 4 <= (now - result).days <= 6

    def test_parse_datetime_invalid_format(self):
        """Test parsing datetime with invalid format."""
        with pytest.raises(ValueError) as exc_info:
            _parse_datetime('invalid-date', 5)

        assert 'Invalid time format' in str(exc_info.value)

    def test_validate_time_range_valid(self):
        """Test validating valid time range."""
        start = datetime(2024, 1, 1, 10, 0, 0)
        end = datetime(2024, 1, 1, 11, 0, 0)

        # Should not raise exception
        _validate_time_range(start, end)

    def test_validate_time_range_start_after_end(self):
        """Test validating time range where start is after end."""
        start = datetime(2024, 1, 1, 11, 0, 0)
        end = datetime(2024, 1, 1, 10, 0, 0)

        with pytest.raises(ValueError) as exc_info:
            _validate_time_range(start, end)

        assert 'start_time must be before end_time' in str(exc_info.value)

    def test_validate_time_range_too_short(self):
        """Test validating time range that is too short."""
        start = datetime(2024, 1, 1, 10, 0, 0)
        end = datetime(2024, 1, 1, 10, 2, 0)  # Only 2 minutes

        with pytest.raises(ValueError) as exc_info:
            _validate_time_range(start, end)

        assert 'Time range must be at least 5 minutes' in str(exc_info.value)

    def test_validate_time_range_too_long(self):
        """Test validating time range that is too long."""
        start = datetime(2024, 1, 1, 10, 0, 0)
        end = datetime(2024, 1, 8, 10, 0, 0)  # 7 days

        with pytest.raises(ValueError) as exc_info:
            _validate_time_range(start, end)

        assert 'Time range cannot exceed 6 days' in str(exc_info.value)
