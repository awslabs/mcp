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

"""Tests for canary_recommendation_engine."""

import pytest
from awslabs.cloudwatch_applicationsignals_mcp_server.canary_knowledge_base_loader import (
    CanaryKnowledgeBaseLoader,
)
from awslabs.cloudwatch_applicationsignals_mcp_server.canary_knowledge_base_model import (
    ErrorPattern,
    FailureContext,
    KBEntry,
    MatchResult,
)
from awslabs.cloudwatch_applicationsignals_mcp_server.canary_recommendation_engine import (
    CanaryRecommendationEngine,
    _extract_keywords,
)
from unittest.mock import MagicMock


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the singleton instance before each test."""
    CanaryKnowledgeBaseLoader._instance = None
    yield
    CanaryKnowledgeBaseLoader._instance = None


def _make_entry(**overrides):
    """Helper to create a KBEntry with sensible defaults."""
    defaults = {
        'id': 'TEST-001',
        'title': 'Test entry',
        'category': 'test',
        'severity': 'high',
        'error_patterns': [ErrorPattern(text_contains='timeout')],
        'symptoms': ['Canary fails with timeout'],
        'root_cause': 'A bug',
        'recommendations': [],
        'runtime_versions': ['syn-nodejs-puppeteer-10.0'],
        'tags': ['timeout', 'puppeteer'],
    }
    defaults.update(overrides)
    return KBEntry(**defaults)


def _make_context(**overrides):
    """Helper to create a FailureContext with sensible defaults."""
    defaults = {
        'error_messages': ['timeout occurred'],
        'state_reasons': ['timeout occurred'],
        'runtime_version': 'syn-nodejs-puppeteer-10.0',
    }
    defaults.update(overrides)
    return FailureContext(**defaults)


class TestExtractKeywords:
    """Tests for _extract_keywords helper."""

    def test_basic(self):
        """Test Basic."""
        kw = _extract_keywords('Canary fails with timeout error')
        assert 'canary' in kw
        assert 'fails' in kw
        assert 'timeout' in kw
        assert 'error' in kw

    def test_stop_words_removed(self):
        """Test Stop words removed."""
        kw = _extract_keywords('the canary is not working')
        assert 'the' not in kw
        assert 'is' not in kw
        assert 'not' not in kw
        assert 'canary' in kw
        assert 'working' in kw

    def test_short_words_removed(self):
        """Test Short words removed."""
        kw = _extract_keywords('a b cd efg')
        assert 'a' not in kw
        assert 'b' not in kw
        assert 'cd' in kw
        assert 'efg' in kw

    def test_preserves_underscores(self):
        """Test Preserves underscores."""
        kw = _extract_keywords('UPDATE_ROLLBACK_FAILED state')
        assert 'update_rollback_failed' in kw

    def test_empty_string(self):
        """Test Empty string."""
        assert _extract_keywords('') == []


class TestScoreErrorPatterns:
    """Tests for _score_error_patterns."""

    def test_text_contains_match(self):
        """Test Text contains match."""
        entry = _make_entry(error_patterns=[ErrorPattern(text_contains='Timeout 60000ms')])
        ctx = _make_context(error_messages=['page.goto: Timeout 60000ms exceeded'])
        engine = CanaryRecommendationEngine(MagicMock())
        assert engine._score_error_patterns(entry, ctx) == 1.0

    def test_text_contains_case_insensitive(self):
        """Test Text contains case insensitive."""
        entry = _make_entry(error_patterns=[ErrorPattern(text_contains='TIMEOUT')])
        ctx = _make_context(error_messages=['timeout occurred'])
        engine = CanaryRecommendationEngine(MagicMock())
        assert engine._score_error_patterns(entry, ctx) == 1.0

    def test_regex_match(self):
        """Test Regex match."""
        entry = _make_entry(error_patterns=[ErrorPattern(regex=r'page\.goto:.*Timeout.*exceeded')])
        ctx = _make_context(error_messages=['page.goto: Timeout 60000ms exceeded'])
        engine = CanaryRecommendationEngine(MagicMock())
        assert engine._score_error_patterns(entry, ctx) == 1.0

    def test_regex_no_match(self):
        """Test Regex no match."""
        entry = _make_entry(error_patterns=[ErrorPattern(regex=r'page\.goto:.*Timeout')])
        ctx = _make_context(error_messages=['something else entirely'])
        engine = CanaryRecommendationEngine(MagicMock())
        assert engine._score_error_patterns(entry, ctx) == 0.0

    def test_regex_invalid(self):
        """Test Regex invalid."""
        entry = _make_entry(error_patterns=[ErrorPattern(regex=r'[invalid')])
        ctx = _make_context(error_messages=['test'])
        engine = CanaryRecommendationEngine(MagicMock())
        assert engine._score_error_patterns(entry, ctx) == 0.0

    def test_error_type_match(self):
        """Test Error type match."""
        entry = _make_entry(error_patterns=[ErrorPattern(error_type='TimeoutError')])
        ctx = _make_context(error_messages=['TimeoutError'])
        engine = CanaryRecommendationEngine(MagicMock())
        assert engine._score_error_patterns(entry, ctx) == 1.0

    def test_error_type_no_match(self):
        """Test Error type no match."""
        entry = _make_entry(error_patterns=[ErrorPattern(error_type='TimeoutError')])
        ctx = _make_context(error_messages=['SomeOtherError'])
        engine = CanaryRecommendationEngine(MagicMock())
        assert engine._score_error_patterns(entry, ctx) == 0.0

    def test_no_patterns(self):
        """Test No patterns."""
        entry = _make_entry(error_patterns=[])
        ctx = _make_context(error_messages=['timeout'])
        engine = CanaryRecommendationEngine(MagicMock())
        assert engine._score_error_patterns(entry, ctx) == 0.0

    def test_no_messages(self):
        """Test No messages."""
        entry = _make_entry()
        ctx = _make_context(error_messages=[])
        engine = CanaryRecommendationEngine(MagicMock())
        assert engine._score_error_patterns(entry, ctx) == 0.0

    def test_multiple_patterns_or_semantics(self):
        """Test Multiple patterns or semantics."""
        entry = _make_entry(
            error_patterns=[
                ErrorPattern(text_contains='no match here'),
                ErrorPattern(text_contains='timeout'),
            ]
        )
        ctx = _make_context(error_messages=['timeout occurred'])
        engine = CanaryRecommendationEngine(MagicMock())
        assert engine._score_error_patterns(entry, ctx) == 1.0


class TestScoreSymptoms:
    """Tests for _score_symptoms."""

    def test_full_match(self):
        """Test Full match."""
        entry = _make_entry(symptoms=['Canary fails with timeout'])
        ctx = _make_context(error_messages=['Canary fails with timeout error'])
        engine = CanaryRecommendationEngine(MagicMock())
        assert engine._score_symptoms(entry, ctx) == 1.0

    def test_partial_match(self):
        """Test Partial match."""
        entry = _make_entry(
            symptoms=[
                'Canary fails with timeout',
                'Memory usage exceeds 90%',
            ]
        )
        ctx = _make_context(error_messages=['Canary fails with timeout error'])
        engine = CanaryRecommendationEngine(MagicMock())
        score = engine._score_symptoms(entry, ctx)
        assert 0.0 < score < 1.0

    def test_no_match(self):
        """Test No match."""
        entry = _make_entry(symptoms=['Visual baseline overwritten'])
        ctx = _make_context(error_messages=['timeout occurred'])
        engine = CanaryRecommendationEngine(MagicMock())
        assert engine._score_symptoms(entry, ctx) == 0.0

    def test_empty_symptoms(self):
        """Test Empty symptoms."""
        entry = _make_entry(symptoms=[])
        ctx = _make_context()
        engine = CanaryRecommendationEngine(MagicMock())
        assert engine._score_symptoms(entry, ctx) == 0.0


class TestScoreRuntimeVersion:
    """Tests for _score_runtime_version."""

    def test_exact_match(self):
        """Test Exact match."""
        entry = _make_entry(runtime_versions=['syn-nodejs-puppeteer-10.0'])
        ctx = _make_context(runtime_version='syn-nodejs-puppeteer-10.0')
        engine = CanaryRecommendationEngine(MagicMock())
        assert engine._score_runtime_version(entry, ctx) == 1.0

    def test_no_match(self):
        """Test No match."""
        entry = _make_entry(runtime_versions=['syn-nodejs-puppeteer-10.0'])
        ctx = _make_context(runtime_version='syn-nodejs-puppeteer-9.0')
        engine = CanaryRecommendationEngine(MagicMock())
        assert engine._score_runtime_version(entry, ctx) == 0.0

    def test_wildcard(self):
        """Test Wildcard."""
        entry = _make_entry(runtime_versions=['*'])
        ctx = _make_context(runtime_version='syn-nodejs-puppeteer-10.0')
        engine = CanaryRecommendationEngine(MagicMock())
        assert engine._score_runtime_version(entry, ctx) == 0.5

    def test_suffix_plus_match(self):
        """Test Suffix plus match."""
        entry = _make_entry(runtime_versions=['syn-nodejs-puppeteer-8.0+'])
        ctx = _make_context(runtime_version='syn-nodejs-puppeteer-10.0')
        engine = CanaryRecommendationEngine(MagicMock())
        assert engine._score_runtime_version(entry, ctx) == 1.0

    def test_suffix_plus_no_match(self):
        """Test Suffix plus no match."""
        entry = _make_entry(runtime_versions=['syn-nodejs-puppeteer-11.0+'])
        ctx = _make_context(runtime_version='syn-nodejs-puppeteer-10.0')
        engine = CanaryRecommendationEngine(MagicMock())
        assert engine._score_runtime_version(entry, ctx) == 0.0

    def test_empty_runtime_versions(self):
        """Test Empty runtime versions."""
        entry = _make_entry(runtime_versions=[])
        ctx = _make_context()
        engine = CanaryRecommendationEngine(MagicMock())
        assert engine._score_runtime_version(entry, ctx) == 1.0

    def test_no_context_runtime(self):
        """Test No context runtime."""
        entry = _make_entry(runtime_versions=['syn-nodejs-puppeteer-10.0'])
        ctx = _make_context(runtime_version='')
        engine = CanaryRecommendationEngine(MagicMock())
        assert engine._score_runtime_version(entry, ctx) == 0.0

    def test_different_family_plus(self):
        """Test Different family plus."""
        entry = _make_entry(runtime_versions=['syn-nodejs-puppeteer-8.0+'])
        ctx = _make_context(runtime_version='syn-nodejs-playwright-10.0')
        engine = CanaryRecommendationEngine(MagicMock())
        assert engine._score_runtime_version(entry, ctx) == 0.0


class TestScoreEnvironment:
    """Tests for _score_environment."""

    def test_overlap(self):
        """Test Overlap."""
        entry = _make_entry(tags=['timeout', 'puppeteer'], category='test')
        ctx = _make_context(environment_indicators=['timeout', 'lambda'])
        engine = CanaryRecommendationEngine(MagicMock())
        score = engine._score_environment(entry, ctx)
        assert score > 0.0

    def test_no_overlap(self):
        """Test No overlap."""
        entry = _make_entry(tags=['visual', 'baseline'], category='visual_monitoring')
        ctx = _make_context(environment_indicators=['timeout', 'lambda'])
        engine = CanaryRecommendationEngine(MagicMock())
        assert engine._score_environment(entry, ctx) == 0.0

    def test_empty_indicators(self):
        """Test Empty indicators."""
        entry = _make_entry()
        ctx = _make_context(environment_indicators=[])
        engine = CanaryRecommendationEngine(MagicMock())
        assert engine._score_environment(entry, ctx) == 0.0


class TestComputeConfidence:
    """Tests for _compute_confidence."""

    def test_all_ones(self):
        """Test All ones."""
        engine = CanaryRecommendationEngine(MagicMock())
        assert engine._compute_confidence(1.0, 1.0, 1.0, 1.0) == 1.0

    def test_all_zeros(self):
        """Test All zeros."""
        engine = CanaryRecommendationEngine(MagicMock())
        assert engine._compute_confidence(0.0, 0.0, 0.0, 0.0) == 0.0

    def test_error_only(self):
        """Test Error only."""
        engine = CanaryRecommendationEngine(MagicMock())
        assert engine._compute_confidence(1.0, 0.0, 0.0, 0.0) == 0.4


def _load_kb_sync() -> CanaryKnowledgeBaseLoader:
    """Synchronously create and load a KB loader for tests."""
    loader = CanaryKnowledgeBaseLoader()
    loader.load()
    return loader


class TestGetRecommendations:
    """Tests for get_recommendations end-to-end."""

    def test_returns_matches_above_threshold(self):
        """Test Returns matches above threshold."""
        loader = _load_kb_sync()
        engine = CanaryRecommendationEngine(loader)

        ctx = FailureContext(
            error_messages=['page.goto: Timeout 60000ms exceeded. waiting until "load"'],
            runtime_version='syn-nodejs-playwright-2.0',
        )
        results = engine.get_recommendations(ctx)
        assert len(results) > 0
        assert results[0].entry.id == 'RUNTIME-001'

    def test_no_match_returns_empty(self):
        """Test No match returns empty."""
        loader = _load_kb_sync()
        engine = CanaryRecommendationEngine(loader)

        ctx = FailureContext(
            error_messages=['completely unrelated error xyz123'],
        )
        results = engine.get_recommendations(ctx)
        assert len(results) == 0

    def test_skips_entries_with_no_error_pattern_match(self):
        """Test Skips entries with no error pattern match."""
        loader = MagicMock()
        entry = _make_entry(error_patterns=[ErrorPattern(text_contains='very specific string')])
        loader.get_active_entries.return_value = [entry]

        engine = CanaryRecommendationEngine(loader)
        ctx = _make_context(error_messages=['no match here'])
        results = engine.get_recommendations(ctx)
        assert len(results) == 0

    def test_max_two_results(self):
        """Test Max two results."""
        loader = MagicMock()
        entries = [
            _make_entry(id=f'TEST-{i:03d}', error_patterns=[ErrorPattern(text_contains='error')])
            for i in range(10)
        ]
        loader.get_active_entries.return_value = entries

        engine = CanaryRecommendationEngine(loader)
        ctx = _make_context(
            error_messages=['error occurred'], runtime_version='syn-nodejs-puppeteer-10.0'
        )
        results = engine.get_recommendations(ctx)
        assert len(results) <= 2

    def test_sorted_by_confidence_descending(self):
        """Test Sorted by confidence descending."""
        loader = _load_kb_sync()
        engine = CanaryRecommendationEngine(loader)

        # Use a broad error message that might match multiple entries
        ctx = FailureContext(
            error_messages=['timeout', 'connection timed out after 60000ms'],
            runtime_version='syn-nodejs-puppeteer-12.0',
        )
        results = engine.get_recommendations(ctx)
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i].confidence_score >= results[i + 1].confidence_score


class TestFormatRecommendations:
    """Tests for format_recommendations."""

    def test_empty_list(self):
        """Test Empty list."""
        engine = CanaryRecommendationEngine(MagicMock())
        assert engine.format_recommendations([]) == ''

    def test_formats_entry(self):
        """Test Formats entry."""
        entry = _make_entry(
            id='RUNTIME-001',
            title='Playwright timeout',
            severity='high',
            category='script_timeouts',
            root_cause='Resource constraints',
            recommendations=[],
            documentation_links=[],
        )
        match = MatchResult(
            entry=entry,
            confidence_score=0.85,
            error_pattern_score=1.0,
            symptom_score=0.5,
            runtime_version_score=1.0,
            environment_score=0.0,
        )
        engine = CanaryRecommendationEngine(MagicMock())
        output = engine.format_recommendations([match])

        assert 'Knowledge Base Recommendations' in output
        assert 'RUNTIME-001' in output
        assert 'Playwright timeout' in output
        assert '85%' in output
        assert 'script_timeouts' in output

    def test_formats_deprecated_entry(self):
        """Test Formats deprecated entry."""
        entry = _make_entry(deprecated=True)
        match = MatchResult(
            entry=entry,
            confidence_score=0.7,
            error_pattern_score=1.0,
            symptom_score=0.0,
            runtime_version_score=0.5,
            environment_score=0.0,
        )
        engine = CanaryRecommendationEngine(MagicMock())
        output = engine.format_recommendations([match])
        assert 'DEPRECATED' in output

    def test_formats_documentation_links(self):
        """Test Formats documentation links."""
        entry = _make_entry(
            documentation_links=[
                {'title': 'AWS Docs', 'url': 'https://docs.aws.amazon.com'},
            ],
        )
        match = MatchResult(
            entry=entry,
            confidence_score=0.8,
            error_pattern_score=1.0,
            symptom_score=0.5,
            runtime_version_score=1.0,
            environment_score=0.0,
        )
        engine = CanaryRecommendationEngine(MagicMock())
        output = engine.format_recommendations([match])
        assert 'AWS Docs' in output

    def test_formats_recommendations_with_steps(self):
        """Test Formats recommendations with solution steps."""
        from awslabs.cloudwatch_applicationsignals_mcp_server.canary_knowledge_base_model import (
            Recommendation,
            SolutionStep,
        )

        entry = _make_entry(
            recommendations=[
                Recommendation(
                    priority='high',
                    confidence=90,
                    title='Increase timeout',
                    problem='Default timeout too low',
                    solution=[
                        SolutionStep(
                            step='Update config',
                            description='Change timeout value',
                            command='aws synthetics update-canary --name my-canary',
                            expected_outcome='Canary passes',
                        ),
                    ],
                    estimated_time='5 minutes',
                ),
            ],
        )
        match = MatchResult(
            entry=entry,
            confidence_score=0.85,
            error_pattern_score=1.0,
            symptom_score=0.5,
            runtime_version_score=1.0,
            environment_score=0.0,
        )
        engine = CanaryRecommendationEngine(MagicMock())
        output = engine.format_recommendations([match])
        assert 'Increase timeout' in output
        assert 'Default timeout too low' in output
        assert 'Update config' in output
        assert 'Change timeout value' in output
        assert 'aws synthetics update-canary' in output
        assert 'Canary passes' in output
        assert '5 minutes' in output

    def test_symptom_with_no_extractable_keywords_skipped(self):
        """Test that symptoms with no extractable keywords are skipped."""
        # A symptom made entirely of stop words / short words → no keywords extracted
        entry = _make_entry(symptoms=['a is the', 'Canary fails with timeout'])
        ctx = _make_context(error_messages=['Canary fails with timeout error'])
        engine = CanaryRecommendationEngine(MagicMock())
        # The first symptom should be skipped, second should match → 1/2 = 0.5
        score = engine._score_symptoms(entry, ctx)
        assert score == 0.5

    def test_suffix_plus_non_numeric_version_value_error(self):
        """Test ValueError path when version suffix+ has non-numeric version."""
        entry = _make_entry(runtime_versions=['syn-nodejs-puppeteer-abc+'])
        ctx = _make_context(runtime_version='syn-nodejs-puppeteer-10.0')
        engine = CanaryRecommendationEngine(MagicMock())
        # float('abc') raises ValueError → caught, returns 0.0
        assert engine._score_runtime_version(entry, ctx) == 0.0

    def test_suffix_plus_non_numeric_canary_version_value_error(self):
        """Test ValueError when canary runtime version is non-numeric."""
        entry = _make_entry(runtime_versions=['syn-nodejs-puppeteer-8.0+'])
        ctx = _make_context(runtime_version='syn-nodejs-puppeteer-beta')
        engine = CanaryRecommendationEngine(MagicMock())
        # float('beta') raises ValueError → caught, returns 0.0
        assert engine._score_runtime_version(entry, ctx) == 0.0

    def test_empty_tags_and_empty_category_returns_zero(self):
        """Test _score_environment returns 0.0 when tags=[] and category=''."""
        entry = _make_entry(tags=[], category='')
        ctx = _make_context(environment_indicators=['timeout'])
        engine = CanaryRecommendationEngine(MagicMock())
        assert engine._score_environment(entry, ctx) == 0.0

    def test_all_wildcard_runtime(self):
        """Test 'all' wildcard in runtime_versions returns 0.5."""
        entry = _make_entry(runtime_versions=['all'])
        ctx = _make_context(runtime_version='syn-nodejs-puppeteer-10.0')
        engine = CanaryRecommendationEngine(MagicMock())
        assert engine._score_runtime_version(entry, ctx) == 0.5
