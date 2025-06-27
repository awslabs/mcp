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

"""Tests for the SecurityValidator class."""

import pytest
from awslabs.prometheus_mcp_server.server import SecurityValidator, DANGEROUS_PATTERNS


class TestSecurityValidator:
    """Tests for the SecurityValidator class."""

    def test_validate_string_safe(self):
        """Test that validate_string returns True for safe strings."""
        safe_strings = [
            "safe string",
            "metric{label='value'}",
            "rate(http_requests_total[5m])",
            "sum by(instance) (rate(node_cpu_seconds_total{mode='system'}[5m]))",
        ]
        
        for string in safe_strings:
            assert SecurityValidator.validate_string(string) is True
            assert SecurityValidator.validate_string(string, "test context") is True

    def test_validate_string_unsafe(self):
        """Test that validate_string returns False for unsafe strings."""
        for pattern in DANGEROUS_PATTERNS:
            unsafe_string = f"before {pattern} after"
            assert SecurityValidator.validate_string(unsafe_string) is False
            assert SecurityValidator.validate_string(unsafe_string, "test context") is False

    def test_validate_params_safe(self):
        """Test that validate_params returns True for safe parameters."""
        # Test with None
        assert SecurityValidator.validate_params(None) is True
        
        # Test with empty dict
        assert SecurityValidator.validate_params({}) is True
        
        # Test with safe parameters
        safe_params = {
            "query": "rate(http_requests_total[5m])",
            "time": "2023-01-01T00:00:00Z",
            "step": "15s",
        }
        assert SecurityValidator.validate_params(safe_params) is True
        
        # Test with non-string values
        mixed_params = {
            "query": "rate(http_requests_total[5m])",
            "count": 10,
            "enabled": True,
        }
        assert SecurityValidator.validate_params(mixed_params) is True

    def test_validate_params_unsafe(self):
        """Test that validate_params returns False for unsafe parameters."""
        for pattern in DANGEROUS_PATTERNS:
            unsafe_params = {
                "query": "rate(http_requests_total[5m])",
                "unsafe": f"before {pattern} after",
            }
            assert SecurityValidator.validate_params(unsafe_params) is False

    def test_validate_query(self):
        """Test that validate_query correctly validates PromQL queries."""
        # Test safe queries
        safe_queries = [
            "up",
            "rate(http_requests_total[5m])",
            "sum by(instance) (rate(node_cpu_seconds_total{mode='system'}[5m]))",
            "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))",
        ]
        for query in safe_queries:
            assert SecurityValidator.validate_query(query) is True
        
        # Test unsafe queries
        for pattern in DANGEROUS_PATTERNS:
            unsafe_query = f"rate(http_requests_total{pattern}[5m])"
            assert SecurityValidator.validate_query(unsafe_query) is False