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

"""Unit tests for ScanAccessPattern model."""

import pytest
from .test_data_model import strip_pydantic_error_url
from awslabs.dynamodb_mcp_server.cost_performance_calculator.data_model import (
    ScanAccessPattern,
    format_validation_errors,
)
from pydantic import ValidationError


class TestScanAccessPattern:
    """Tests for ScanAccessPattern model."""

    @pytest.fixture
    def scan_pattern(self):
        """Base Scan access pattern for calculation tests."""
        return {
            'operation': 'Scan',
            'pattern': 'test',
            'description': 'test',
            'table': 'test-table',
            'rps': 100,
            'item_size_bytes': 2000,
            'item_count': 50,
            'strongly_consistent': False,
        }

    class TestValid:
        """Tests for valid Scan creation."""

        def test_valid_scan_minimal(self, scan_pattern):
            """Test Scan with valid minimal data."""
            ap = ScanAccessPattern(**scan_pattern)
            assert ap.operation == 'Scan'
            assert ap.item_count == 50

        def test_valid_scan_with_gsi(self, scan_pattern):
            """Test Scan with GSI."""
            scan_pattern['gsi'] = 'test-gsi'
            ap = ScanAccessPattern(**scan_pattern)
            assert ap.gsi == 'test-gsi'

    class TestInvalid:
        """Tests for invalid Scan creation."""

        def test_invalid_scan_gsi_with_strong_consistency(self, scan_pattern):
            """Test Scan rejects GSI with strong consistency."""
            scan_pattern['gsi'] = 'test-gsi'
            scan_pattern['strongly_consistent'] = True
            with pytest.raises(ValidationError) as exc_info:
                ScanAccessPattern(**scan_pattern)
            err = strip_pydantic_error_url(exc_info.value)
            assert err.startswith(
                '1 validation error for ScanAccessPattern\n  Value error, GSI does not support strongly consistent reads. gsi: "test-gsi", strongly_consistent: True [type=value_error, input_value='
            )
            assert (
                format_validation_errors(exc_info.value)
                == 'GSI does not support strongly consistent reads. gsi: "test-gsi", strongly_consistent: True'
            )
