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

"""Tests for parse_filter and the parse_json error hint."""

import json
import pytest
from awslabs.billing_cost_management_mcp_server.utilities import aws_service_base


LEAF = {'Dimensions': {'Key': 'SERVICE', 'Values': ['Amazon Simple Storage Service']}}


class TestParseJsonHint:
    """Invalid JSON gets a hint about the quoting."""

    def test_python_repr_names_double_quotes(self):
        """A dict repr with single quotes is the usual mistake, so the error names the fix."""
        with pytest.raises(ValueError) as excinfo:
            aws_service_base.parse_json(str(LEAF), 'filter')

        message = str(excinfo.value)
        assert message.startswith('Invalid JSON format for filter parameter: ')
        assert 'double quotes' in message


class TestParseFilter:
    """parse_filter keeps None as "no filter" and rejects an empty one."""

    def test_none_is_no_filter(self):
        """Omitting the filter is not an error."""
        assert aws_service_base.parse_filter(None) is None

    @pytest.mark.parametrize(
        'value', [LEAF, '{"Dimensions": {"Key": "SERVICE", "Values": ["x"]}}']
    )
    def test_expression_is_parsed(self, value):
        """An object passes through and a JSON string is parsed."""
        parsed = aws_service_base.parse_filter(value)

        assert isinstance(parsed, dict) and 'Dimensions' in parsed

    @pytest.mark.parametrize('value', ['', '   ', '{}', {}, '[]', [], 'null'], ids=repr)
    def test_empty_is_rejected(self, value):
        """An empty filter would match everything, so it is an error, not "no filter"."""
        with pytest.raises(ValueError) as excinfo:
            aws_service_base.parse_filter(value)

        assert str(excinfo.value) == (
            'filter is empty. Omit filter to query without one, or pass a filter expression.'
        )

    @pytest.mark.parametrize('value', ['0', 'false', '"SERVICE"'])
    def test_scalars_are_left_to_the_service(self, value):
        """A non-empty JSON scalar is not called empty; the SDK or service rejects its shape."""
        assert aws_service_base.parse_filter(value) == json.loads(value)

    def test_parameter_name_is_used(self):
        """The error names the caller's parameter."""
        with pytest.raises(ValueError, match='^filters is empty. Omit filters'):
            aws_service_base.parse_filter({}, 'filters')

    def test_invalid_json_keeps_the_hint(self):
        """Malformed JSON reports the JSON error, not an empty filter."""
        with pytest.raises(ValueError, match='double quotes'):
            aws_service_base.parse_filter("{'Dimensions': {}}")
