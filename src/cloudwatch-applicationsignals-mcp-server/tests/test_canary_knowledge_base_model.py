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

"""Tests for canary_knowledge_base_model Pydantic models."""

import pytest
from awslabs.cloudwatch_applicationsignals_mcp_server.canary_knowledge_base_model import (
    ErrorPattern,
    FailureContext,
    KBEntry,
    MatchResult,
    SolutionStep,
)
from datetime import date


class TestErrorPattern:
    """Tests for ErrorPattern model."""

    def test_all_fields_optional(self):
        """Test All fields optional."""
        p = ErrorPattern()
        assert p.regex is None
        assert p.text_contains is None
        assert p.error_type is None

    def test_with_regex(self):
        """Test With regex."""
        p = ErrorPattern(regex=r'page\.goto:.*Timeout')
        assert p.regex == r'page\.goto:.*Timeout'

    def test_with_text_contains(self):
        """Test With text contains."""
        p = ErrorPattern(text_contains='Timeout 60000ms exceeded')
        assert p.text_contains == 'Timeout 60000ms exceeded'

    def test_with_error_type(self):
        """Test With error type."""
        p = ErrorPattern(error_type='TimeoutError')
        assert p.error_type == 'TimeoutError'


class TestSolutionStep:
    """Tests for SolutionStep model."""

    def test_minimal(self):
        """Test Minimal."""
        s = SolutionStep(step='Increase timeout')
        assert s.step == 'Increase timeout'
        assert s.description is None
        assert s.command is None
        assert s.expected_outcome is None

    def test_full(self):
        """Test Full."""
        s = SolutionStep(
            step='Update config',
            description='Change the timeout value',
            command='aws synthetics update-canary ...',
            expected_outcome='Canary passes',
        )
        assert s.command is not None


class TestKBEntry:
    """Tests for KBEntry model."""

    @pytest.fixture
    def minimal_entry_data(self):
        """Minimal entry data."""
        return {
            'id': 'TEST-001',
            'title': 'Test entry',
            'category': 'test',
            'severity': 'high',
            'error_patterns': [{'text_contains': 'error'}],
            'symptoms': ['Something broke'],
            'root_cause': 'A bug',
            'recommendations': [
                {
                    'priority': 'high',
                    'confidence': 90,
                    'solution': [{'step': 'Fix it'}],
                }
            ],
        }

    def test_minimal_entry(self, minimal_entry_data):
        """Test Minimal entry."""
        entry = KBEntry(**minimal_entry_data)
        assert entry.id == 'TEST-001'
        assert entry.severity == 'high'
        assert entry.deprecated is False
        assert entry.tags == []
        assert entry.runtime_versions == []

    def test_severity_validation_valid(self, minimal_entry_data):
        """Test Severity validation valid."""
        for sev in ['critical', 'high', 'medium', 'low', 'HIGH', 'Critical']:
            minimal_entry_data['severity'] = sev
            entry = KBEntry(**minimal_entry_data)
            assert entry.severity == sev.lower()

    def test_severity_validation_invalid(self, minimal_entry_data):
        """Test Severity validation invalid."""
        minimal_entry_data['severity'] = 'urgent'
        with pytest.raises(ValueError, match='severity must be one of'):
            KBEntry(**minimal_entry_data)

    def test_extra_fields_ignored(self, minimal_entry_data):
        """Test Extra fields ignored."""
        minimal_entry_data['unknown_field'] = 'should be ignored'
        entry = KBEntry(**minimal_entry_data)
        assert not hasattr(entry, 'unknown_field')

    def test_deprecated_entry(self, minimal_entry_data):
        """Test Deprecated entry."""
        minimal_entry_data['deprecated'] = True
        minimal_entry_data['deprecation_date'] = '2025-01-01'
        entry = KBEntry(**minimal_entry_data)
        assert entry.deprecated is True
        assert entry.deprecation_date == date(2025, 1, 1)

    def test_documentation_links(self, minimal_entry_data):
        """Test Documentation links."""
        minimal_entry_data['documentation_links'] = [
            {'title': 'AWS Docs', 'url': 'https://docs.aws.amazon.com'}
        ]
        entry = KBEntry(**minimal_entry_data)
        assert len(entry.documentation_links) == 1
        assert entry.documentation_links[0].title == 'AWS Docs'


class TestFailureContext:
    """Tests for FailureContext model."""

    def test_defaults(self):
        """Test Defaults."""
        ctx = FailureContext()
        assert ctx.error_messages == []
        assert ctx.state_reasons == []
        assert ctx.runtime_version == ''
        assert ctx.log_patterns == []
        assert ctx.resource_metrics == {}
        assert ctx.environment_indicators == []

    def test_with_data(self):
        """Test With data."""
        ctx = FailureContext(
            error_messages=['Timeout 60000ms exceeded'],
            runtime_version='syn-nodejs-playwright-2.0',
            resource_metrics={'maxEphemeralStorageUsagePercent': 92.5},
        )
        assert len(ctx.error_messages) == 1
        assert ctx.resource_metrics['maxEphemeralStorageUsagePercent'] == 92.5


class TestMatchResult:
    """Tests for MatchResult model."""

    def test_match_result(self):
        """Test Match result."""
        entry = KBEntry(
            id='T-001',
            title='Test',
            category='test',
            severity='high',
            error_patterns=[],
            symptoms=[],
            root_cause='bug',
            recommendations=[],
        )
        result = MatchResult(
            entry=entry,
            confidence_score=0.85,
            error_pattern_score=1.0,
            symptom_score=0.5,
            runtime_version_score=1.0,
            environment_score=0.0,
        )
        assert result.confidence_score == 0.85
        assert result.error_pattern_score == 1.0
