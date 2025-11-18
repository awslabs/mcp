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

"""Edge case tests for validator module."""

from awslabs.iac_mcp_server.validator import _format_results, _map_level
from cfnlint.match import Match
from cfnlint.rules import CloudFormationLintRule
from unittest.mock import Mock


class TestMapLevel:
    """Test severity determination from rule IDs."""

    def test_error_severity(self):
        """Test error severity for E-prefixed rules."""
        assert _map_level('E1234') == 'error'
        assert _map_level('E9999') == 'error'

    def test_warning_severity(self):
        """Test warning severity for W-prefixed rules."""
        assert _map_level('W1234') == 'warning'
        assert _map_level('W9999') == 'warning'

    def test_info_severity(self):
        """Test info severity for I-prefixed rules."""
        assert _map_level('I1234') == 'info'
        assert _map_level('I9999') == 'info'

    def test_unknown_severity_defaults_to_error(self):
        """Test unknown rule IDs default to error."""
        assert _map_level('X1234') == 'error'
        assert _map_level('1234') == 'error'
        assert _map_level('') == 'error'


class TestFormatResults:
    """Test match formatting with different severity levels."""

    def test_format_results_with_info_level(self):
        """Test formatting matches with info level."""
        mock_rule = Mock(spec=CloudFormationLintRule)
        mock_rule.id = 'I1234'
        mock_rule.shortdesc = 'Info message'
        mock_rule.description = 'Info description'

        match = Match(
            linenumber=10,
            columnnumber=5,
            linenumberend=10,
            columnnumberend=20,
            filename='template.yaml',
            rule=mock_rule,
            message='This is an info message',
        )

        result = _format_results([match])

        assert result['validation_results']['info_count'] == 1
        assert result['validation_results']['warning_count'] == 0
        assert result['validation_results']['error_count'] == 0
        assert len(result['issues']) == 1
        assert result['issues'][0]['level'] == 'info'
