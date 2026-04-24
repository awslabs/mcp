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

"""Recommendation engine: weighted scoring and ranking of knowledge base entries."""

from __future__ import annotations

import re
from .canary_knowledge_base_loader import CanaryKnowledgeBaseLoader
from .canary_knowledge_base_model import FailureContext, KBEntry, MatchResult
from loguru import logger


# Severity ordering for tiebreaking (higher index = higher priority)
_SEVERITY_ORDER = {'critical': 3, 'high': 2, 'medium': 1, 'low': 0}
_SEVERITY_ICONS = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}


_STOP_WORDS = frozenset(
    {
        'a',
        'an',
        'the',
        'is',
        'are',
        'was',
        'were',
        'be',
        'been',
        'being',
        'in',
        'on',
        'at',
        'to',
        'for',
        'of',
        'with',
        'by',
        'from',
        'as',
        'into',
        'through',
        'during',
        'before',
        'after',
        'above',
        'below',
        'and',
        'but',
        'or',
        'nor',
        'not',
        'so',
        'yet',
        'both',
        'either',
        'neither',
        'each',
        'every',
        'all',
        'any',
        'few',
        'more',
        'most',
        'other',
        'some',
        'such',
        'no',
        'only',
        'own',
        'same',
        'than',
        'too',
        'very',
        'can',
        'will',
        'just',
        'should',
        'now',
        'also',
        'it',
        'its',
        'this',
        'that',
        'these',
        'those',
        'he',
        'she',
        'they',
        'we',
        'you',
        'i',
        'me',
        'my',
        'your',
        'his',
        'her',
        'our',
        'their',
        'has',
        'have',
        'had',
        'do',
        'does',
        'did',
        'may',
        'might',
        'must',
        'shall',
        'would',
        'could',
    }
)

# Minimum keyword match ratio for a symptom to count as matched
_SYMPTOM_KEYWORD_THRESHOLD = 0.5


def _extract_keywords(text: str) -> list[str]:
    """Extract significant lowercase keywords from text, filtering stop words.

    Splits on non-alphanumeric boundaries (preserving underscores and hyphens
    within tokens like UPDATE_ROLLBACK_FAILED) and drops short/stop words.
    """
    # Split on whitespace and punctuation but keep underscores/hyphens inside tokens
    tokens = re.split(r'[^\w-]+', text.lower())
    return [t for t in tokens if t and len(t) > 1 and t not in _STOP_WORDS]


