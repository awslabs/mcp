"""Common search utilities for AWS CDK Expert."""

import re
import urllib.parse
from typing import Any, Callable, Dict, List, Optional, TypeVar


T = TypeVar('T')  # Generic type for search items


def normalize_term(term: str) -> str:
    """Normalize a term for consistent matching.

    Args:
        term: The term to normalize

    Returns:
        Normalized term (lowercase, with spaces preserved for word boundaries)
    """
    # Decode URL-encoded strings
    term = urllib.parse.unquote(term).lower()

    # Replace hyphens and underscores with spaces
    term = re.sub(r'[-_]', ' ', term)

    # Remove other special characters but preserve spaces
    term = re.sub(r'[^a-z0-9 ]', '', term)

    # Normalize multiple spaces
    term = re.sub(r'\s+', ' ', term).strip()

    return term


def get_term_variations(term: str) -> List[str]:
    """Get common variations of a term.

    Args:
        term: The term to get variations for

    Returns:
        List of term variations
    """
    term = term.lower()
    variations = [term]

    # Common singular/plural mappings
    term_variations = {
        'knowledgebase': ['knowledgebases', 'knowledge-base', 'knowledge-bases'],
        'knowledgebases': ['knowledgebase', 'knowledge-base', 'knowledge-bases'],
        'agent': ['agents'],
        'agents': ['agent'],
        'actiongroup': ['actiongroups', 'action-group', 'action-groups'],
        'actiongroups': ['actiongroup', 'action-group', 'action-groups'],
        'apigateway': ['api-gateway', 'api gateway', 'apigatewayv2', 'api-gateway-v2'],
        'lambda': ['lambdas', 'lambda-function', 'lambda-functions'],
        'dynamodb': ['dynamo-db', 'dynamo db'],
        's3': ['s3-bucket', 's3 bucket', 'simple storage service'],
        'sqs': ['simple-queue-service', 'simple queue service'],
        'sns': ['simple-notification-service', 'simple notification service'],
    }

    # Add variations if they exist
    if term in term_variations:
        variations.extend(term_variations[term])

    return variations


def expand_search_terms(terms: List[str]) -> List[str]:
    """Expand a list of search terms with variations.

    Args:
        terms: List of search terms

    Returns:
        Expanded list of normalized search terms with variations
    """
    expanded_terms = []

    for term in terms:
        # Normalize the term
        norm_term = normalize_term(term)
        if norm_term and norm_term not in expanded_terms:
            expanded_terms.append(norm_term)

        # Add variations
        for variation in get_term_variations(term):
            norm_variation = normalize_term(variation)
            if norm_variation and norm_variation not in expanded_terms:
                expanded_terms.append(norm_variation)

    return expanded_terms


def calculate_match_score(
    item_text: str,
    search_terms: List[str],
    name_parts: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Calculate a match score for an item against search terms.

    Args:
        item_text: The text to search in (e.g., description)
        search_terms: List of search terms to match
        name_parts: Optional list of name parts for higher-weight matching

    Returns:
        Dictionary with score and matched terms
    """
    matched_terms = []
    score = 0

    for term in search_terms:
        term_matched = False

        # Check name parts first (highest weight)
        if name_parts:
            for part in name_parts:
                if term in normalize_term(part):
                    score += 10
                    if term not in matched_terms:
                        matched_terms.append(term)
                    term_matched = True
                    break

        # If not matched in name parts, check in full text
        if not term_matched and term in item_text:
            score += 5
            if term not in matched_terms:
                matched_terms.append(term)

    # Bonus for matching multiple terms
    if len(matched_terms) > 1:
        score += len(matched_terms) * 3

    return {'score': score, 'matched_terms': matched_terms, 'has_match': len(matched_terms) > 0}


def search_items_with_terms(
    items: List[T],
    search_terms: List[str],
    get_text_fn: Callable[[T], str],
    get_name_parts_fn: Optional[Callable[[T], List[str]]] = None,
) -> List[Dict[str, Any]]:
    """Generic function to search items with search terms.

    Args:
        items: List of items to search
        search_terms: List of search terms
        get_text_fn: Function to extract searchable text from an item
        get_name_parts_fn: Optional function to extract name parts from an item

    Returns:
        List of matched items with scores
    """
    # Expand search terms with variations
    expanded_terms = expand_search_terms(search_terms)

    # Calculate scores for each item
    scored_items = []

    for item in items:
        item_text = normalize_term(get_text_fn(item))
        name_parts = get_name_parts_fn(item) if get_name_parts_fn else None

        match_result = calculate_match_score(item_text, expanded_terms, name_parts)

        # Only include items with at least one match
        if match_result['has_match']:
            scored_items.append(
                {
                    'item': item,
                    'score': match_result['score'],
                    'matched_terms': match_result['matched_terms'],
                }
            )

    # Sort by score (descending)
    scored_items.sort(key=lambda x: x['score'], reverse=True)

    return scored_items
