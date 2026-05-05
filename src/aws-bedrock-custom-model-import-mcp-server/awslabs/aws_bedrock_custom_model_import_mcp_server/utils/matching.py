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

"""Utility functions for approximate resource matching."""

import difflib
import re
from loguru import logger
from thefuzz import fuzz
from typing import List, Optional


def normalize_name(name: str) -> str:
    """Normalize name for comparison.

    Args:
        name: name to normalize

    Returns:
        str: Normalized name
    """
    # Convert to lowercase
    name = name.lower()

    # Remove all dots and dashes
    name = re.sub(r'[.-]', '', name)

    # Remove other common separators
    name = re.sub(r'[-_]', '', name)

    return name.strip()


def approximate_match(
    candidates: List[str], target: str, threshold: int = 200
) -> Optional[List[str]]:
    """Find best matches using approximate resource matching.

    Uses a combination of fuzzy matching algorithms to find the best matches for a target resource.

    Args:
        candidates: List of candidate resources to match against
        target: Resource to match against
        threshold: Minimum score threshold for considering a match (default: 200)

    Returns:
        Optional[List[str]]: List of best matching resources, or None if no matches meet the threshold
    """
    logger.debug(f'Finding best matches for {target} among {candidates}')
    if not candidates:
        return None

    # Normalize target
    target_normalized = normalize_name(target)

    # Score each candidate using approximate matching
    scored_candidates = []

    for candidate in candidates:
        candidate_normalized = normalize_name(candidate)

        # Base similarity scores
        ratio_score = fuzz.ratio(target_normalized, candidate_normalized)
        partial_score = fuzz.partial_ratio(target_normalized, candidate_normalized)
        token_score = fuzz.token_sort_ratio(target_normalized, candidate_normalized)

        # Sequence matcher for longest contiguous match
        seq_matcher = difflib.SequenceMatcher(None, target_normalized, candidate_normalized)
        longest_match = seq_matcher.find_longest_match(
            0, len(target_normalized), 0, len(candidate_normalized)
        )
        longest_match_score = (longest_match.size / len(target_normalized)) * 100

        # Adjust ratio score based on string length
        length_factor = min(len(candidate_normalized) / len(target_normalized), 1)
        adjusted_ratio_score = ratio_score * length_factor

        score = (
            adjusted_ratio_score * 1.0  # Higher weight for exact character match
            + partial_score * 1.0  # Normal weight for partial matches
            + token_score * 0.5  # Lower weight for token sorting
            + longest_match_score * 2.0  # Weight for longest contiguous match
        )
        scored_candidates.append((candidate, score))

    logger.debug(f'Scores for {target} candidates: {scored_candidates}')

    if not scored_candidates:
        return None

    # Find candidates with the highest score
    max_score = max(score for _, score in scored_candidates)
    if max_score < threshold:
        return None

    best_matches = [name for name, score in scored_candidates if score == max_score]
    return best_matches
