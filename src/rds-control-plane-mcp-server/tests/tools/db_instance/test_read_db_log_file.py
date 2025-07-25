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

"""Tests for read_db_log_file tool."""

import pytest
from awslabs.rds_control_plane_mcp_server.tools.db_instance.read_db_log_file import (
    DBLogFileResponse,
    preprocess_log_content,
    read_db_log_file,
)


class TestReadDBLogFile:
    """Test cases for read_db_log_file function."""

    @pytest.mark.asyncio
    async def test_read_log_file_success(self, mock_rds_client):
        """Test successful log file reading."""
        mock_rds_client.download_db_log_file_portion.return_value = {
            'LogFileData': 'ERROR: Connection failed\nINFO: Starting service\nERROR: Database timeout',
            'Marker': 'next-marker-123',
            'AdditionalDataPending': True,
        }

        result = await read_db_log_file(
            db_instance_identifier='test-instance', log_file_name='error/postgresql.log', pattern=None
        )

        assert isinstance(result, DBLogFileResponse)
        assert (
            result.log_content
            == 'ERROR: Connection failed\nINFO: Starting service\nERROR: Database timeout'
        )
        assert result.next_marker == 'next-marker-123'
        assert result.additional_data_pending is True
        mock_rds_client.download_db_log_file_portion.assert_called_once()

    @pytest.mark.asyncio
    async def test_read_log_file_with_pattern(self, mock_rds_client):
        """Test log file reading with pattern filter."""
        mock_rds_client.download_db_log_file_portion.return_value = {
            'LogFileData': 'ERROR: Connection failed\nINFO: Starting service\nERROR: Database timeout',
            'Marker': 'next-marker-123',
            'AdditionalDataPending': True,
        }

        result = await read_db_log_file(
            db_instance_identifier='test-instance',
            log_file_name='error/postgresql.log',
            pattern='ERROR',
        )

        assert isinstance(result, DBLogFileResponse)
        assert 'ERROR: Connection failed' in result.log_content
        assert 'ERROR: Database timeout' in result.log_content
        assert 'INFO: Starting service' not in result.log_content

    @pytest.mark.asyncio
    async def test_read_log_file_with_marker(self, mock_rds_client):
        """Test log file reading with pagination marker."""
        mock_rds_client.download_db_log_file_portion.return_value = {
            'LogFileData': 'ERROR: Connection failed\nINFO: Starting service\nERROR: Database timeout',
            'Marker': 'next-marker-123',
            'AdditionalDataPending': True,
        }

        result = await read_db_log_file(
            db_instance_identifier='test-instance',
            log_file_name='error/postgresql.log',
            marker='previous-marker',
            pattern=None,
        )

        assert isinstance(result, DBLogFileResponse)
        call_args = mock_rds_client.download_db_log_file_portion.call_args[1]
        assert call_args['Marker'] == 'previous-marker'

    @pytest.mark.asyncio
    async def test_read_log_file_with_number_of_lines(self, mock_rds_client):
        """Test log file reading with specific number of lines."""
        mock_rds_client.download_db_log_file_portion.return_value = {
            'LogFileData': 'ERROR: Connection failed\nINFO: Starting service\nERROR: Database timeout',
            'Marker': 'next-marker-123',
            'AdditionalDataPending': True,
        }

        result = await read_db_log_file(
            db_instance_identifier='test-instance',
            log_file_name='error/postgresql.log',
            number_of_lines=50,
            pattern=None,
        )

        assert isinstance(result, DBLogFileResponse)
        call_args = mock_rds_client.download_db_log_file_portion.call_args[1]
        assert call_args['NumberOfLines'] == 50

    @pytest.mark.asyncio
    async def test_preprocess_log_content_no_pattern(self):
        """Test log content preprocessing without pattern."""
        content = 'Line 1\nLine 2\nLine 3'
        result = await preprocess_log_content(content)
        assert result == content

    @pytest.mark.asyncio
    async def test_preprocess_log_content_with_pattern(self):
        """Test log content preprocessing with pattern."""
        content = 'ERROR: Failed\nINFO: Success\nERROR: Timeout'
        result = await preprocess_log_content(content, pattern='ERROR')
        assert result == 'ERROR: Failed\nERROR: Timeout'

    @pytest.mark.asyncio
    async def test_preprocess_log_content_empty(self):
        """Test log content preprocessing with empty content."""
        result = await preprocess_log_content('', pattern='ERROR')
        assert result == ''

    @pytest.mark.asyncio
    async def test_preprocess_log_content_no_matches(self):
        """Test log content preprocessing with no pattern matches."""
        content = 'INFO: Success\nDEBUG: Details'
        result = await preprocess_log_content(content, pattern='ERROR')
        assert result == ''
