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

"""Utility functions for approximate string matching."""

from thefuzz import fuzz
from typing import List, Optional


def approximate_match(
    candidates: List[str], target: str, threshold: int = 200
) -> Optional[List[str]]:
    """Find best matches using approximate string matching.

    Uses a combination of fuzzy matching algorithms to find the best matches for a target string.

    Args:
        candidates: List of candidate strings to match against
        target: String to match against
        threshold: Minimum score threshold for considering a match (default: 200)

    Returns:
        Optional[List[str]]: List of best matching strings, or None if no matches meet the threshold
    """
    if not candidates:
        return None

    # Score each candidate using approximate matching
    scored_candidates = []
    target_lower = target.lower()

    for name in candidates:
        name_lower = name.lower()
        # Combine different approximate matching methods
        score = (
            fuzz.ratio(target_lower, name_lower)  # Exact character match
            + fuzz.partial_ratio(target_lower, name_lower)  # Partial string match
            + fuzz.token_sort_ratio(target_lower, name_lower)  # Token order independent match
        )
        scored_candidates.append((name, score))

    if not scored_candidates:
        return None

    # Find candidates with the highest score
    max_score = max(score for _, score in scored_candidates)
    if max_score < threshold:
        return None

    best_matches = [name for name, score in scored_candidates if score == max_score]
    return best_matches
