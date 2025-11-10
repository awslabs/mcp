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

"""Pattern matching algorithms for genomics file search."""

from awslabs.aws_healthomics_mcp_server.consts import (
    FUZZY_MATCH_MAX_MULTIPLIER,
    FUZZY_MATCH_THRESHOLD,
    MULTIPLE_MATCH_BONUS_MULTIPLIER,
    SUBSTRING_MATCH_MAX_MULTIPLIER,
    TAG_MATCH_PENALTY_MULTIPLIER,
)
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple


class PatternMatcher:
    """Handles pattern matching for genomics file search with fuzzy matching algorithms."""

    def __init__(self):
        """Initialize the pattern matcher."""
        self.fuzzy_threshold = FUZZY_MATCH_THRESHOLD

    def calculate_match_score(self, text: str, patterns: List[str]) -> Tuple[float, List[str]]:
        """Calculate match score for text against multiple patterns.

        Args:
            text: The text to match against (file path, name, etc.)
            patterns: List of search patterns to match

        Returns:
            Tuple of (score, match_reasons) where score is 0.0-1.0 and
            match_reasons is a list of explanations for the matches
        """
        if not patterns or not text:
            return 0.0, []

        max_score = 0.0
        match_reasons = []

        for pattern in patterns:
            if not pattern.strip():
                continue

            # Try different matching strategies
            exact_score = self._exact_match_score(text, pattern)
            substring_score = self._substring_match_score(text, pattern)
            fuzzy_score = self._fuzzy_match_score(text, pattern)

            # Take the best score for this pattern
            pattern_score = max(exact_score, substring_score, fuzzy_score)

            if pattern_score > 0:
                if exact_score == pattern_score:
                    match_reasons.append(f"Exact match for '{pattern}'")
                elif substring_score == pattern_score:
                    match_reasons.append(f"Substring match for '{pattern}'")
                elif fuzzy_score == pattern_score:
                    match_reasons.append(f"Fuzzy match for '{pattern}'")

                max_score = max(max_score, pattern_score)

        # Apply bonus for multiple pattern matches
        if len([r for r in match_reasons if 'match' in r]) > 1:
            max_score = min(
                1.0, max_score * MULTIPLE_MATCH_BONUS_MULTIPLIER
            )  # Bonus, capped at 1.0

        return max_score, match_reasons

    def match_file_path(self, file_path: str, patterns: List[str]) -> Tuple[float, List[str]]:
        """Match patterns against file path components.

        Args:
            file_path: Full file path to match against
            patterns: List of search patterns

        Returns:
            Tuple of (score, match_reasons)
        """
        if not patterns or not file_path:
            return 0.0, []

        # Extract different components of the path for matching
        path_components = [
            file_path,  # Full path
            file_path.split('/')[-1],  # Filename only
            file_path.split('/')[-1].split('.')[0],  # Filename without extension
        ]

        max_score = 0.0
        all_reasons = []

        for component in path_components:
            score, reasons = self.calculate_match_score(component, patterns)
            if score > max_score:
                max_score = score
                all_reasons = reasons

        return max_score, all_reasons

    def match_tags(self, tags: Dict[str, str], patterns: List[str]) -> Tuple[float, List[str]]:
        """Match patterns against file tags.

        Args:
            tags: Dictionary of tag key-value pairs
            patterns: List of search patterns

        Returns:
            Tuple of (score, match_reasons)
        """
        if not patterns or not tags:
            return 0.0, []

        max_score = 0.0
        match_reasons = []

        # Check both tag keys and values
        tag_texts = []
        for key, value in tags.items():
            tag_texts.extend([key, value, f'{key}:{value}'])

        for tag_text in tag_texts:
            score, reasons = self.calculate_match_score(tag_text, patterns)
            if score > max_score:
                max_score = score
                match_reasons = [f'Tag {reason}' for reason in reasons]

        # Tag matches get a slight penalty compared to path matches
        return max_score * TAG_MATCH_PENALTY_MULTIPLIER, match_reasons

    def _exact_match_score(self, text: str, pattern: str) -> float:
        """Calculate score for exact matches (case-insensitive)."""
        if text.lower() == pattern.lower():
            return 1.0
        return 0.0

    def _substring_match_score(self, text: str, pattern: str) -> float:
        """Calculate score for substring matches (case-insensitive)."""
        text_lower = text.lower()
        pattern_lower = pattern.lower()

        if pattern_lower in text_lower:
            # Score based on how much of the text the pattern covers
            coverage = len(pattern_lower) / len(text_lower)
            return SUBSTRING_MATCH_MAX_MULTIPLIER * coverage  # Max score for substring matches
        return 0.0

    def _fuzzy_match_score(self, text: str, pattern: str) -> float:
        """Calculate score for fuzzy matches using sequence similarity."""
        text_lower = text.lower()
        pattern_lower = pattern.lower()

        # Use SequenceMatcher for fuzzy matching
        similarity = SequenceMatcher(None, text_lower, pattern_lower).ratio()

        if similarity >= self.fuzzy_threshold:
            return FUZZY_MATCH_MAX_MULTIPLIER * similarity  # Max score for fuzzy matches
        return 0.0

    def extract_filename_components(self, file_path: str) -> Dict[str, Optional[str]]:
        """Extract useful components from a file path for matching.

        Args:
            file_path: Full file path

        Returns:
            Dictionary with extracted components
        """
        filename = file_path.split('/')[-1]

        # Handle compressed extensions
        if filename.endswith('.gz'):
            base_filename = filename[:-3]
            compression = 'gz'
        elif filename.endswith('.bz2'):
            base_filename = filename[:-4]
            compression = 'bz2'
        else:
            base_filename = filename
            compression = None

        # Extract base name and extension
        if '.' in base_filename:
            name_parts = base_filename.split('.')
            base_name = name_parts[0]
            extension = '.'.join(name_parts[1:])
        else:
            base_name = base_filename
            extension = ''

        return {
            'full_path': file_path,
            'filename': filename,
            'base_filename': base_filename,
            'base_name': base_name,
            'extension': extension,
            'compression': compression,
            'directory': '/'.join(file_path.split('/')[:-1]) if '/' in file_path else '',
        }
