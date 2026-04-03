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

"""Tests for common utilities."""

from datetime import datetime, timezone


class TestRemoveNullValues:
    """Tests for remove_null_values."""

    def test_mixed_dict(self):
        from awslabs.aws_systems_manager_for_sap_mcp_server.common import remove_null_values
        result = remove_null_values({'a': 1, 'b': None, 'c': 'hello', 'd': None})
        assert result == {'a': 1, 'c': 'hello'}

    def test_empty_dict(self):
        from awslabs.aws_systems_manager_for_sap_mcp_server.common import remove_null_values
        assert remove_null_values({}) == {}

    def test_all_none(self):
        from awslabs.aws_systems_manager_for_sap_mcp_server.common import remove_null_values
        assert remove_null_values({'a': None, 'b': None}) == {}


class TestFormatDatetime:
    """Tests for format_datetime."""

    def test_datetime_object(self):
        from awslabs.aws_systems_manager_for_sap_mcp_server.common import format_datetime
        dt = datetime(2026, 3, 15, 10, 30, 0, tzinfo=timezone.utc)
        assert format_datetime(dt) == '2026-03-15 10:30:00 UTC'

    def test_none_input(self):
        from awslabs.aws_systems_manager_for_sap_mcp_server.common import format_datetime
        assert format_datetime(None) == 'N/A'

    def test_string_input(self):
        from awslabs.aws_systems_manager_for_sap_mcp_server.common import format_datetime
        assert format_datetime('2026-03-15') == '2026-03-15'

    def test_exception_branch(self):
        """Test format_datetime with an object whose strftime raises."""
        from awslabs.aws_systems_manager_for_sap_mcp_server.common import format_datetime

        class BadDatetime(datetime):
            def strftime(self, fmt):
                raise ValueError('bad format')

        bad_dt = BadDatetime(2026, 1, 1, tzinfo=timezone.utc)
        result = format_datetime(bad_dt)
        # Falls through to str(dt) in the except branch
        assert '2026' in result


class TestSafeJsonSerialize:
    """Tests for safe_json_serialize."""

    def test_dict_with_datetime(self):
        from awslabs.aws_systems_manager_for_sap_mcp_server.common import safe_json_serialize
        dt = datetime(2026, 3, 15, 10, 0, 0, tzinfo=timezone.utc)
        result = safe_json_serialize({'key': 'value', 'time': dt})
        assert '"key": "value"' in result
        assert '2026' in result

    def test_simple_dict(self):
        from awslabs.aws_systems_manager_for_sap_mcp_server.common import safe_json_serialize
        result = safe_json_serialize({'a': 1, 'b': [1, 2]})
        assert '"a": 1' in result