class CanaryRecommendationEngine:
    """Scores KB entries against failure context and returns ranked matches."""

    def __init__(self, loader: CanaryKnowledgeBaseLoader) -> None:
        """Initialize the engine with a knowledge base loader."""
        self.loader = loader

    def _score_error_patterns(self, entry: KBEntry, context: FailureContext) -> float:
        """Score 0.0-1.0 based on error_pattern matches (regex, text_contains, error_type).

        OR-semantics: any single pattern matching any single error message → 1.0.
        """
        if not entry.error_patterns or not context.error_messages:
            return 0.0

        for pattern in entry.error_patterns:
            for msg in context.error_messages:
                # regex match (case-insensitive)
                if pattern.regex:
                    try:
                        if re.search(pattern.regex, msg, re.IGNORECASE):
                            return 1.0
                    except re.error as e:
                        logger.warning(
                            f'Invalid regex in KB entry {entry.id}: {pattern.regex!r} - {e}'
                        )

                # text_contains match (case-insensitive substring)
                if pattern.text_contains:
                    if pattern.text_contains.lower() in msg.lower():
                        return 1.0

                # error_type match (exact match)
                if pattern.error_type:
                    if pattern.error_type == msg:
                        return 1.0

        return 0.0

    def _score_symptoms(self, entry: KBEntry, context: FailureContext) -> float:
        """Score as ratio of matched symptoms to total symptoms in entry.

        Uses keyword-based matching: each symptom is split into significant
        keywords and counts as matched if >= _SYMPTOM_KEYWORD_THRESHOLD of
        its keywords appear anywhere in the combined context text.
        """
        if not entry.symptoms:
            return 0.0

        # Combine all symptom-related text from the failure context
        combined_parts = context.error_messages + context.state_reasons + context.log_patterns
        combined_text = ' '.join(combined_parts)
        context_keywords = set(_extract_keywords(combined_text))

        matched = 0
        for symptom in entry.symptoms:
            keywords = _extract_keywords(symptom)
            if not keywords:
                continue
            hits = sum(1 for kw in keywords if kw in context_keywords)
            if hits / len(keywords) >= _SYMPTOM_KEYWORD_THRESHOLD:
                matched += 1

        return matched / len(entry.symptoms)

    def _score_runtime_version(self, entry: KBEntry, context: FailureContext) -> float:
        """Score 1.0 if version matches, 0.5 for wildcard '*', 0.0 otherwise.

        Supports suffix '+' for version-or-later matching
        (e.g. 'syn-nodejs-puppeteer-8.0+' means 8.0 or later).
        """
        if not entry.runtime_versions:
            return 1.0

        # Wildcard entries
        if '*' in entry.runtime_versions or 'all' in entry.runtime_versions:
            return 0.5

        if not context.runtime_version:
            return 0.0

        for version in entry.runtime_versions:
            # Exact match
            if context.runtime_version == version:
                return 1.0
            # Suffix '+' matching (e.g. 'syn-nodejs-puppeteer-8.0+')
            if version.endswith('+'):
                prefix = version[:-1]
                parts = prefix.rsplit('-', 1)
                if len(parts) == 2:
                    family, min_ver = parts[0], parts[1]
                    canary_parts = context.runtime_version.rsplit('-', 1)
                    if len(canary_parts) == 2:
                        canary_family, canary_ver = canary_parts[0], canary_parts[1]
                        if canary_family == family:
                            try:
                                if float(canary_ver) >= float(min_ver):
                                    return 1.0
                            except ValueError:
                                pass

        return 0.0

    def _score_environment(self, entry: KBEntry, context: FailureContext) -> float:
        """Score based on overlap between context env indicators and entry tags/category."""
        entry_tags = {tag.lower() for tag in entry.tags + [entry.category]}
        if not entry_tags:
            return 0.0

        context_indicators = {ind.lower() for ind in context.environment_indicators}
        overlap = len(entry_tags & context_indicators)
        return overlap / max(len(entry_tags), 1)

    def _compute_confidence(
        self, error: float, symptom: float, runtime: float, env: float
    ) -> float:
        """Weighted sum: error*0.40 + symptom*0.20 + runtime*0.20 + env*0.20."""
        return error * 0.40 + symptom * 0.20 + runtime * 0.20 + env * 0.20

    def get_recommendations(self, context: FailureContext) -> list[MatchResult]:
        """Score all active entries, filter by threshold, return top-2 ranked."""
        results: list[MatchResult] = []

        for entry in self.loader.get_active_entries():
            error_score = self._score_error_patterns(entry, context)

            # If no error patterns matched at all, skip — no point recommending
            if error_score == 0.0:
                continue

            symptom_score = self._score_symptoms(entry, context)
            runtime_score = self._score_runtime_version(entry, context)
            env_score = self._score_environment(entry, context)
            confidence = self._compute_confidence(
                error_score, symptom_score, runtime_score, env_score
            )

            if confidence >= 0.60:
                results.append(
                    MatchResult(
                        entry=entry,
                        confidence_score=confidence,
                        error_pattern_score=error_score,
                        symptom_score=symptom_score,
                        runtime_version_score=runtime_score,
                        environment_score=env_score,
                    )
                )

        # Sort descending by confidence, then by severity for ties
        results.sort(
            key=lambda r: (r.confidence_score, _SEVERITY_ORDER.get(r.entry.severity, 0)),
            reverse=True,
        )

        return results[:2]

    def format_recommendations(self, recommendations: list[MatchResult]) -> str:
        """Render matched MatchResult entries into a formatted string section.

        For each match, includes: title, confidence score (as percentage),
        root cause, and solution steps.
        """
        if not recommendations:
            return ''

        lines: list[str] = []
        lines.append('\n📚 Knowledge Base Recommendations')
        lines.append('=' * 40)

        for i, match in enumerate(recommendations, 1):
            entry = match.entry
            confidence_pct = f'{match.confidence_score * 100:.0f}%'
            icon = _SEVERITY_ICONS.get(entry.severity, 'ℹ️')

            lines.append(f'\n{icon} {i}. [{entry.id}] {entry.title}')
            lines.append(f'   Confidence: {confidence_pct} | Severity: {entry.severity}')
            lines.append(f'   Category: {entry.category}')
            lines.append(f'   Root Cause: {entry.root_cause[:300]}')

            if entry.deprecated:
                lines.append('   ⚠️ DEPRECATED')

            for rec in entry.recommendations:
                if rec.title:
                    lines.append(f'   Recommendation: {rec.title}')
                if rec.problem:
                    lines.append(f'     Problem: {rec.problem[:200]}')
                for step in rec.solution:
                    lines.append(f'   - {step.step}')
                    if step.description:
                        lines.append(f'     {step.description}')
                    if step.command:
                        lines.append(f'     Command: {step.command}')
                    if step.expected_outcome:
                        lines.append(f'     Expected: {step.expected_outcome}')
                if rec.estimated_time:
                    lines.append(f'     Estimated time: {rec.estimated_time}')

            if entry.documentation_links:
                lines.append('   Documentation:')
                for doc in entry.documentation_links:
                    lines.append(f'   • {doc.title}: {doc.url}')

        lines.append('')
        return '\n'.join(lines)
