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

"""CloudWatch Application Signals MCP Server - Utility functions."""

from datetime import datetime, timedelta, timezone


def remove_null_values(data: dict) -> dict:
    """Remove keys with None values from a dictionary.

    Args:
        data: Dictionary to clean

    Returns:
        Dictionary with None values removed
    """
    return {k: v for k, v in data.items() if v is not None}


def parse_timestamp(timestamp_str: str, default_hours: int = 24) -> datetime:
    """Parse timestamp string into datetime object.

    Args:
        timestamp_str: Timestamp in unix seconds or 'YYYY-MM-DD HH:MM:SS' format
        default_hours: Default hours to subtract from now if parsing fails

    Returns:
        datetime object in UTC timezone
    """
    try:
        # Ensure we have a string
        if not isinstance(timestamp_str, str):
            timestamp_str = str(timestamp_str)

        # Try parsing as unix timestamp first
        if timestamp_str.isdigit():
            return datetime.fromtimestamp(int(timestamp_str), tz=timezone.utc)

        # Try parsing as ISO format
        if 'T' in timestamp_str:
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

        # Try parsing as 'YYYY-MM-DD HH:MM:SS' format
        return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        # Fallback to default
        return datetime.now(timezone.utc) - timedelta(hours=default_hours)


def calculate_name_similarity(
    target_name: str, candidate_name: str, name_type: str = 'service'
) -> int:
    """Calculate similarity score between target name and candidate name.

    Args:
        target_name: The name the user is looking for
        candidate_name: A candidate name from the API
        name_type: Type of name being matched ("service" or "slo")

    Returns:
        Similarity score (0-100, higher is better match)
    """
    target_lower = target_name.lower().strip()
    candidate_lower = candidate_name.lower().strip()

    # Handle empty strings
    if not target_lower or not candidate_lower:
        return 0

    # Exact match (case insensitive)
    if target_lower == candidate_lower:
        return 100

    # Normalize for special characters (treat -, _, . as equivalent)
    target_normalized = target_lower.replace('_', '-').replace('.', '-')
    candidate_normalized = candidate_lower.replace('_', '-').replace('.', '-')

    if target_normalized == candidate_normalized:
        return 95

    score = 0

    # Word-based matching (most important for fuzzy matching)
    target_words = set(target_normalized.split())
    candidate_words = set(candidate_normalized.split())

    if target_words and candidate_words:
        common_words = target_words.intersection(candidate_words)
        if common_words:
            # Calculate word match ratio
            word_match_ratio = len(common_words) / len(target_words.union(candidate_words))
            score += int(word_match_ratio * 60)  # Up to 60 points for word matches

            # Bonus for high word overlap
            target_coverage = len(common_words) / len(target_words)

            if target_coverage >= 0.8:  # 80% of target words found
                score += 20
            elif target_coverage >= 0.6:  # 60% of target words found
                score += 10

    # Substring matching (secondary)
    if target_normalized in candidate_normalized:
        # Target is contained in candidate
        containment_ratio = len(target_normalized) / len(candidate_normalized)
        score += int(containment_ratio * 30)  # Up to 30 points
    elif candidate_normalized in target_normalized:
        # Candidate is contained in target
        containment_ratio = len(candidate_normalized) / len(target_normalized)
        score += int(containment_ratio * 25)  # Up to 25 points

    # Check for key domain terms that should boost relevance
    if name_type == 'slo':
        key_terms = [
            'availability',
            'latency',
            'error',
            'fault',
            'search',
            'owner',
            'response',
            'time',
            'success',
            'failure',
            'request',
            'operation',
        ]
    else:  # service
        key_terms = [
            'service',
            'api',
            'web',
            'app',
            'backend',
            'frontend',
            'database',
            'cache',
            'queue',
            'worker',
            'lambda',
            'function',
            'microservice',
        ]

    common_key_terms = 0
    for term in key_terms:
        if term in target_normalized and term in candidate_normalized:
            common_key_terms += 1

    if common_key_terms > 0:
        score += common_key_terms * 8  # Up to 8 points per key term

    # Penalize very different lengths (likely different concepts)
    length_diff = abs(len(target_normalized) - len(candidate_normalized))
    if length_diff > 20:
        score = max(0, score - 15)
    elif length_diff > 10:
        score = max(0, score - 5)

    return min(100, score)
